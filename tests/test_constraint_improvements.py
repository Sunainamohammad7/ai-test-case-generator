from app.constraint_service import (
    extract_constraints,
    compare_constraints,
)


def mismatch_fields(first, second):
    return {
        item["constraint"]
        for item in compare_constraints(first, second)
    }


def test_email_vs_sms():
    fields = mismatch_fields(
        "User receives password reset link via email.",
        "User receives password reset code via SMS.",
    )

    assert "channel" in fields


def test_expiry_difference():
    fields = mismatch_fields(
        "Password reset link expires after 30 minutes.",
        "Password reset link expires after 10 minutes.",
    )

    assert "expiry_minutes" in fields


def test_role_difference():
    fields = mismatch_fields(
        "Admin can download reports.",
        "Customer can download reports.",
    )

    assert "role" in fields


def test_country_difference():
    fields = mismatch_fields(
        "Customers in India can pay online.",
        "Customers in Germany can pay online.",
    )

    assert "country" in fields


def test_amount_difference():
    fields = mismatch_fields(
        "User can transfer INR 1000.",
        "User can transfer INR 5000.",
    )

    assert "amount" in fields


def test_password_vs_otp():
    fields = mismatch_fields(
        "User can log in using email and password.",
        "User can log in using OTP.",
    )

    assert "security_rules" in fields


def test_equivalent_time_units():
    fields = mismatch_fields(
        "Link expires after 60 minutes.",
        "Link expires after 1 hour.",
    )

    assert "expiry_minutes" not in fields


def test_same_constraints():
    fields = mismatch_fields(
        "User can log in using email and password.",
        "User can sign in using email and password.",
    )

    assert fields == set()
