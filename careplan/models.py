"""
Data models for the Care Plan Generator application.

Core entities:
- Provider: Healthcare provider / referring physician
- Patient: Patient demographics and identifiers
- Order: Care plan order linking patient, provider, diagnosis, and medication
- CarePlan: AI-generated care plan content with metadata
"""

from django.db import models
from django.core.validators import RegexValidator


class Provider(models.Model):
    """
    Healthcare provider (referring physician).

    NPI (National Provider Identifier) is unique and exactly 10 digits.
    This is critical for pharma reporting and preventing duplicate entries.
    """
    name = models.CharField(
        max_length=255,
        help_text="Full name of the provider (e.g., 'Dr. Jane Smith')"
    )
    npi = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='NPI must be exactly 10 digits'
            )
        ],
        help_text="National Provider Identifier - exactly 10 digits"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['npi']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"


class Patient(models.Model):
    """
    Patient information.

    MRN (Medical Record Number) is unique and exactly 6 digits.
    Used to identify patients and detect duplicates.
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(
        max_length=6,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='MRN must be exactly 6 digits'
            )
        ],
        help_text="Medical Record Number - exactly 6 digits"
    )
    dob = models.DateField(
        help_text="Date of birth (required for care plan generation)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['mrn']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['last_name', 'first_name', 'dob']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} (MRN: {self.mrn})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Order(models.Model):
    """
    A care plan order for a patient.

    Links a patient with a provider, diagnosis, and medication.
    Contains the patient records text used to generate the care plan.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('completed', 'Completed'),
    ]

    # Relationships
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.PROTECT,  # Don't allow deleting providers with orders
        related_name='orders'
    )

    # Diagnosis information
    primary_diagnosis_code = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]\d{2}(\.\d{1,4})?$',
                message='Invalid ICD-10 code format. Expected format: A00 or A00.0000'
            )
        ],
        help_text="Primary ICD-10 diagnosis code (e.g., G70.00)"
    )
    primary_diagnosis_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Description of the primary diagnosis"
    )
    additional_diagnoses = models.JSONField(
        default=list,
        blank=True,
        help_text="List of additional ICD-10 codes"
    )

    # Medication information
    medication_name = models.CharField(
        max_length=255,
        help_text="Name of the medication (e.g., IVIG)"
    )
    medication_history = models.JSONField(
        default=list,
        blank=True,
        help_text="List of previous medications"
    )

    # Patient records (input for LLM)
    patient_records = models.TextField(
        help_text="Clinical notes and patient records for care plan generation"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['patient', 'medication_name']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.patient.full_name} - {self.medication_name}"


class CarePlan(models.Model):
    """
    AI-generated care plan for an order.

    Contains the generated content and metadata about the generation.
    """
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='care_plan'
    )
    content = models.TextField(
        help_text="The generated care plan content"
    )
    model_used = models.CharField(
        max_length=50,
        help_text="The AI model used for generation (e.g., claude-sonnet-4-20250514)"
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    generation_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time taken to generate the care plan in milliseconds"
    )

    # Edit tracking fields
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether the care plan content has been manually edited"
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last manual edit"
    )

    class Meta:
        verbose_name = "Care Plan"
        verbose_name_plural = "Care Plans"

    def __str__(self):
        return f"Care Plan for Order #{self.order.id}"
