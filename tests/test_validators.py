"""
Test suite for input validators.
"""

from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError

from careplan.validators import (
    validate_npi,
    validate_mrn,
    validate_icd10_code,
    validate_icd10_codes_list,
    validate_dob,
    parse_comma_separated_codes,
    parse_medication_history,
)


class NPIValidatorTests(TestCase):
    """Tests for NPI validation."""

    def test_valid_npi(self):
        """Valid 10-digit NPI should pass."""
        validate_npi('1234567890')  # Should not raise

    def test_npi_too_short(self):
        """NPI with less than 10 digits should fail."""
        with self.assertRaises(ValidationError) as context:
            validate_npi('123456789')
        self.assertIn('10 digits', str(context.exception))

    def test_npi_too_long(self):
        """NPI with more than 10 digits should fail."""
        with self.assertRaises(ValidationError):
            validate_npi('12345678901')

    def test_npi_with_letters(self):
        """NPI with letters should fail."""
        with self.assertRaises(ValidationError):
            validate_npi('123456789a')

    def test_npi_empty(self):
        """Empty NPI should fail."""
        with self.assertRaises(ValidationError):
            validate_npi('')

    def test_npi_with_spaces(self):
        """NPI with spaces should be stripped and validated."""
        validate_npi(' 1234567890 ')  # Should not raise


class MRNValidatorTests(TestCase):
    """Tests for MRN validation."""

    def test_valid_mrn(self):
        """Valid 6-digit MRN should pass."""
        validate_mrn('123456')  # Should not raise

    def test_mrn_too_short(self):
        """MRN with less than 6 digits should fail."""
        with self.assertRaises(ValidationError) as context:
            validate_mrn('12345')
        self.assertIn('6 digits', str(context.exception))

    def test_mrn_too_long(self):
        """MRN with more than 6 digits should fail."""
        with self.assertRaises(ValidationError):
            validate_mrn('1234567')

    def test_mrn_with_letters(self):
        """MRN with letters should fail."""
        with self.assertRaises(ValidationError):
            validate_mrn('12345a')

    def test_mrn_empty(self):
        """Empty MRN should fail."""
        with self.assertRaises(ValidationError):
            validate_mrn('')


class ICD10ValidatorTests(TestCase):
    """Tests for ICD-10 code validation."""

    def test_valid_icd10_basic(self):
        """Basic ICD-10 code (letter + 2 digits) should pass."""
        validate_icd10_code('A00')  # Should not raise

    def test_valid_icd10_with_decimal(self):
        """ICD-10 code with decimal should pass."""
        validate_icd10_code('G70.00')  # Should not raise
        validate_icd10_code('M54.5')  # Should not raise
        validate_icd10_code('I10.1234')  # Should not raise (max 4 after decimal)

    def test_valid_icd10_lowercase_converted(self):
        """Lowercase ICD-10 code should be accepted (converted to uppercase)."""
        validate_icd10_code('g70.00')  # Should not raise

    def test_invalid_icd10_no_letter(self):
        """ICD-10 code without leading letter should fail."""
        with self.assertRaises(ValidationError):
            validate_icd10_code('100')

    def test_invalid_icd10_wrong_format(self):
        """ICD-10 code with wrong format should fail."""
        with self.assertRaises(ValidationError):
            validate_icd10_code('ABC')

    def test_invalid_icd10_too_many_decimals(self):
        """ICD-10 code with too many decimal digits should fail."""
        with self.assertRaises(ValidationError):
            validate_icd10_code('A00.12345')


class ICD10ListValidatorTests(TestCase):
    """Tests for ICD-10 code list validation."""

    def test_valid_list(self):
        """Valid list of ICD-10 codes should pass."""
        result = validate_icd10_codes_list(['A00', 'G70.00', 'I10'])
        self.assertEqual(result, ['A00', 'G70.00', 'I10'])

    def test_empty_list(self):
        """Empty list should return empty list."""
        result = validate_icd10_codes_list([])
        self.assertEqual(result, [])

    def test_list_with_invalid_code(self):
        """List with invalid code should fail."""
        with self.assertRaises(ValidationError):
            validate_icd10_codes_list(['A00', 'INVALID', 'I10'])

    def test_list_normalizes_to_uppercase(self):
        """Codes should be normalized to uppercase."""
        result = validate_icd10_codes_list(['a00', 'g70.00'])
        self.assertEqual(result, ['A00', 'G70.00'])


class DOBValidatorTests(TestCase):
    """Tests for date of birth validation."""

    def test_valid_dob(self):
        """Valid DOB should pass."""
        validate_dob(date(1980, 1, 15))  # Should not raise

    def test_dob_in_future(self):
        """DOB in the future should fail."""
        future_date = date.today() + timedelta(days=1)
        with self.assertRaises(ValidationError) as context:
            validate_dob(future_date)
        self.assertIn('future', str(context.exception))

    def test_dob_too_old(self):
        """DOB indicating age over 120 should fail."""
        old_date = date.today() - timedelta(days=365 * 121)
        with self.assertRaises(ValidationError) as context:
            validate_dob(old_date)
        self.assertIn('120', str(context.exception))

    def test_dob_none(self):
        """None DOB should pass (optional field)."""
        validate_dob(None)  # Should not raise


class ParsersTests(TestCase):
    """Tests for parsing functions."""

    def test_parse_comma_separated_codes(self):
        """Comma-separated codes should be parsed correctly."""
        result = parse_comma_separated_codes('I10, K21.0, G70.00')
        self.assertEqual(result, ['I10', 'K21.0', 'G70.00'])

    def test_parse_comma_separated_codes_empty(self):
        """Empty string should return empty list."""
        result = parse_comma_separated_codes('')
        self.assertEqual(result, [])

    def test_parse_medication_history(self):
        """Medication history should be parsed correctly."""
        result = parse_medication_history('Prednisone, Pyridostigmine, Lisinopril')
        self.assertEqual(result, ['Prednisone', 'Pyridostigmine', 'Lisinopril'])

    def test_parse_medication_history_with_spaces(self):
        """Extra spaces should be handled."""
        result = parse_medication_history('  Prednisone  ,  Pyridostigmine  ')
        self.assertEqual(result, ['Prednisone', 'Pyridostigmine'])
