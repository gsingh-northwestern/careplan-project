"""
Input validation functions for the Care Plan Generator.

Validates and normalizes:
- NPI (National Provider Identifier) - 10 digit format
- MRN (Medical Record Number) - 6 digit format
- ICD-10 diagnosis codes - standard format
- Date of Birth - reasonable date ranges
"""

import re
from datetime import date
from django.core.exceptions import ValidationError


def validate_npi(value: str) -> None:
    """
    Validate NPI (National Provider Identifier).

    Rules:
    - Must be exactly 10 digits
    - Must be numeric only

    Raises:
        ValidationError: If NPI is invalid
    """
    if not value:
        raise ValidationError("NPI is required")

    # Remove any whitespace
    value = value.strip()

    if not re.match(r'^\d{10}$', value):
        raise ValidationError(
            "NPI must be exactly 10 digits",
            code='invalid_npi'
        )


def validate_mrn(value: str) -> None:
    """
    Validate MRN (Medical Record Number).

    Rules:
    - Must be exactly 6 digits
    - Must be numeric only

    Raises:
        ValidationError: If MRN is invalid
    """
    if not value:
        raise ValidationError("MRN is required")

    # Remove any whitespace
    value = value.strip()

    if not re.match(r'^\d{6}$', value):
        raise ValidationError(
            "MRN must be exactly 6 digits",
            code='invalid_mrn'
        )


def validate_icd10_code(value: str) -> None:
    """
    Validate ICD-10 code format.

    Rules:
    - Starts with a letter (A-Z)
    - Followed by 2 digits
    - Optionally followed by a decimal and up to 4 characters

    Valid examples: A00, A00.0, G70.00, M54.5

    Raises:
        ValidationError: If ICD-10 code is invalid
    """
    if not value:
        raise ValidationError("ICD-10 code is required")

    # Remove any whitespace and convert to uppercase
    value = value.strip().upper()

    # Pattern: Letter + 2 digits + optional (. + 1-4 alphanumeric)
    pattern = r'^[A-Z]\d{2}(\.[A-Z0-9]{1,4})?$'

    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid ICD-10 code format. Expected format: A00 or A00.0000",
            code='invalid_icd10'
        )


def validate_icd10_codes_list(codes: list) -> list:
    """
    Validate a list of ICD-10 codes.

    Args:
        codes: List of ICD-10 code strings

    Returns:
        List of validated and normalized codes

    Raises:
        ValidationError: If any code is invalid
    """
    if not codes:
        return []

    validated = []
    errors = []

    for i, code in enumerate(codes):
        if not isinstance(code, str):
            errors.append(f"Code at position {i + 1} must be a string")
            continue

        code = code.strip().upper()
        if not code:
            continue  # Skip empty strings

        try:
            validate_icd10_code(code)
            validated.append(code)
        except ValidationError as e:
            errors.append(f"Code '{code}': {e.message}")

    if errors:
        raise ValidationError(
            "Invalid ICD-10 codes: " + "; ".join(errors),
            code='invalid_icd10_list'
        )

    return validated


def validate_dob(value: date) -> None:
    """
    Validate date of birth.

    Rules:
    - Cannot be in the future
    - Cannot be more than 120 years ago (reasonable age limit)

    Raises:
        ValidationError: If DOB is invalid
    """
    if not value:
        return  # DOB is optional

    today = date.today()

    if value > today:
        raise ValidationError(
            "Date of birth cannot be in the future",
            code='future_dob'
        )

    # Check for reasonable age (0-120 years)
    age = (today - value).days // 365
    if age > 120:
        raise ValidationError(
            "Date of birth indicates age over 120 years",
            code='unreasonable_dob'
        )


def normalize_npi(value: str) -> str:
    """
    Normalize NPI by removing whitespace and ensuring proper format.
    """
    if not value:
        return ""
    return value.strip()


def normalize_mrn(value: str) -> str:
    """
    Normalize MRN by removing whitespace and ensuring proper format.
    """
    if not value:
        return ""
    return value.strip()


def normalize_icd10(value: str) -> str:
    """
    Normalize ICD-10 code to uppercase.
    """
    if not value:
        return ""
    return value.strip().upper()


def parse_comma_separated_codes(value: str) -> list:
    """
    Parse a comma-separated string of ICD-10 codes into a list.

    Args:
        value: Comma-separated string like "I10, K21.0, G70.00"

    Returns:
        List of individual codes
    """
    if not value:
        return []

    codes = [code.strip().upper() for code in value.split(',')]
    return [code for code in codes if code]  # Remove empty strings


def parse_medication_history(value: str) -> list:
    """
    Parse a comma-separated string of medications into a list.

    Args:
        value: Comma-separated string like "Prednisone, Pyridostigmine"

    Returns:
        List of individual medications
    """
    if not value:
        return []

    meds = [med.strip() for med in value.split(',')]
    return [med for med in meds if med]  # Remove empty strings
