"""
Test suite for few-shot learning in care plan generation.
"""

from datetime import date
from django.test import TestCase

from careplan.models import Provider, Patient, Order, CarePlan
from careplan.llm_service import (
    get_recent_care_plans,
    format_care_plan_examples,
    MAX_EXAMPLE_LENGTH,
)


class GetRecentCarePlansTests(TestCase):
    """Tests for fetching recent care plans."""

    def setUp(self):
        """Create test data."""
        self.provider = Provider.objects.create(
            name='Dr. Test Provider',
            npi='1234567890'
        )
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456',
            dob=date(1980, 1, 15)
        )

    def _create_order_with_plan(self, medication='IVIG', content='Test care plan content'):
        """Helper to create order with care plan."""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis_code='G70.00',
            primary_diagnosis_description='Test Diagnosis',
            medication_name=medication,
            patient_records='Test records'
        )
        return CarePlan.objects.create(
            order=order,
            content=content,
            model_used='test-model'
        )

    def test_returns_empty_when_no_plans(self):
        """Returns empty list when no care plans exist."""
        result = get_recent_care_plans(limit=3)
        self.assertEqual(result, [])

    def test_returns_available_plans(self):
        """Returns available plans when fewer than limit exist."""
        self._create_order_with_plan('Med1')
        self._create_order_with_plan('Med2')

        result = get_recent_care_plans(limit=3)
        self.assertEqual(len(result), 2)

    def test_respects_limit(self):
        """Returns only up to limit plans."""
        for i in range(5):
            self._create_order_with_plan(f'Med{i}')

        result = get_recent_care_plans(limit=3)
        self.assertEqual(len(result), 3)

    def test_excludes_specified_order(self):
        """Excludes the specified order ID."""
        cp1 = self._create_order_with_plan('Med1')
        cp2 = self._create_order_with_plan('Med2')

        result = get_recent_care_plans(limit=3, exclude_order_id=cp1.order.id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, cp2.id)

    def test_ordered_by_most_recent(self):
        """Returns plans ordered by generated_at descending."""
        cp1 = self._create_order_with_plan('Med1')
        cp2 = self._create_order_with_plan('Med2')
        cp3 = self._create_order_with_plan('Med3')

        result = get_recent_care_plans(limit=3)

        # Most recent should be first
        self.assertEqual(result[0].id, cp3.id)
        self.assertEqual(result[1].id, cp2.id)
        self.assertEqual(result[2].id, cp1.id)

    def test_includes_related_data(self):
        """Returns plans with related order, patient, provider data."""
        self._create_order_with_plan('IVIG')

        result = get_recent_care_plans(limit=1)

        # Should be able to access related objects without additional queries
        self.assertEqual(result[0].order.medication_name, 'IVIG')
        self.assertEqual(result[0].order.patient.first_name, 'John')
        self.assertEqual(result[0].order.provider.name, 'Dr. Test Provider')


class FormatCarePlanExamplesTests(TestCase):
    """Tests for formatting care plan examples."""

    def setUp(self):
        """Create test data."""
        self.provider = Provider.objects.create(
            name='Dr. Test Provider',
            npi='1234567890'
        )
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456',
            dob=date(1980, 1, 15)
        )

    def _create_care_plan(self, medication='IVIG', content='Care plan content here'):
        """Helper to create care plan."""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis_code='G70.00',
            primary_diagnosis_description='Myasthenia Gravis',
            medication_name=medication,
            patient_records='Records'
        )
        return CarePlan.objects.create(
            order=order,
            content=content,
            model_used='test'
        )

    def test_returns_empty_string_for_empty_list(self):
        """Returns empty string when no plans provided."""
        result = format_care_plan_examples([])
        self.assertEqual(result, "")

    def test_formats_single_example(self):
        """Formats single care plan correctly."""
        care_plan = self._create_care_plan()

        result = format_care_plan_examples([care_plan])

        self.assertIn('EXAMPLE 1', result)
        self.assertIn('John Doe', result)
        self.assertIn('G70.00', result)
        self.assertIn('Myasthenia Gravis', result)
        self.assertIn('IVIG', result)
        self.assertIn('Care plan content here', result)

    def test_formats_multiple_examples(self):
        """Formats multiple care plans with numbering."""
        cp1 = self._create_care_plan('Med1', 'Content 1')
        cp2 = self._create_care_plan('Med2', 'Content 2')
        cp3 = self._create_care_plan('Med3', 'Content 3')

        result = format_care_plan_examples([cp1, cp2, cp3])

        self.assertIn('EXAMPLE 1', result)
        self.assertIn('EXAMPLE 2', result)
        self.assertIn('EXAMPLE 3', result)
        self.assertIn('Content 1', result)
        self.assertIn('Content 2', result)
        self.assertIn('Content 3', result)

    def test_truncates_long_content(self):
        """Truncates care plan content over MAX_EXAMPLE_LENGTH chars."""
        long_content = 'A' * (MAX_EXAMPLE_LENGTH + 1000)
        care_plan = self._create_care_plan(content=long_content)

        result = format_care_plan_examples([care_plan])

        self.assertIn('[... truncated for brevity ...]', result)
        # Should not contain the full content
        self.assertNotIn('A' * (MAX_EXAMPLE_LENGTH + 100), result)

    def test_does_not_truncate_short_content(self):
        """Does not truncate content under MAX_EXAMPLE_LENGTH chars."""
        short_content = 'B' * 100
        care_plan = self._create_care_plan(content=short_content)

        result = format_care_plan_examples([care_plan])

        self.assertIn(short_content, result)
        self.assertNotIn('[... truncated for brevity ...]', result)

    def test_includes_separator_between_examples(self):
        """Includes separator between multiple examples."""
        cp1 = self._create_care_plan('Med1')
        cp2 = self._create_care_plan('Med2')

        result = format_care_plan_examples([cp1, cp2])

        self.assertIn('---', result)


class FewShotIntegrationTests(TestCase):
    """Integration tests for few-shot learning flow."""

    def setUp(self):
        """Create test data."""
        self.provider = Provider.objects.create(
            name='Dr. Test Provider',
            npi='1234567890'
        )
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456',
            dob=date(1980, 1, 15)
        )

    def test_get_and_format_flow(self):
        """Test getting recent plans and formatting them works together."""
        # Create some care plans
        for i in range(3):
            order = Order.objects.create(
                patient=self.patient,
                provider=self.provider,
                primary_diagnosis_code='G70.00',
                primary_diagnosis_description='Test Diagnosis',
                medication_name=f'Med{i}',
                patient_records='Records'
            )
            CarePlan.objects.create(
                order=order,
                content=f'Care plan content for Med{i}',
                model_used='test'
            )

        # Get recent plans
        plans = get_recent_care_plans(limit=3)
        self.assertEqual(len(plans), 3)

        # Format them
        result = format_care_plan_examples(plans)

        # Should have all 3 examples
        self.assertIn('EXAMPLE 1', result)
        self.assertIn('EXAMPLE 2', result)
        self.assertIn('EXAMPLE 3', result)

    def test_exclude_current_order(self):
        """Test that current order is excluded from examples."""
        # Create existing care plans
        for i in range(2):
            order = Order.objects.create(
                patient=self.patient,
                provider=self.provider,
                primary_diagnosis_code='G70.00',
                medication_name=f'Med{i}',
                patient_records='Records'
            )
            CarePlan.objects.create(
                order=order,
                content=f'Existing content {i}',
                model_used='test'
            )

        # Create the "current" order
        current_order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis_code='G70.00',
            medication_name='CurrentMed',
            patient_records='Records'
        )
        CarePlan.objects.create(
            order=current_order,
            content='Current care plan - should be excluded',
            model_used='test'
        )

        # Get plans excluding current order
        plans = get_recent_care_plans(limit=3, exclude_order_id=current_order.id)

        # Should only have the 2 other plans
        self.assertEqual(len(plans), 2)

        # Format and verify current plan is not included
        result = format_care_plan_examples(plans)
        self.assertNotIn('Current care plan - should be excluded', result)
        self.assertNotIn('CurrentMed', result)
