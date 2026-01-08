"""
Test suite for duplicate detection logic.
"""

from datetime import date
from django.test import TestCase

from careplan.models import Provider, Patient, Order
from careplan.duplicates import (
    check_provider_duplicate,
    check_patient_duplicate,
    check_order_duplicate,
    DuplicateResult,
)


class ProviderDuplicateTests(TestCase):
    """Tests for provider duplicate detection."""

    def setUp(self):
        """Create test providers."""
        self.provider1 = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )
        self.provider2 = Provider.objects.create(
            name='Dr. John Doe',
            npi='0987654321'
        )

    def test_exact_npi_match_blocks(self):
        """Exact NPI match should return blocking result."""
        result = check_provider_duplicate('Dr. Jane Smith', '1234567890')
        self.assertEqual(result.type, 'block')
        self.assertIn('already exists', result.message)

    def test_different_npi_ok(self):
        """Different NPI should return OK."""
        result = check_provider_duplicate('Dr. New Provider', '1111111111')
        self.assertEqual(result.type, 'ok')

    def test_similar_name_different_npi_warns(self):
        """Similar name with different NPI should warn."""
        result = check_provider_duplicate('Dr. Jane Johnson', '1111111111')
        self.assertEqual(result.type, 'warn')
        self.assertIn('Similar provider', result.message)

    def test_exclude_id_works(self):
        """Excluding own ID should not flag as duplicate."""
        result = check_provider_duplicate(
            'Dr. Jane Smith',
            '1234567890',
            exclude_id=self.provider1.id
        )
        self.assertEqual(result.type, 'ok')


class PatientDuplicateTests(TestCase):
    """Tests for patient duplicate detection."""

    def setUp(self):
        """Create test patients."""
        self.patient1 = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456',
            dob=date(1980, 1, 15)
        )

    def test_exact_mrn_match_blocks(self):
        """Exact MRN match should return blocking result."""
        result = check_patient_duplicate('John', 'Doe', '123456')
        self.assertEqual(result.type, 'block')
        self.assertIn('already exists', result.message)

    def test_different_mrn_ok(self):
        """Different MRN should return OK."""
        result = check_patient_duplicate('Jane', 'Smith', '654321')
        self.assertEqual(result.type, 'ok')

    def test_same_name_dob_different_mrn_warns(self):
        """Same name and DOB with different MRN should warn."""
        result = check_patient_duplicate(
            'John',
            'Doe',
            '654321',
            dob=date(1980, 1, 15)
        )
        self.assertEqual(result.type, 'warn')
        self.assertIn('same name and date of birth', result.message)

    def test_same_name_no_dob_ok(self):
        """Same name without DOB should be OK (can't confirm duplicate)."""
        result = check_patient_duplicate('John', 'Doe', '654321')
        self.assertEqual(result.type, 'ok')

    def test_exclude_id_works(self):
        """Excluding own ID should not flag as duplicate."""
        result = check_patient_duplicate(
            'John',
            'Doe',
            '123456',
            exclude_id=self.patient1.id
        )
        self.assertEqual(result.type, 'ok')


class OrderDuplicateTests(TestCase):
    """Tests for order duplicate detection."""

    def setUp(self):
        """Create test data."""
        self.provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456',
            dob=date(1980, 1, 15)
        )
        self.order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis_code='G70.00',
            medication_name='IVIG',
            patient_records='Test records'
        )

    def test_same_patient_medication_warns(self):
        """Same patient and medication should warn."""
        result = check_order_duplicate(
            self.patient.id,
            'IVIG'
        )
        self.assertEqual(result.type, 'warn')
        self.assertIn('IVIG', result.message)

    def test_same_patient_different_medication_ok(self):
        """Same patient with different medication should be OK."""
        result = check_order_duplicate(
            self.patient.id,
            'Different Med'
        )
        self.assertEqual(result.type, 'ok')

    def test_different_patient_same_medication_ok(self):
        """Different patient with same medication should be OK."""
        other_patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            mrn='654321',
            dob=date(1985, 6, 20)
        )
        result = check_order_duplicate(
            other_patient.id,
            'IVIG'
        )
        self.assertEqual(result.type, 'ok')

    def test_exclude_id_works(self):
        """Excluding own ID should not flag as duplicate."""
        result = check_order_duplicate(
            self.patient.id,
            'IVIG',
            exclude_id=self.order.id
        )
        self.assertEqual(result.type, 'ok')


class DuplicateResultTests(TestCase):
    """Tests for DuplicateResult helper class."""

    def test_ok_result(self):
        """OK result should have correct properties."""
        result = DuplicateResult('ok')
        self.assertTrue(result.is_ok)
        self.assertFalse(result.is_warning)
        self.assertFalse(result.is_blocking)

    def test_warn_result(self):
        """Warn result should have correct properties."""
        result = DuplicateResult('warn', 'Test warning')
        self.assertFalse(result.is_ok)
        self.assertTrue(result.is_warning)
        self.assertFalse(result.is_blocking)
        self.assertEqual(result.message, 'Test warning')

    def test_block_result(self):
        """Block result should have correct properties."""
        result = DuplicateResult('block', 'Test error', [{'id': 1}])
        self.assertFalse(result.is_ok)
        self.assertFalse(result.is_warning)
        self.assertTrue(result.is_blocking)
        self.assertEqual(len(result.similar_items), 1)

    def test_to_dict(self):
        """to_dict should return proper dictionary."""
        result = DuplicateResult('warn', 'Test', [{'id': 1}], severity='high')
        d = result.to_dict()
        self.assertEqual(d['type'], 'warn')
        self.assertEqual(d['message'], 'Test')
        self.assertEqual(d['similar_items'], [{'id': 1}])
        self.assertEqual(d['severity'], 'high')

    def test_severity_default(self):
        """Severity should default to medium."""
        result = DuplicateResult('warn', 'Test')
        self.assertEqual(result.severity, 'medium')
        self.assertFalse(result.is_high_severity)

    def test_high_severity(self):
        """High severity result should have correct property."""
        result = DuplicateResult('warn', 'Test', severity='high')
        self.assertTrue(result.is_high_severity)
