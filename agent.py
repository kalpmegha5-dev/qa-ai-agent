
import requests
import json
import re


# =========================================================
# CONFIGURATION
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

REQUEST_TIMEOUT = 600
CONTEXT_SIZE = 8192


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def clean_text(value, default="Not specified"):
    if value is None:
        return default

    if isinstance(value, str):
        return value.strip() or default

    if isinstance(value, (int, float)):
        return str(value)

    return default


def normalise_steps(value):
    if isinstance(value, list):
        steps = [
            clean_text(step, "")
            for step in value
            if clean_text(step, "")
        ]
        return steps or ["Execute the described test scenario."]

    if isinstance(value, str):
        lines = [
            line.strip()
            for line in value.splitlines()
            if line.strip()
        ]
        return lines or ["Execute the described test scenario."]

    return ["Execute the described test scenario."]


def normalise_category(category):
    category = clean_text(category, "").lower().strip()
    category = re.sub(r"[_-]+", " ", category)
    category = re.sub(r"\s+", " ", category)

    aliases = {
        "positive": "Positive",
        "positive testing": "Positive",
        "happy path": "Positive",

        "negative": "Negative",
        "negative testing": "Negative",

        "boundary": "Boundary",
        "boundary value": "Boundary",
        "boundary testing": "Boundary",

        "edge": "Edge Case",
        "edge case": "Edge Case",
        "edge cases": "Edge Case",

        "regression": "Regression",
        "regression testing": "Regression"
    }

    return aliases.get(category, "Positive")


def normalise_priority(priority):
    priority = clean_text(priority, "Medium").lower()

    if priority in ["high", "critical", "p1"]:
        return "High"

    if priority in ["low", "p3"]:
        return "Low"

    return "Medium"


def normalise_test_case(case, index):
    if not isinstance(case, dict):
        case = {"scenario": str(case)}

    scenario = (
        case.get("scenario")
        or case.get("test_scenario")
        or case.get("test_case")
        or case.get("title")
        or case.get("description")
    )

    if not scenario:
        return None

    return {
        "id": f"TC-{index:03d}",
        "category": normalise_category(case.get("category")),
        "coverage_area": clean_text(
            case.get("coverage_area")
            or case.get("coverage")
            or case.get("feature")
        ),
        "scenario": clean_text(scenario),
        "preconditions": clean_text(
            case.get("preconditions")
            or case.get("precondition")
            or case.get("setup")
        ),
        "test_data": clean_text(
            case.get("test_data")
            or case.get("testdata")
        ),
        "steps": normalise_steps(
            case.get("steps")
            or case.get("test_steps")
            or case.get("procedure")
        ),
        "expected_result": clean_text(
            case.get("expected_result")
            or case.get("expected")
            or case.get("expected_outcome")
        ),
        "priority": normalise_priority(case.get("priority"))
    }


# =========================================================
# OLLAMA BATCH GENERATION
# =========================================================

def generate_batch(user_story, category_instructions, token_limit):

    prompt = f"""
You are a Senior QA Lead specialising in e-commerce,
retail, payments and omnichannel applications.

USER STORY:
{user_story}

Generate test cases for ONLY these categories:

{category_instructions}

QA GUIDELINES:

- Generate distinct, meaningful and executable test cases.
- Follow the exact quantities requested.
- Group cases in the same order as the requested categories.
- Include 2 to 4 practical test steps per case.
- Include preconditions, test data and expected results.
- Do not invent business rules or numerical limits.
- Record unknown requirements in gaps or assumptions.
- Regression cases must cover potentially impacted existing
  functionality, not unrelated features.
- Avoid duplicate scenarios.

For payment-related stories, consider applicable scenarios:
credit card, gift card, split payment, insufficient balance,
declined payment, gateway timeout, duplicate payment,
payment success followed by order failure, payment reversal
and order/payment status consistency.

Return ONLY valid JSON. No Markdown fences.

Use exactly this structure:

{{
  "test_cases": [
    {{
      "id": "TC-001",
      "category": "Positive",
      "coverage_area": "Payment",
      "scenario": "Specific test scenario",
      "preconditions": "Required setup",
      "test_data": "Relevant test data",
      "steps": [
        "Step 1",
        "Step 2",
        "Step 3"
      ],
      "expected_result": "Expected outcome",
      "priority": "High"
    }}
  ],
  "assumptions": [],
  "gaps": []
}}

Allowed categories:
Positive, Negative, Boundary, Edge Case, Regression.

Return all requested cases and all required fields.
Return valid JSON only.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": token_limit,
                "num_ctx": CONTEXT_SIZE
            }
        },
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    response_data = response.json()
    ai_response = response_data.get("response", "")

    if not ai_response or not ai_response.strip():
        raise ValueError("Ollama returned an empty response.")

    if response_data.get("done_reason") == "length":
        raise ValueError(
            "Ollama reached the output token limit. "
            "The JSON response may be incomplete."
        )

    try:
        result = json.loads(ai_response)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Ollama returned incomplete or invalid JSON: {error}"
        ) from error

    if not isinstance(result, dict):
        raise ValueError("AI response must be a JSON object.")

    if not isinstance(result.get("test_cases"), list):
        raise ValueError("AI did not return a test_cases list.")

    return result


# =========================================================
# MAIN TEST CASE GENERATOR
# =========================================================

def generate_test_cases(user_story):

    if not user_story or not user_story.strip():
        raise ValueError("Please enter a user story.")

    # Batch 1: Positive, Negative and Boundary
    batch_one_instructions = """
1. Positive: exactly 4 test cases.
2. Negative: exactly 4 test cases.
3. Boundary: exactly 3 test cases.

Return them grouped in this order.
Total: 11 test cases.
"""

    # Batch 2: Edge Case and Regression
    batch_two_instructions = """
1. Edge Case: exactly 3 test cases.
2. Regression: exactly 3 test cases.

Return them grouped in this order.
Total: 6 test cases.
"""

    try:
        # Generate first batch.
        batch_one = generate_batch(
            user_story,
            batch_one_instructions,
            2800
        )

        # Generate second batch.
        batch_two = generate_batch(
            user_story,
            batch_two_instructions,
            1800
        )

        raw_cases = (
            batch_one.get("test_cases", [])
            + batch_two.get("test_cases", [])
        )

        if not raw_cases:
            raise ValueError("No test cases were generated.")

        final_cases = []

        for case in raw_cases:
            normalised = normalise_test_case(
                case,
                len(final_cases) + 1
            )

            if normalised:
                final_cases.append(normalised)

        if not final_cases:
            raise ValueError(
                "No usable test scenarios were returned."
            )

        # Assign unique sequential IDs.
        for index, case in enumerate(final_cases, start=1):
            case["id"] = f"TC-{index:03d}"

        # Combine assumptions and gaps.
        assumptions = (
            batch_one.get("assumptions", [])
            + batch_two.get("assumptions", [])
        )

        gaps = (
            batch_one.get("gaps", [])
            + batch_two.get("gaps", [])
        )

        if isinstance(assumptions, str):
            assumptions = [assumptions]

        if isinstance(gaps, str):
            gaps = [gaps]

        if not isinstance(assumptions, list):
            assumptions = []

        if not isinstance(gaps, list):
            gaps = []

        return {
            "test_cases": final_cases,
            "assumptions": assumptions,
            "gaps": gaps
        }

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Ollama timed out during test case generation. "
            "Please check that Ollama is running."
        )

    except requests.exceptions.HTTPError as error:
        details = (
            error.response.text[:1000]
            if error.response is not None
            else "No server details available."
        )
        raise RuntimeError(
            f"Ollama HTTP error: {error}. Details: {details}"
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Could not connect to Ollama: {error}"
        )

    except ValueError as error:
        raise RuntimeError(
            f"Could not process AI response: {error}"
        )
