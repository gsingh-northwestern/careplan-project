"""
Form definitions for the Care Plan Generator.

Handles user input and validation for:
- OrderForm: Main form for creating care plan orders
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Provider, Patient, Order
from .validators import (
    validate_npi,
    validate_mrn,
    validate_icd10_code,
    validate_icd10_codes_list,
    validate_dob,
    parse_comma_separated_codes,
    parse_medication_history,
)
from .duplicates import (
    check_provider_duplicate,
    check_patient_duplicate,
    get_existing_provider_by_npi,
    get_existing_patient_by_mrn,
)


class OrderForm(forms.Form):
    """
    Main form for creating a new care plan order.

    Combines provider, patient, diagnosis, medication, and patient records
    into a single form for the medical assistant workflow.
    """

    # Provider fields
    provider_name = forms.CharField(
        max_length=255,
        label="Provider Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Dr. Jane Smith',
            'hx-post': '/api/check-provider/',
            'hx-trigger': 'blur',
            'hx-target': '#provider-warning',
            'hx-include': '[name=provider_npi]',
        })
    )
    provider_npi = forms.CharField(
        max_length=10,
        min_length=10,
        label="Provider NPI",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '1234567890',
            'hx-post': '/api/check-provider/',
            'hx-trigger': 'blur',
            'hx-target': '#provider-warning',
            'hx-include': '[name=provider_name]',
        })
    )

    # Patient fields
    patient_first_name = forms.CharField(
        max_length=100,
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'John',
        })
    )
    patient_last_name = forms.CharField(
        max_length=100,
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Doe',
        })
    )
    patient_mrn = forms.CharField(
        max_length=6,
        min_length=6,
        label="MRN",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '123456',
            'hx-post': '/api/check-patient/',
            'hx-trigger': 'blur',
            'hx-target': '#patient-warning',
            'hx-include': '[name=patient_first_name],[name=patient_last_name],[name=patient_dob]',
        })
    )
    patient_dob = forms.DateField(
        required=True,
        label="Date of Birth",
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        }),
        help_text="Required for care plan generation"
    )

    # Diagnosis fields
    primary_diagnosis_code = forms.CharField(
        max_length=10,
        label="Primary Diagnosis (ICD-10)",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'G70.00',
        })
    )
    primary_diagnosis_description = forms.CharField(
        max_length=255,
        required=False,
        label="Diagnosis Description",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Myasthenia gravis',
        })
    )
    additional_diagnoses = forms.CharField(
        required=False,
        label="Additional Diagnoses",
        help_text="Enter ICD-10 codes separated by commas",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'I10, K21.0',
        })
    )

    # Medication fields
    medication_name = forms.CharField(
        max_length=255,
        label="Medication Name",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'IVIG',
        })
    )
    medication_history = forms.CharField(
        required=False,
        label="Medication History",
        help_text="Enter medications separated by commas",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Prednisone, Pyridostigmine',
        })
    )

    # Patient records
    patient_records = forms.CharField(
        label="Patient Records",
        help_text="Paste clinical notes and patient records here",
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 12,
            'placeholder': 'Paste patient clinical records here...',
        })
    )

    def clean_provider_npi(self):
        """Validate NPI format."""
        npi = self.cleaned_data.get('provider_npi', '').strip()
        validate_npi(npi)
        return npi

    def clean_patient_mrn(self):
        """Validate MRN format."""
        mrn = self.cleaned_data.get('patient_mrn', '').strip()
        validate_mrn(mrn)
        return mrn

    def clean_primary_diagnosis_code(self):
        """Validate ICD-10 code format."""
        code = self.cleaned_data.get('primary_diagnosis_code', '').strip().upper()
        validate_icd10_code(code)
        return code

    def clean_additional_diagnoses(self):
        """Parse and validate additional diagnosis codes."""
        codes_str = self.cleaned_data.get('additional_diagnoses', '')
        if not codes_str:
            return []
        codes = parse_comma_separated_codes(codes_str)
        return validate_icd10_codes_list(codes)

    def clean_medication_history(self):
        """Parse medication history into a list."""
        meds_str = self.cleaned_data.get('medication_history', '')
        return parse_medication_history(meds_str)

    def clean_patient_dob(self):
        """Validate date of birth (required field)."""
        dob = self.cleaned_data.get('patient_dob')
        if not dob:
            raise ValidationError("Date of birth is required for care plan generation.")
        validate_dob(dob)
        return dob

    def clean(self):
        """Cross-field validation and duplicate checks."""
        cleaned_data = super().clean()

        # Check provider duplicate (warning only in form, blocking handled in view)
        provider_name = cleaned_data.get('provider_name', '')
        provider_npi = cleaned_data.get('provider_npi', '')

        if provider_name and provider_npi:
            result = check_provider_duplicate(provider_name, provider_npi)
            if result.is_blocking:
                raise ValidationError(result.message)
            # Store warning for display (not blocking)
            cleaned_data['_provider_warning'] = result if result.is_warning else None

        # Check patient duplicate
        patient_first = cleaned_data.get('patient_first_name', '')
        patient_last = cleaned_data.get('patient_last_name', '')
        patient_mrn = cleaned_data.get('patient_mrn', '')
        patient_dob = cleaned_data.get('patient_dob')

        if patient_first and patient_last and patient_mrn:
            result = check_patient_duplicate(
                patient_first, patient_last, patient_mrn, patient_dob
            )
            if result.is_blocking:
                raise ValidationError(result.message)
            cleaned_data['_patient_warning'] = result if result.is_warning else None

        return cleaned_data

    def get_or_create_provider(self) -> Provider:
        """
        Get existing provider by NPI or create a new one.
        """
        npi = self.cleaned_data['provider_npi']
        name = self.cleaned_data['provider_name']

        provider = get_existing_provider_by_npi(npi)
        if provider:
            return provider

        return Provider.objects.create(name=name, npi=npi)

    def get_or_create_patient(self) -> Patient:
        """
        Get existing patient by MRN or create a new one.
        """
        mrn = self.cleaned_data['patient_mrn']
        first_name = self.cleaned_data['patient_first_name']
        last_name = self.cleaned_data['patient_last_name']
        dob = self.cleaned_data.get('patient_dob')

        patient = get_existing_patient_by_mrn(mrn)
        if patient:
            return patient

        return Patient.objects.create(
            first_name=first_name,
            last_name=last_name,
            mrn=mrn,
            dob=dob
        )

    def create_order(self) -> Order:
        """
        Create a new Order from the form data.
        """
        provider = self.get_or_create_provider()
        patient = self.get_or_create_patient()

        return Order.objects.create(
            provider=provider,
            patient=patient,
            primary_diagnosis_code=self.cleaned_data['primary_diagnosis_code'],
            primary_diagnosis_description=self.cleaned_data.get('primary_diagnosis_description', ''),
            additional_diagnoses=self.cleaned_data.get('additional_diagnoses', []),
            medication_name=self.cleaned_data['medication_name'],
            medication_history=self.cleaned_data.get('medication_history', []),
            patient_records=self.cleaned_data['patient_records'],
            status='draft'
        )
