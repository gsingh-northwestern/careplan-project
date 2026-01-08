"""
LLM Service for generating care plans.

Provides the interface for care plan generation using Claude API.
Supports both production mode and mock mode for testing without API access.
Includes few-shot learning from recent care plans for improved generation quality.
"""

import logging
import time
from typing import Tuple, List, Optional

from django.conf import settings

logger = logging.getLogger('careplan')

# Maximum characters per example to avoid context window issues
MAX_EXAMPLE_LENGTH = 3000

# Template for including few-shot examples in the prompt
EXAMPLES_SECTION_TEMPLATE = """## Reference Examples

Below are examples of previously generated care plans. Use these as a reference for style, structure, and level of detail. Adapt the content appropriately for the current patient.

{examples}

---

## Instructions
Generate a care plan for the patient below, following a similar style and level of detail as the examples above.

"""

# Care plan generation prompt template
CARE_PLAN_PROMPT = """You are a clinical pharmacist assistant. Based on the patient records provided, generate a comprehensive care plan following clinical guidelines.
{example_section}

## Patient Information
- Name: {patient_name}
- MRN: {mrn}
- Primary Diagnosis: {primary_diagnosis}
- Additional Diagnoses: {additional_diagnoses}
- Current Medication: {medication_name}
- Medication History: {medication_history}

## Patient Records
{patient_records}

## Required Output Format

Generate a detailed care plan with the following sections:

### 1. Problem List / Drug Therapy Problems (DTPs)
Identify all drug therapy problems including:
- Need for additional therapy
- Unnecessary therapy
- Ineffective drug therapy
- Dosage too low/high
- Adverse drug reactions
- Non-adherence
- Drug interactions

### 2. Goals (SMART)
**Primary Goal:** [Specific clinical outcome]
**Safety Goals:** [Adverse event prevention targets]
**Process Goals:** [Treatment completion targets]

### 3. Pharmacist Interventions / Plan

**Dosing & Administration**
- Verify total dose calculations
- Document administration schedule

**Premedication**
- Recommended premedications with doses and timing

**Infusion Rates & Titration** (if applicable)
- Starting rate
- Titration schedule
- Maximum rate

**Hydration & Renal Protection**
- Fluid recommendations
- Renal function monitoring

**Thrombosis Risk Mitigation**
- Risk assessment
- Prophylactic measures

**Concomitant Medications**
- Continue/adjust recommendations for other medications

### 4. Monitoring Plan & Lab Schedule

| Timepoint | Parameters to Monitor |
|-----------|----------------------|
| Before therapy | [Labs, vitals, assessments] |
| During therapy | [Monitoring frequency and parameters] |
| Post-therapy | [Follow-up schedule] |

### 5. Adverse Event Management
- Mild reactions: [Protocol]
- Moderate reactions: [Protocol]
- Severe reactions: [Protocol]

### 6. Patient Education Points
- Key information for patient understanding
- Signs/symptoms to report
- Lifestyle considerations

### 7. Documentation & Communication
- Required documentation
- Communication with care team

Be specific, evidence-based, and follow current clinical guidelines. Include relevant dosing calculations where applicable."""


def generate_care_plan(order) -> Tuple[str, int, str]:
    """
    Generate a care plan for the given order.

    Args:
        order: Order model instance with patient, provider, and clinical data

    Returns:
        Tuple of (care_plan_content, generation_time_ms, model_used)
    """
    if settings.LLM_MOCK_MODE:
        return _generate_mock_care_plan(order)
    else:
        return _generate_claude_care_plan(order)


def get_recent_care_plans(limit: int = 3, exclude_order_id: Optional[int] = None) -> List:
    """
    Fetch the most recent care plans for use as few-shot examples.

    Args:
        limit: Maximum number of care plans to return
        exclude_order_id: Order ID to exclude (to avoid using current order's plan)

    Returns:
        List of CarePlan objects ordered by generated_at descending
    """
    from .models import CarePlan

    queryset = CarePlan.objects.select_related(
        'order',
        'order__patient',
        'order__provider'
    ).order_by('-generated_at')

    if exclude_order_id:
        queryset = queryset.exclude(order_id=exclude_order_id)

    return list(queryset[:limit])


def format_care_plan_examples(care_plans: List) -> str:
    """
    Format care plans as few-shot examples for the prompt.

    Truncates very long care plans to manage context window.

    Args:
        care_plans: List of CarePlan objects

    Returns:
        Formatted string with numbered examples
    """
    if not care_plans:
        return ""

    examples = []

    for i, cp in enumerate(care_plans, 1):
        order = cp.order

        # Truncate content if too long
        content = cp.content
        if len(content) > MAX_EXAMPLE_LENGTH:
            content = content[:MAX_EXAMPLE_LENGTH] + "\n\n[... truncated for brevity ...]"

        example = f"""
### EXAMPLE {i}
**Patient:** {order.patient.first_name} {order.patient.last_name}
**Diagnosis:** {order.primary_diagnosis_code} - {order.primary_diagnosis_description}
**Medication:** {order.medication_name}

**CARE PLAN OUTPUT:**
{content}
"""
        examples.append(example)

    return "\n---\n".join(examples)


def _generate_claude_care_plan(order) -> Tuple[str, int, str]:
    """
    Generate care plan using Claude API.
    """
    import anthropic

    api_key = settings.ANTHROPIC_API_KEY

    # Debug logging for API key (never log the actual key!)
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not configured - environment variable is empty or not set")
        raise ValueError(
            "ANTHROPIC_API_KEY is not configured. "
            "Set it in your .env file or enable LLM_MOCK_MODE=True"
        )

    # Log key details for debugging (safe - only length and prefix)
    key_prefix = api_key[:12] if len(api_key) > 12 else "too_short"
    logger.info(f"API key configured: prefix={key_prefix}..., length={len(api_key)}")

    # Set explicit timeout for API calls (default httpx timeout is 30s which is too short)
    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=300.0  # 5 minute timeout for care plan generation
    )

    # Fetch recent care plans for few-shot learning
    recent_plans = get_recent_care_plans(limit=3, exclude_order_id=order.id)

    # Build example section
    example_section = ""
    if recent_plans:
        examples_text = format_care_plan_examples(recent_plans)
        example_section = EXAMPLES_SECTION_TEMPLATE.format(examples=examples_text)
        logger.info(f"Including {len(recent_plans)} care plan examples in prompt")
    else:
        logger.info("No previous care plans available for few-shot learning")

    # Format the prompt with order data AND examples
    prompt = CARE_PLAN_PROMPT.format(
        example_section=example_section,
        patient_name=f"{order.patient.first_name} {order.patient.last_name}",
        mrn=order.patient.mrn,
        primary_diagnosis=f"{order.primary_diagnosis_code} - {order.primary_diagnosis_description}",
        additional_diagnoses=", ".join(order.additional_diagnoses) if order.additional_diagnoses else "None",
        medication_name=order.medication_name,
        medication_history=", ".join(order.medication_history) if order.medication_history else "None",
        patient_records=order.patient_records
    )

    model = "claude-sonnet-4-5-20250929"
    start_time = time.time()

    logger.info(f"Starting API call to model {model} for Order #{order.id}")
    logger.info(f"Prompt length: {len(prompt)} characters")

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        content = response.content[0].text

        logger.info(
            f"Generated care plan for Order #{order.id} "
            f"using {model} in {elapsed_ms}ms"
        )

        return content, elapsed_ms, model

    except anthropic.APIError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Claude API error after {elapsed_ms}ms: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Unexpected error after {elapsed_ms}ms: {type(e).__name__}: {str(e)}")
        raise


def _generate_mock_care_plan(order) -> Tuple[str, int, str]:
    """
    Generate a mock care plan for testing without API access.
    """
    # Simulate some processing time
    time.sleep(0.5)
    start_time = time.time()

    # Log example usage even in mock mode for testing
    recent_plans = get_recent_care_plans(limit=3, exclude_order_id=order.id)
    logger.info(f"Mock mode: Would use {len(recent_plans)} examples in production")

    mock_content = f"""# Care Plan for {order.patient.first_name} {order.patient.last_name}

**Generated:** {time.strftime('%Y-%m-%d %H:%M')}
**MRN:** {order.patient.mrn}
**Medication:** {order.medication_name}
**Primary Diagnosis:** {order.primary_diagnosis_code} - {order.primary_diagnosis_description}

---

## 1. Problem List / Drug Therapy Problems (DTPs)

1. **Need for immunomodulation** - Patient requires {order.medication_name} therapy for symptomatic control
2. **Risk of infusion-related reactions** - Headache, chills, fever, rare anaphylaxis
3. **Risk of renal dysfunction** - Monitor in susceptible patients
4. **Risk of thromboembolic events** - Rare but requires risk factor assessment
5. **Drug-drug interactions** - Review concomitant medications
6. **Patient education gap** - Ensure understanding of therapy and adverse signs

## 2. Goals (SMART)

**Primary Goal:** Achieve clinically meaningful improvement in symptoms within 2 weeks of completing therapy course.

**Safety Goals:**
- No severe infusion reactions during therapy
- No acute kidney injury (SCr increase <0.3 mg/dL within 7 days)
- No thromboembolic events during or after therapy

**Process Goals:**
- Complete full prescribed course with documented monitoring
- Document all interventions and patient education in EMR

## 3. Pharmacist Interventions / Plan

### Dosing & Administration
- **Total dose:** Calculate based on actual body weight
- **Schedule:** Per physician order and manufacturer recommendations
- **Documentation:** Record lot number and expiration of product

### Premedication
- Acetaminophen 650 mg PO 30-60 minutes prior to infusion
- Diphenhydramine 25-50 mg PO 30-60 minutes prior to infusion
- Consider low-dose corticosteroid if prior reactions

### Infusion Rates & Titration
- Start at low rate per product label (e.g., 0.5 mL/kg/hr)
- Increase stepwise every 15-30 minutes as tolerated
- Maximum rate per manufacturer specifications
- Slow or stop if any infusion reactions occur

### Hydration & Renal Protection
- Ensure adequate hydration prior to infusion
- Consider 250-500 mL normal saline if not fluid overloaded
- Monitor renal function pre-course and within 3-7 days post-completion

### Thrombosis Risk Mitigation
- Assess baseline thrombosis risk
- Encourage early ambulation and adequate hydration
- Educate patient on symptoms to report

### Concomitant Medications
- Review all current medications for interactions
- Continue supportive care medications as prescribed

## 4. Monitoring Plan & Lab Schedule

| Timepoint | Parameters to Monitor |
|-----------|----------------------|
| Before therapy | CBC, BMP (SCr, BUN), baseline vitals, assess symptoms |
| During infusion | Vitals q15 min first hour, then q30-60 min; respiratory status |
| After each infusion | Assess for delayed adverse events |
| 3-7 days post-course | BMP to check renal function |
| Clinical follow-up | 2 weeks and 6-8 weeks to assess response |

## 5. Adverse Event Management

**Mild Reaction (headache, chills, myalgia):**
- Slow infusion rate
- Give acetaminophen/antihistamine
- Observe closely

**Moderate Reaction (wheezing, hypotension, chest pain):**
- Stop infusion immediately
- Follow emergency protocol
- Notify prescriber

**Severe Reaction (anaphylaxis):**
- Stop infusion immediately
- Administer epinephrine per protocol
- Airway support
- Emergency response team

## 6. Patient Education Points

- Explain the infusion process and expected duration
- Review signs and symptoms to report immediately:
  - Chest pain, shortness of breath
  - Severe headache
  - Swelling in extremities
  - Fever, chills, rash
- Emphasize importance of adequate hydration
- Provide contact information for questions

## 7. Documentation & Communication

- Enter all interventions and education in EMR
- Document infusion details including lot numbers
- Communicate any dose modifications or adverse events to prescriber
- Coordinate with nursing team on monitoring schedule

---

*This care plan was generated based on the provided patient records and current clinical guidelines. All recommendations should be verified with the prescribing physician.*

**[MOCK MODE]** - This is a sample care plan for demonstration purposes.
"""

    elapsed_ms = int((time.time() - start_time) * 1000) + 500  # Add simulated delay
    model = "mock-claude-model"

    logger.info(
        f"Generated MOCK care plan for Order #{order.id} in {elapsed_ms}ms"
    )

    return mock_content, elapsed_ms, model
