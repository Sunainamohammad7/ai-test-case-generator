
def build_test_case_prompt(requirement: str) -> str:

    prompt = f"""
    You are an experienced Software Test Engineer.

    Your task is to analyze the given software requirement
    and generate comprehensive software test cases.

    Follow these instructions:

    1. Generate positive test cases.
    2. Generate negative test cases.
    3. Generate boundary test cases wherever applicable.
    4. Include clear test steps.
    5. Provide expected results for every test case.
    6. Assign priority as High, Medium or Low.
    7. Do not invent business rules that are not specified.
    8. Mention any assumptions separately.

    Software Requirement:
    {requirement}

    Generate approximately 6 to 10 test cases.
    """

    return prompt
