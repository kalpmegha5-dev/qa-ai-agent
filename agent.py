
import requests
import json


def generate_test_cases(user_story):

    prompt = f"""
    Act as a Senior QA Engineer with expertise in e-commerce testing.

    Analyse the following user story and generate detailed test cases.

    User Story:
    {user_story}

    Include:
    1. Positive test cases
    2. Negative test cases
    3. Boundary test cases
    4. Edge cases

    Return only valid JSON in this structure:

    {{
        "test_cases": [
            {{
                "id": "TC-001",
                "category": "Positive",
                "scenario": "Test scenario",
                "preconditions": "Required preconditions",
                "steps": ["Step 1", "Step 2"],
                "expected_result": "Expected outcome",
                "priority": "High"
            }}
        ],
        "assumptions": ["Assumption 1"],
        "gaps": ["Missing requirement or clarification"]
    }}
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            },
            timeout=300
        )

        response.raise_for_status()

        result = response.json()
        return json.loads(result["response"])

    except requests.exceptions.RequestException as e:
        raise Exception(f"Could not connect to Ollama: {e}")

    except (KeyError, json.JSONDecodeError) as e:
        raise Exception(f"Could not read the AI response: {e}")
