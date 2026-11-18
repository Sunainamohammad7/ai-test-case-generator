import re

from app.constraint_service import compare_constraints
from app.models import (
    ChangeImpactRequest,
    ChangeImpactResponse,
    ImpactedTestCase,
    NewTestRequirement,
)


CAPABILITIES = {
    "password_reset": (
        r"\b(?:reset|recover)\b.{0,30}\bpassword\b"
        r"|\bpassword\b.{0,30}\b(?:reset|recovery)\b"
    ),
    "login": r"\b(?:login|log in|sign in)\b",
    "export": r"\b(?:export|download)\b",
    "delete": r"\b(?:delete|remove)\b",
    "upload": r"\bupload\b",
    "notifications": r"\bnotifications?\b",
}


AUTHENTICATION_METHODS = {
    "google_login": (
        r"\bgoogle\b.{0,30}"
        r"\b(?:login|log in|sign in|authentication)\b"
        r"|\b(?:login|log in|sign in|authentication)\b"
        r".{0,30}\bgoogle\b"
    ),
    "email_password_login": (
        r"\bemail\b.{0,30}\bpassword\b"
        r"|\bpassword\b.{0,30}\bemail\b"
    ),
}

def extract_removed_authentication_methods(
    previous: str,
    revised: str,
) -> set[str]:
    removed_methods = set()

    previous_lower = previous.lower()
    revised_lower = revised.lower()

    google_was_supported = bool(
        re.search(
            AUTHENTICATION_METHODS["google_login"],
            previous_lower,
        )
    )

    google_explicitly_removed = bool(
        re.search(
            r"\bgoogle\b.{0,50}"
            r"\b(?:no longer supported|"
            r"not supported|removed|disabled|unavailable)\b",
            revised_lower,
        )
        or re.search(
            r"\b(?:no longer supported|"
            r"not supported|removed|disabled|unavailable)\b"
            r".{0,50}\bgoogle\b",
            revised_lower,
        )
    )

    if google_was_supported and google_explicitly_removed:
        removed_methods.add("google_login")

    return removed_methods


def extract_capabilities(text: str) -> set[str]:
    return {
        name
        for name, pattern in CAPABILITIES.items()
        if re.search(pattern, text, re.IGNORECASE)
    }


def is_expiry_related(text: str, old_minutes) -> bool:
    text = text.lower()

    expiry_words = re.search(
        r"\b(expir(?:e|es|ed|y|ation)|"
        r"validity|valid\s+for|"
        r"time\s+limit|timeout|"
        r"boundary|elapsed)\b",
        text,
    )

    old_duration = (
        re.search(
            rf"\b{re.escape(str(old_minutes))}\s*"
            r"(?:minutes?|mins?)\b",
            text,
        )
        if old_minutes is not None
        else None
    )

    return bool(expiry_words or old_duration)


def is_constraint_relevant(
    text: str,
    mismatch: dict,
) -> bool:
    field = mismatch["constraint"]
    old_value = mismatch["cached_value"]
    new_value = mismatch["requested_value"]

    text = text.lower()

    if field == "expiry_minutes":
        return is_expiry_related(text, old_value)

    if field == "channel":
        channels = {
            "email": ["email", "e-mail", "inbox"],
            "sms": ["sms", "text message"],
        }
        words = (
            channels.get(str(old_value), [])
            + channels.get(str(new_value), [])
        )
        return any(word in text for word in words)

    values = [old_value, new_value]

    for value in values:
        if value is None:
            continue

        if isinstance(value, list):
            if any(str(item).lower() in text for item in value):
                return True
        elif re.search(
            rf"\b{re.escape(str(value).lower())}\b",
            text,
        ):
            return True

    return False


def analyze_change_impact(
    request: ChangeImpactRequest,
) -> ChangeImpactResponse:

    previous = request.previous_requirement
    revised = request.revised_requirement

    mismatches = compare_constraints(previous, revised)

    removed = (
        extract_capabilities(previous)
        - extract_capabilities(revised)
    )

    added = (
        extract_capabilities(revised)
        - extract_capabilities(previous)
    )

    removed_auth_methods = (
        extract_removed_authentication_methods(
            previous,
            revised,
        )
    )

    impacted = []
    new_tests = []

    same_requirement = (
        " ".join(previous.lower().split())
        == " ".join(revised.lower().split())
    )

    for test in request.existing_test_cases:

        test_text = " ".join([
            test.title,
            " ".join(test.preconditions),
            " ".join(test.steps),
            test.expected_result,
        ]).lower()

        removed_matches = [
            capability
            for capability in removed
            if re.search(
                CAPABILITIES[capability],
                test_text,
                re.IGNORECASE,
            )
        ]

        relevant_changes = [
            mismatch["constraint"]
            for mismatch in mismatches
            if is_constraint_relevant(
                test_text,
                mismatch,
            )
        ]


        removed_auth_matches = [
            method
            for method in removed_auth_methods
            if re.search(
                AUTHENTICATION_METHODS[method],
                test_text,
                re.IGNORECASE,
            )
        ]

        email_password_still_supported = bool(
            re.search(
                AUTHENTICATION_METHODS["email_password_login"],
                previous,
                re.IGNORECASE,
            )
            and re.search(
                AUTHENTICATION_METHODS["email_password_login"],
                revised,
                re.IGNORECASE,
            )
        )

        email_password_test = bool(
            re.search(
                AUTHENTICATION_METHODS["email_password_login"],
                test_text,
                re.IGNORECASE,
            )
        )

        if removed_auth_matches:
            classification = "Obsolete"
            rationale = (
                "The authentication method covered by "
                "this test has been explicitly removed: "
                + ", ".join(removed_auth_matches)
                + "."
            )

        elif removed_matches:
            classification = "Obsolete"
            rationale = (
                "The revised requirement no longer "
                "mentions this capability: "
                + ", ".join(removed_matches)
                + ". Confirm removal with the product owner."
            )

        elif same_requirement:
            classification = "Unchanged"
            rationale = (
                "The requirement has not changed."
            )

        elif relevant_changes:
            classification = "Needs Update"
            rationale = (
                "This test depends on changed constraints: "
                + ", ".join(relevant_changes)
                + ". Review its steps and expected result."
            )

        elif (
            email_password_still_supported
            and email_password_test
            and removed_auth_methods == {"google_login"}
            and not mismatches
            and not added
            and not removed
        ):
            classification = "Unchanged"
            rationale = (
                "Email and password authentication remains "
                "supported. The removed Google authentication "
                "method does not affect this test."
            )

        elif mismatches and not removed and not added:
            classification = "Unchanged"
            rationale = (
                "No dependency on the recognized changed "
                "constraints was detected in this test."
            )

        else:
            classification = "Needs Update"
            rationale = (
                "The requirement changed in a way this "
                "rule-based analyzer cannot fully assess. "
                "Manual review is required."
            )


        impacted.append(
            ImpactedTestCase(
                test_case_id=test.test_case_id,
                title=test.title,
                classification=classification,
                rationale=rationale,
            )
        )

    for capability in sorted(added):
        new_tests.append(
            NewTestRequirement(
                description=(
                    f"Add test coverage for {capability}."
                ),
                rationale=(
                    "This capability appears in the revised "
                    "requirement but not the previous one."
                ),
            )
        )

    for mismatch in mismatches:
        field = mismatch["constraint"]

        new_tests.append(
            NewTestRequirement(
                description=(
                    f"Review and add coverage for "
                    f"{field}: {mismatch['requested_value']}."
                ),
                rationale=(
                    f"The {field} constraint changed from "
                    f"{mismatch['cached_value']} to "
                    f"{mismatch['requested_value']}."
                ),
            )
        )

    return ChangeImpactResponse(
        previous_requirement=previous,
        revised_requirement=revised,
        impacted_test_cases=impacted,
        new_tests_required=new_tests,
        changed_constraints=mismatches,
    )
