from app.constraint_service import (
    extract_constraints,
    compare_constraints
)


def test_email_channel_extraction():
    result = extract_constraints(
        "User receives a reset link via email"
    )

    assert result["channel"] == "email"


def test_sms_channel_extraction():
    result = extract_constraints(
        "User receives a reset code via SMS"
    )

    assert result["channel"] == "sms"


def test_expiry_extraction():
    result = extract_constraints(
        "Reset link expires after 30 minutes"
    )

    assert result["expiry_minutes"] == 30


def test_hours_conversion():
    result = extract_constraints(
        "Reset link expires after 2 hours"
    )

    assert result["expiry_minutes"] == 120


def test_constraint_mismatch():
    requirement_a = (
        "User receives a password reset link "
        "via email valid for 30 minutes"
    )

    requirement_b = (
        "User receives a password reset code "
        "via SMS valid for 5 minutes"
    )

    mismatches = compare_constraints(
        requirement_a,
        requirement_b
    )

    mismatch_fields = {
        item["constraint"]
        for item in mismatches
    }

    assert "channel" in mismatch_fields
    assert "expiry_minutes" in mismatch_fields


def test_identical_constraints():
    requirement = (
        "User receives a reset link via email "
        "valid for 30 minutes"
    )

    mismatches = compare_constraints(
        requirement,
        requirement
    )

    assert mismatches == []
