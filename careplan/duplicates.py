"""
Duplicate detection for the Care Plan Generator.

Detects potential duplicate entries for:
- Providers: Exact NPI match (block) or similar name with different NPI (warn)
- Patients: Same MRN with mismatched name/DOB (warn) or same name+DOB with different MRN (warn)
- Orders: Same patient + medication within time window (two-tier severity)

Note: Patients with same MRN are NOT blocked because patients can have multiple orders.
The system reuses existing patient records for new orders.

Result types:
- 'block': Cannot proceed, duplicate exists (providers only)
- 'warn': Can proceed but user should verify
- 'ok': No duplicates detected
"""

from datetime import timedelta
from typing import Optional
from django.utils import timezone
from django.db.models import Q

from .models import Provider, Patient, Order


class DuplicateResult:
    """Result of a duplicate check."""

    def __init__(
        self,
        duplicate_type: str,
        message: str = "",
        similar_items: list = None,
        severity: str = "medium"
    ):
        """
        Args:
            duplicate_type: 'block', 'warn', or 'ok'
            message: User-friendly message explaining the duplicate
            similar_items: List of similar items found (for display)
            severity: 'high', 'medium', or 'low' - for UI styling
        """
        self.type = duplicate_type
        self.message = message
        self.similar_items = similar_items or []
        self.severity = severity

    @property
    def is_ok(self) -> bool:
        return self.type == 'ok'

    @property
    def is_warning(self) -> bool:
        return self.type == 'warn'

    @property
    def is_blocking(self) -> bool:
        return self.type == 'block'

    @property
    def is_high_severity(self) -> bool:
        return self.severity == 'high'

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'message': self.message,
            'similar_items': self.similar_items,
            'severity': self.severity
        }


def check_provider_duplicate(
    name: str,
    npi: str,
    exclude_id: Optional[int] = None
) -> DuplicateResult:
    """
    Check for duplicate providers.

    Detection rules:
    1. Exact NPI match -> BLOCK (can't have two providers with same NPI)
    2. Similar name with different NPI -> WARN (might be a typo/error)

    Args:
        name: Provider name to check
        npi: NPI to check
        exclude_id: Provider ID to exclude (for updates)

    Returns:
        DuplicateResult with type 'block', 'warn', or 'ok'
    """
    if not name or not npi:
        return DuplicateResult('ok')

    # Check for exact NPI match
    npi_query = Provider.objects.filter(npi=npi)
    if exclude_id:
        npi_query = npi_query.exclude(id=exclude_id)

    exact_npi = npi_query.first()
    if exact_npi:
        return DuplicateResult(
            'block',
            f"Provider with NPI {npi} already exists: {exact_npi.name}",
            [{'id': exact_npi.id, 'name': exact_npi.name, 'npi': exact_npi.npi}]
        )

    # Check for similar name with different NPI
    # Split name and filter out common prefixes
    name_parts = name.strip().split()
    if not name_parts:
        return DuplicateResult('ok')

    # Common prefixes to skip when matching
    skip_prefixes = {'dr', 'dr.', 'mr', 'mr.', 'mrs', 'mrs.', 'ms', 'ms.', 'prof', 'prof.'}

    # Filter name parts - skip short parts and common prefixes
    significant_parts = [
        part for part in name_parts
        if len(part) > 3 and part.lower().rstrip('.') not in skip_prefixes
    ]

    if not significant_parts:
        return DuplicateResult('ok')

    # Search for providers with similar names
    similar_query = Provider.objects.exclude(npi=npi)
    if exclude_id:
        similar_query = similar_query.exclude(id=exclude_id)

    # Build OR query for significant name parts
    name_q = Q()
    for part in significant_parts[:2]:  # Check first two significant parts
        name_q |= Q(name__icontains=part)

    if name_q:
        similar = similar_query.filter(name_q)[:5]

        if similar.exists():
            return DuplicateResult(
                'warn',
                "Similar provider name exists with a different NPI. Please verify this is correct.",
                [{'id': p.id, 'name': p.name, 'npi': p.npi} for p in similar]
            )

    return DuplicateResult('ok')


def check_patient_duplicate(
    first_name: str,
    last_name: str,
    mrn: str,
    dob=None,
    exclude_id: Optional[int] = None
) -> DuplicateResult:
    """
    Check for patient data entry issues.

    Detection rules:
    1. MRN exists with DIFFERENT name/DOB -> WARN (data entry mismatch)
    2. Same name + DOB with different MRN -> WARN (might be same person, different MRN)

    Note: Same MRN is NOT blocked because patients can have multiple orders.
    The system will reuse existing patient records for new orders.

    Args:
        first_name: Patient first name
        last_name: Patient last name
        mrn: MRN to check
        dob: Optional date of birth
        exclude_id: Patient ID to exclude (for updates)

    Returns:
        DuplicateResult with type 'warn' or 'ok' (never 'block' for patients)
    """
    if not mrn:
        return DuplicateResult('ok')

    # Check for existing patient with same MRN but different info
    mrn_query = Patient.objects.filter(mrn=mrn)
    if exclude_id:
        mrn_query = mrn_query.exclude(id=exclude_id)

    existing = mrn_query.first()
    if existing:
        # Check if the entered name/DOB matches the existing patient
        name_matches = (
            existing.first_name.lower() == first_name.strip().lower() and
            existing.last_name.lower() == last_name.strip().lower()
        )
        dob_matches = (dob is None or existing.dob == dob)

        if not name_matches or not dob_matches:
            # Warn about data mismatch - they're entering different info for same MRN
            return DuplicateResult(
                'warn',
                f"Patient with MRN {mrn} already exists as {existing.first_name} {existing.last_name} "
                f"(DOB: {existing.dob}). The existing patient record will be used for this order.",
                [{
                    'id': existing.id,
                    'name': f"{existing.first_name} {existing.last_name}",
                    'mrn': existing.mrn,
                    'dob': str(existing.dob) if existing.dob else None
                }]
            )
        # Same MRN with matching info - OK, will reuse patient
        return DuplicateResult('ok')

    # Check for same name + DOB with different MRN (potential duplicate patient record)
    if first_name and last_name and dob:
        name_dob_query = Patient.objects.filter(
            first_name__iexact=first_name.strip(),
            last_name__iexact=last_name.strip(),
            dob=dob
        ).exclude(mrn=mrn)

        if exclude_id:
            name_dob_query = name_dob_query.exclude(id=exclude_id)

        similar = name_dob_query.first()
        if similar:
            return DuplicateResult(
                'warn',
                f"Patient with same name and date of birth exists with MRN {similar.mrn}. Is this a duplicate?",
                [{
                    'id': similar.id,
                    'name': f"{similar.first_name} {similar.last_name}",
                    'mrn': similar.mrn,
                    'dob': str(similar.dob)
                }]
            )

    return DuplicateResult('ok')


def check_order_duplicate(
    patient_id: int,
    medication_name: str,
    days_window: int = 30,
    exclude_id: Optional[int] = None
) -> DuplicateResult:
    """
    Check for duplicate orders with two-tier severity.

    Detection rules:
    - Same patient + same medication on SAME DAY -> HIGH severity warning
    - Same patient + same medication within time window -> MEDIUM severity warning

    Args:
        patient_id: ID of the patient
        medication_name: Name of the medication
        days_window: Number of days to look back (default 30)
        exclude_id: Order ID to exclude (for updates)

    Returns:
        DuplicateResult with type 'warn' or 'ok', and severity 'high' or 'medium'
    """
    if not patient_id or not medication_name:
        return DuplicateResult('ok')

    cutoff_date = timezone.now() - timedelta(days=days_window)
    today = timezone.now().date()

    recent_query = Order.objects.filter(
        patient_id=patient_id,
        medication_name__iexact=medication_name.strip(),
        created_at__gte=cutoff_date
    ).order_by('-created_at')  # Most recent first

    if exclude_id:
        recent_query = recent_query.exclude(id=exclude_id)

    recent = recent_query.first()
    if recent:
        order_date = recent.created_at.date()

        if order_date == today:
            # SAME DAY - High severity warning
            return DuplicateResult(
                'warn',
                f"⚠️ DUPLICATE ALERT: An order for {medication_name} was ALREADY created for this patient TODAY at {recent.created_at.strftime('%I:%M %p')}. This is likely a duplicate order.",
                [{
                    'id': recent.id,
                    'medication': recent.medication_name,
                    'created_at': recent.created_at.strftime('%Y-%m-%d %H:%M'),
                    'status': recent.status
                }],
                severity='high'
            )
        else:
            # Within 30 days - Medium severity warning
            return DuplicateResult(
                'warn',
                f"An order for {medication_name} was created for this patient on {order_date.strftime('%Y-%m-%d')}. Is this a duplicate?",
                [{
                    'id': recent.id,
                    'medication': recent.medication_name,
                    'created_at': recent.created_at.strftime('%Y-%m-%d %H:%M'),
                    'status': recent.status
                }],
                severity='medium'
            )

    return DuplicateResult('ok')


def get_existing_provider_by_npi(npi: str) -> Optional[Provider]:
    """
    Get an existing provider by NPI.

    Useful for auto-populating provider info when NPI is entered.
    """
    if not npi or len(npi) != 10:
        return None
    return Provider.objects.filter(npi=npi).first()


def get_existing_patient_by_mrn(mrn: str) -> Optional[Patient]:
    """
    Get an existing patient by MRN.

    Useful for auto-populating patient info when MRN is entered.
    """
    if not mrn or len(mrn) != 6:
        return None
    return Patient.objects.filter(mrn=mrn).first()
