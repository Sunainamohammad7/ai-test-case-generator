# AI-Powered Test Case Generator

## Project Overview

An AI-powered application that generates software
test cases from user-provided requirements using
Google Gemini.

## Technologies Used

- Python
- FastAPI
- Google Gemini API
- Pydantic
- Pytest
- Uvicorn

## Features

- Accepts software requirements through a REST API.
- Uses Gemini to understand requirements.
- Generates positive, negative and boundary test cases.
- Returns structured JSON responses.
- Validates input and AI-generated output.
- Includes automated API tests.

## How to Run

1. Create and activate a virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Configure GEMINI_API_KEY in .env.

4. Start the application:

   python -m uvicorn app.main:app --reload

5. Open:

   http://127.0.0.1:8000/docs

## Run Tests

python -m pytest -v
