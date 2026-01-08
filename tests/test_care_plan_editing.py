"""
Test suite for care plan editing functionality.
"""

from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from careplan.models import Provider, Patient, Order, CarePlan


class CarePlanEditingTests(TestCase):
    """Tests for care plan editing via HTMX endpoints."""

    def setUp(self):
        """Create test data."""
        self.client = Client()
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
        self.order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis_code='G70.00',
            primary_diagnosis_description='Myasthenia gravis',
            medication_name='IVIG',
            patient_records='Test patient records'
        )
        self.care_plan = CarePlan.objects.create(
            order=self.order,
            content='Original care plan content here.',
            model_used='test-model',
            generation_time_ms=500
        )

    def test_edit_form_renders(self):
        """Edit form endpoint returns edit template with textarea."""
        url = reverse('care_plan_edit_form', args=[self.care_plan.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'textarea')
        self.assertContains(response, 'Original care plan content here.')
        self.assertContains(response, 'Editing Care Plan')

    def test_save_updates_content(self):
        """Save endpoint updates care plan content."""
        url = reverse('save_care_plan_edit', args=[self.care_plan.id])
        response = self.client.post(url, {'content': 'Updated care plan content.'})

        self.assertEqual(response.status_code, 200)

        self.care_plan.refresh_from_db()
        self.assertEqual(self.care_plan.content, 'Updated care plan content.')
        self.assertTrue(self.care_plan.is_edited)
        self.assertIsNotNone(self.care_plan.edited_at)

    def test_save_sets_edited_timestamp(self):
        """Save endpoint sets edited_at timestamp."""
        before_edit = timezone.now()

        url = reverse('save_care_plan_edit', args=[self.care_plan.id])
        self.client.post(url, {'content': 'Updated content'})

        self.care_plan.refresh_from_db()
        self.assertGreaterEqual(self.care_plan.edited_at, before_edit)

    def test_save_empty_content_fails(self):
        """Save endpoint rejects empty content."""
        url = reverse('save_care_plan_edit', args=[self.care_plan.id])
        response = self.client.post(url, {'content': ''})

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'cannot be empty', status_code=400)

        # Content should be unchanged
        self.care_plan.refresh_from_db()
        self.assertEqual(self.care_plan.content, 'Original care plan content here.')
        self.assertFalse(self.care_plan.is_edited)

    def test_save_whitespace_only_fails(self):
        """Save endpoint rejects whitespace-only content."""
        url = reverse('save_care_plan_edit', args=[self.care_plan.id])
        response = self.client.post(url, {'content': '   \n\t  '})

        self.assertEqual(response.status_code, 400)

    def test_display_endpoint_returns_display(self):
        """Display endpoint returns non-edit view."""
        url = reverse('care_plan_display', args=[self.care_plan.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Original care plan content here.')
        self.assertNotContains(response, 'textarea')
        self.assertContains(response, 'Generated Care Plan')

    def test_edited_badge_shown_after_edit(self):
        """Edited badge appears after saving changes."""
        self.care_plan.is_edited = True
        self.care_plan.edited_at = timezone.now()
        self.care_plan.save()

        url = reverse('care_plan_display', args=[self.care_plan.id])
        response = self.client.get(url)

        self.assertContains(response, 'Edited')

    def test_edit_nonexistent_care_plan_returns_404(self):
        """Trying to edit nonexistent care plan returns 404."""
        url = reverse('care_plan_edit_form', args=[99999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_save_nonexistent_care_plan_returns_404(self):
        """Trying to save nonexistent care plan returns 404."""
        url = reverse('save_care_plan_edit', args=[99999])
        response = self.client.post(url, {'content': 'Some content'})

        self.assertEqual(response.status_code, 404)

    def test_display_nonexistent_care_plan_returns_404(self):
        """Trying to display nonexistent care plan returns 404."""
        url = reverse('care_plan_display', args=[99999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class CarePlanModelEditTrackingTests(TestCase):
    """Tests for CarePlan model edit tracking fields."""

    def setUp(self):
        """Create test data."""
        self.provider = Provider.objects.create(
            name='Dr. Test',
            npi='1234567890'
        )
        self.patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            mrn='654321',
            dob=date(1990, 6, 20)
        )
        self.order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis_code='G70.00',
            medication_name='IVIG',
            patient_records='Records'
        )

    def test_new_care_plan_not_edited(self):
        """New care plan should have is_edited=False."""
        care_plan = CarePlan.objects.create(
            order=self.order,
            content='Test content',
            model_used='test-model'
        )

        self.assertFalse(care_plan.is_edited)
        self.assertIsNone(care_plan.edited_at)

    def test_is_edited_defaults_false(self):
        """is_edited field defaults to False."""
        care_plan = CarePlan.objects.create(
            order=self.order,
            content='Test content',
            model_used='test-model'
        )

        # Refresh from DB to ensure default is applied
        care_plan.refresh_from_db()
        self.assertFalse(care_plan.is_edited)

    def test_edited_at_can_be_null(self):
        """edited_at can be null for unedited care plans."""
        care_plan = CarePlan.objects.create(
            order=self.order,
            content='Test content',
            model_used='test-model'
        )

        self.assertIsNone(care_plan.edited_at)
