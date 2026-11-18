import re


def extract_constraints(requirement: str) -> dict:
    """
    Extract material constraints using deterministic rules.

    This does not call Gemini. Unrecognized constraints
    remain a limitation of the rule-based approach.
    """

    text = requirement.lower()

    constraints = {
        "channel": None,
        "expiry_minutes": None,
        "role": None,
        "country": None,
        "currency": None,
        "amount": None,
        "security_rules": [],
    }

    # Communication channel
    channels = []

    if re.search(r"\b(?:email|e-mail)\b", text):
        channels.append("email")

    if re.search(r"\b(?:sms|text message)\b", text):
        channels.append("sms")

    if channels:
        constraints["channel"] = (
            channels[0] if len(channels) == 1 else "multiple"
        )

    # Time limit
    time_match = re.search(
        r"\b(\d+)\s*(minutes?|mins?|hours?|hrs?)\b",
        text,
    )

    if time_match:
        value = int(time_match.group(1))
        unit = time_match.group(2)

        if unit.startswith(("hour", "hr")):
            value *= 60

        constraints["expiry_minutes"] = value

    # Actor / role
    roles = []

    for role in ["admin", "manager", "customer", "user"]:
        if re.search(rf"\b{role}s?\b", text):
            roles.append(role)

    if roles:
        constraints["role"] = (
            roles[0] if len(roles) == 1 else "multiple"
        )

    # Country
    countries = {
        "india": "IN",
        "germany": "DE",
        "united states": "US",
        "usa": "US",
        "united kingdom": "GB",
        "uk": "GB",
    }

    detected_countries = {
        code
        for name, code in countries.items()
        if re.search(rf"\b{re.escape(name)}\b", text)
    }

    if detected_countries:
        constraints["country"] = (
            next(iter(detected_countries))
            if len(detected_countries) == 1
            else "multiple"
        )

    # Currency
    currencies = {
        "inr": "INR",
        "rupees": "INR",
        "eur": "EUR",
        "euros": "EUR",
        "usd": "USD",
        "dollars": "USD",
    }

    detected_currencies = {
        code
        for name, code in currencies.items()
        if re.search(rf"\b{re.escape(name)}\b", text)
    }

    if detected_currencies:
        constraints["currency"] = (
            next(iter(detected_currencies))
            if len(detected_currencies) == 1
            else "multiple"
        )

    # Monetary amount
    amount_match = re.search(
        r"(?:\b(?:inr|eur|usd|rs)\b|[$€₹])"
        r"\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
        text,
    )

    if not amount_match:
        amount_match = re.search(
            r"\b(\d+(?:,\d{3})*(?:\.\d+)?)"
            r"\s*(?:inr|eur|usd|rupees|euros|dollars)\b",
            text,
        )

    if amount_match:
        constraints["amount"] = float(
            amount_match.group(1).replace(",", "")
        )

    # Security and authorization constraints
    security_patterns = {
        "password": r"\bpasswords?\b",
        "otp": r"\b(?:otp|one.time.password)\b",
        "two_factor": r"\b(?:two.factor|2fa|mfa|multi.factor)\b",
        "authentication": r"\bauthenticat(?:ion|e|ed)\b",
        "authorization": r"\bauthoriz(?:ation|e|ed)\b",
        "verification": r"\bverif(?:y|ication|ied)\b",
        "permission": r"\bpermissions?\b",
        "access_control": r"\baccess control\b",
        "encrypted": r"\bencrypt(?:ed|ion)?\b",
    }

    constraints["security_rules"] = sorted(
        name
        for name, pattern in security_patterns.items()
        if re.search(pattern, text)
    )

    return constraints


def compare_constraints(
    requirement_a: str,
    requirement_b: str,
) -> list[dict]:
    """
    Compare extracted material constraints.

    requirement_a: cached or previous requirement
    requirement_b: requested or revised requirement
    """

    constraints_a = extract_constraints(requirement_a)
    constraints_b = extract_constraints(requirement_b)

    mismatches = []

    for field in constraints_a:
        value_a = constraints_a[field]
        value_b = constraints_b[field]

        if value_a != value_b:
            mismatches.append({
                "constraint": field,
                "cached_value": value_a,
                "requested_value": value_b,
            })

    return mismatches
