
import json
import requests
from typing import Any


# ---------------------------------------------------------
# OLLAMA CONFIGURATION
# ---------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

REQUEST_TIMEOUT = 600
ANALYSIS_TOKENS = 2200
CLARIFICATION_TOKENS = 2200
CONTEXT_SIZE = 4096


# ---------------------------------------------------------
# OLLAMA API CALL
# ---------------------------------------------------------

def call_ollama(prompt: str, num_predict: int = ANALYSIS_TOKENS) -> dict:
    """
    Send a prompt to the locally running Ollama model
    and return the generated JSON as a Python dictionary.
    """

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": num_predict,
            "num_ctx": CONTEXT_SIZE
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()
        response_data = response.json()

        ai_response = response_data.get("response", "")

        if not ai_response or not ai_response.strip():
            raise ValueError("Ollama returned an empty response.")

        # Detect output stopped because the token limit was reached.
        done_reason = response_data.get("done_reason", "")

        if done_reason == "length":
            raise ValueError(
                "Ollama reached its output token limit before completing "
                "the response. Reduce the requirement size or increase "
                "the output token limit."
            )

        try:
            result = json.loads(ai_response)

        except json.JSONDecodeError as error:
            raise ValueError(
                "The AI returned incomplete or invalid JSON. "
                "This can happen when the model stops before completing "
                "its response. Please try again."
            ) from error

        if not isinstance(result, dict):
            raise ValueError("The AI response must be a JSON object.")

        return result

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "Ollama response timed out. The local model may need more "
            "time to process this requirement. Try a shorter requirement."
        ) from error

    except requests.exceptions.HTTPError as error:
        response_text = ""

        if error.response is not None:
            response_text = error.response.text[:500]

        raise RuntimeError(
            f"Ollama HTTP error: {error}. {response_text}"
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "Ollama connection failed. Make sure Ollama is running "
            "and the model is available."
        ) from error


# ---------------------------------------------------------
# GENERAL VALIDATION HELPERS
# ---------------------------------------------------------

def validate_fields(data: dict, required_fields: list) -> dict:
    """Ensure the response contains the required fields."""

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object from the AI.")

    for field in required_fields:
        if field not in data:
            data[field] = None

    return data


def safe_text(value: Any, default: str = "") -> str:
    """Convert values safely into displayable text."""

    if value is None:
        return default

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float, bool)):
        return str(value)

    return default


def safe_list(value: Any) -> list:
    """Return a list even when the AI returns an unexpected value."""

    if isinstance(value, list):
        return value

    return []


# ---------------------------------------------------------
# NORMALISATION HELPERS
# ---------------------------------------------------------

def normalise_issue_list(items: Any, prefix: str) -> list:
    """
    Normalise requirement gaps, ambiguities and conflicts.
    """

    normalised = []

    for index, item in enumerate(safe_list(items), start=1):

        if isinstance(item, str):
            item = {"observation": item}

        if not isinstance(item, dict):
            continue

        item_id = (
            item.get("gap_id")
            or item.get("ambiguity_id")
            or item.get("conflict_id")
            or f"{prefix}-{index:03d}"
        )

        normalised.append({
            "gap_id": safe_text(item_id),
            "ambiguity_id": safe_text(item_id),
            "conflict_id": safe_text(item_id),
            "title": safe_text(item.get("title"), "Requirement finding"),
            "observation": safe_text(item.get("observation")),
            "business_impact": safe_text(item.get("business_impact")),
            "qa_impact": safe_text(item.get("qa_impact")),
            "priority": safe_text(item.get("priority"), "Medium")
        })

    return normalised


def normalise_question_list(items: Any) -> list:
    """Normalise BA/PO clarification questions."""

    normalised = []

    for index, item in enumerate(safe_list(items), start=1):

        if isinstance(item, str):
            item = {"question": item}

        if not isinstance(item, dict):
            continue

        related_gap_ids = item.get("related_gap_ids", [])

        if not isinstance(related_gap_ids, list):
            related_gap_ids = []

        normalised.append({
            "question_id": safe_text(
                item.get("question_id"),
                f"Q-{index:03d}"
            ),
            "related_area": safe_text(item.get("related_area")),
            "question": safe_text(item.get("question")),
            "why_it_matters": safe_text(item.get("why_it_matters")),
            "priority": safe_text(item.get("priority"), "Medium"),
            "related_gap_ids": related_gap_ids
        })

    return normalised


def normalise_scenario_list(items: Any) -> list:
    """Normalise a list of test scenarios."""

    normalised = []

    for item in safe_list(items):

        if isinstance(item, str):
            item = {"scenario": item}

        if not isinstance(item, dict):
            continue

        scenario = safe_text(item.get("scenario"))

        if not scenario:
            continue

        normalised.append({
            "scenario": scenario,
            "rationale": safe_text(item.get("rationale")),
            "priority": safe_text(item.get("priority"), "Medium")
        })

    return normalised


def normalise_scenarios(data: Any) -> dict:
    """Ensure all four scenario categories are present."""

    if not isinstance(data, dict):
        data = {}

    return {
        "positive": normalise_scenario_list(data.get("positive")),
        "negative": normalise_scenario_list(data.get("negative")),
        "boundary": normalise_scenario_list(data.get("boundary")),
        "edge_cases": normalise_scenario_list(data.get("edge_cases"))
    }


def normalise_dependencies(items: Any) -> list:
    """Normalise external system and process dependencies."""

    normalised = []

    for item in safe_list(items):

        if isinstance(item, str):
            item = {"system": item}

        if not isinstance(item, dict):
            continue

        normalised.append({
            "system": safe_text(item.get("system")),
            "purpose": safe_text(item.get("purpose")),
            "interface": safe_text(item.get("interface")),
            "qa_considerations": safe_text(
                item.get("qa_considerations")
            ),
            "confirmation_needed": safe_text(
                item.get("confirmation_needed")
            )
        })

    return normalised


def normalise_requirement_result(data: dict) -> dict:
    """Normalise the complete requirement analysis response."""

    data = validate_fields(
        data,
        [
            "requirement_summary",
            "requirement_gaps",
            "ambiguities",
            "conflicting_requirements",
            "external_dependencies",
            "test_scenarios",
            "clarification_questions",
            "overall_risks",
            "assumptions",
            "readiness"
        ]
    )

    risks = data.get("overall_risks", [])
    assumptions = data.get("assumptions", [])

    if isinstance(risks, str):
        risks = [risks]

    if isinstance(assumptions, str):
        assumptions = [assumptions]

    readiness = safe_text(data.get("readiness"), "Not Ready")

    valid_readiness = [
        "Ready",
        "Partially Ready",
        "Not Ready"
    ]

    if readiness not in valid_readiness:
        readiness = "Partially Ready"

    return {
        "requirement_summary": safe_text(
            data.get("requirement_summary")
        ),
        "requirement_gaps": normalise_issue_list(
            data.get("requirement_gaps"),
            "GAP"
        ),
        "ambiguities": normalise_issue_list(
            data.get("ambiguities"),
            "AMB"
        ),
        "conflicting_requirements": normalise_issue_list(
            data.get("conflicting_requirements"),
            "CON"
        ),
        "external_dependencies": normalise_dependencies(
            data.get("external_dependencies")
        ),
        "test_scenarios": normalise_scenarios(
            data.get("test_scenarios")
        ),
        "clarification_questions": normalise_question_list(
            data.get("clarification_questions")
        ),
        "overall_risks": [
            safe_text(item)
            for item in safe_list(risks)
            if safe_text(item)
        ],
        "assumptions": [
            safe_text(item)
            for item in safe_list(assumptions)
            if safe_text(item)
        ],
        "readiness": readiness
    }


# ---------------------------------------------------------
# REQUIREMENT ANALYSIS
# ---------------------------------------------------------

def analyze_requirement(user_story: str) -> dict:
    """
    Analyse a user story like a Senior QA Lead.

    Identify:
    - Requirement gaps
    - Ambiguities
    - Conflicting requirements
    - External dependencies
    - Positive scenarios
    - Negative scenarios
    - Boundary scenarios
    - Edge cases
    - BA/PO clarification questions
    - Risks and readiness
    """

    user_story = safe_text(user_story)

    if not user_story:
        raise ValueError("Please enter a user story or requirement.")

    prompt = f"""
You are a Senior QA Lead with expertise in enterprise,
retail, e-commerce, payments and omnichannel applications.

Analyse the following user story from a QA perspective.

USER STORY:
{user_story}

INSTRUCTIONS:

1. Understand the business objective and expected functionality.

2. Identify requirement gaps:
   Important business rules or acceptance criteria that are missing.

3. Identify ambiguities:
   Statements that can be interpreted in multiple ways.

4. Identify conflicting requirements:
   Requirements that contradict each other.

5. Identify external dependencies:
   Systems, APIs, payment providers, databases, inventory,
   order management or other integrations, only where relevant.

6. Derive test scenarios:
   - Positive: valid user journeys.
   - Negative: invalid inputs, failures and rejected transactions.
   - Boundary: minimum, maximum and threshold conditions.
   - Edge cases: unusual combinations, interruptions,
     retries, duplicate actions and recovery conditions.

7. Ask BA/PO clarification questions ONLY for missing,
   ambiguous or conflicting business requirements.

8. Do not ask BA/PO to design test cases.
   QA coverage scenarios are your responsibility.

9. Do not invent business rules.
   Clearly identify assumptions.

10. Consider risks such as data integrity, security,
    transaction consistency, usability and integrations
    where relevant to the story.

11. Keep the response concise and specific.
    Avoid repeating the same finding in different sections.

12. If the story does not provide enough information
    to identify a dependency, do not invent one.

READINESS:
- Ready: No important requirement questions remain.
- Partially Ready: Some details need confirmation.
- Not Ready: Critical business rules are missing or conflicting.

Return ONLY valid JSON. Do not use Markdown or code fences.

Use exactly this JSON structure:

{{
  "requirement_summary": "Short summary of the business requirement",
  "requirement_gaps": [
    {{
      "gap_id": "GAP-001",
      "title": "Short title",
      "observation": "What is missing",
      "business_impact": "Why it matters to the business",
      "qa_impact": "How it affects testing",
      "priority": "High"
    }}
  ],
  "ambiguities": [
    {{
      "ambiguity_id": "AMB-001",
      "title": "Short title",
      "observation": "What is unclear",
      "business_impact": "Why clarification matters",
      "qa_impact": "Testing impact",
      "priority": "Medium"
    }}
  ],
  "conflicting_requirements": [
    {{
      "conflict_id": "CON-001",
      "title": "Short title",
      "observation": "What conflicts",
      "business_impact": "Business impact",
      "qa_impact": "Testing impact",
      "priority": "High"
    }}
  ],
  "external_dependencies": [
    {{
      "system": "System name",
      "purpose": "Why it is involved",
      "interface": "API, event, file or other interface",
      "qa_considerations": "What QA should verify",
      "confirmation_needed": "What needs confirmation, or None"
    }}
  ],
  "test_scenarios": {{
    "positive": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "High"
      }}
    ],
    "negative": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "High"
      }}
    ],
    "boundary": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "Medium"
      }}
    ],
    "edge_cases": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "Medium"
      }}
    ]
  }},
  "clarification_questions": [
    {{
      "question_id": "Q-001",
      "related_area": "Business area",
      "question": "Specific question for BA/PO",
      "why_it_matters": "Impact of the answer",
      "priority": "High",
      "related_gap_ids": ["GAP-001"]
    }}
  ],
  "overall_risks": [
    "Relevant risk"
  ],
  "assumptions": [
    "Clearly stated assumption"
  ],
  "readiness": "Partially Ready"
}}

Return empty arrays when a section has no findings.
Do not omit any top-level JSON key.
"""

    result = call_ollama(
        prompt,
        num_predict=ANALYSIS_TOKENS
    )

    return normalise_requirement_result(result)


# ---------------------------------------------------------
# CLARIFICATION REVIEW
# ---------------------------------------------------------

def analyze_clarification(
    user_story: str,
    initial_analysis: dict,
    ba_response: str,
    previous_reviews: list = None
) -> dict:
    """
    Reassess the requirement after BA/PO answers clarification
    questions.

    The AI should:
    - Identify which questions are resolved.
    - Record confirmed business rules.
    - Retain genuinely unresolved gaps.
    - Identify new questions only when necessary.
    - Avoid repeating questions already answered.
    - Update QA scenarios and risks.
    """

    user_story = safe_text(user_story)
    ba_response = safe_text(ba_response)

    if not user_story:
        raise ValueError("The original user story is missing.")

    if not ba_response:
        raise ValueError("Please enter the BA/PO clarification response.")

    if not isinstance(initial_analysis, dict):
        initial_analysis = {}

    if previous_reviews is None:
        previous_reviews = []

    # Keep the context compact so the local model can process it.
    initial_context = {
        "requirement_summary": initial_analysis.get(
            "requirement_summary", ""
        ),
        "requirement_gaps": initial_analysis.get(
            "requirement_gaps", []
        ),
        "ambiguities": initial_analysis.get(
            "ambiguities", []
        ),
        "conflicting_requirements": initial_analysis.get(
            "conflicting_requirements", []
        ),
        "clarification_questions": initial_analysis.get(
            "clarification_questions", []
        ),
        "assumptions": initial_analysis.get(
            "assumptions", []
        ),
        "readiness": initial_analysis.get(
            "readiness", "Not Ready"
        )
    }

    # Limit previous review history to avoid excessive prompt size.
    review_context = previous_reviews[-3:]

    prompt = f"""
You are a Senior QA Lead reviewing BA/PO clarification responses.

ORIGINAL USER STORY:
{user_story}

INITIAL REQUIREMENT ANALYSIS:
{json.dumps(initial_context, ensure_ascii=False)}

PREVIOUS CLARIFICATION REVIEWS:
{json.dumps(review_context, ensure_ascii=False)}

LATEST BA/PO RESPONSE:
{ba_response}

YOUR TASK:

1. Compare the BA/PO response with the original gaps,
   ambiguities, conflicts and clarification questions.

2. Mark items as resolved only when the response provides
   a clear and usable business rule.

3. Capture confirmed business rules explicitly.

4. Retain unanswered or partially answered questions
   under remaining_gaps.

5. Ask new clarification questions only when the response
   reveals a genuinely new requirement gap.

6. Never repeat a question that has already been answered
   or resolved in this or an earlier review.

7. Do not ask BA/PO to provide QA test scenarios.
   Derive QA scenarios yourself.

8. Update positive, negative, boundary and edge scenarios
   based on the confirmed business rules.

9. Keep assumptions separate from confirmed business rules.

10. Set readiness:
    - Ready: No important clarification remains.
    - Partially Ready: Some non-critical clarification remains.
    - Not Ready: Critical business rules are still missing.

11. Be concise. Do not repeat the entire original analysis.

Return ONLY valid JSON. No Markdown or code fences.

Use exactly this structure:

{{
  "assessment_summary": "Summary of the latest reassessment",
  "resolved_items": [
    {{
      "item": "Original question or gap",
      "resolution": "What the BA/PO confirmed"
    }}
  ],
  "confirmed_business_rules": [
    "Confirmed rule"
  ],
  "remaining_gaps": [
    {{
      "gap_id": "GAP-001",
      "title": "Short title",
      "observation": "What is still missing",
      "business_impact": "Why it matters",
      "qa_impact": "Testing impact",
      "priority": "High"
    }}
  ],
  "new_clarification_questions": [
    {{
      "question_id": "Q-NEW-001",
      "related_area": "Business area",
      "question": "New question only",
      "why_it_matters": "Why it matters",
      "priority": "Medium",
      "related_gap_ids": []
    }}
  ],
  "updated_test_scenarios": {{
    "positive": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "High"
      }}
    ],
    "negative": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "High"
      }}
    ],
    "boundary": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "Medium"
      }}
    ],
    "edge_cases": [
      {{
        "scenario": "Scenario description",
        "rationale": "Why it should be tested",
        "priority": "Medium"
      }}
    ]
  }},
  "outstanding_risks": [
    "Risk that remains"
  ],
  "readiness": "Partially Ready",
  "recommendation": "Recommended next QA action"
}}

Return empty arrays when there are no items.
Do not omit any top-level key.
"""

    result = call_ollama(
        prompt,
        num_predict=CLARIFICATION_TOKENS
    )

    result = validate_fields(
        result,
        [
            "assessment_summary",
            "resolved_items",
            "confirmed_business_rules",
            "remaining_gaps",
            "new_clarification_questions",
            "updated_test_scenarios",
            "outstanding_risks",
            "readiness",
            "recommendation"
        ]
    )

    readiness = safe_text(
        result.get("readiness"),
        "Partially Ready"
    )

    if readiness not in [
        "Ready",
        "Partially Ready",
        "Not Ready"
    ]:
        readiness = "Partially Ready"

    confirmed_rules = result.get("confirmed_business_rules", [])
    outstanding_risks = result.get("outstanding_risks", [])

    if isinstance(confirmed_rules, str):
        confirmed_rules = [confirmed_rules]

    if isinstance(outstanding_risks, str):
        outstanding_risks = [outstanding_risks]

    resolved_items = safe_list(result.get("resolved_items"))

    normalised_resolved_items = []

    for item in resolved_items:
        if isinstance(item, str):
            normalised_resolved_items.append({
                "item": item,
                "resolution": ""
            })
        elif isinstance(item, dict):
            normalised_resolved_items.append({
                "item": safe_text(item.get("item")),
                "resolution": safe_text(item.get("resolution"))
            })

    return {
        "assessment_summary": safe_text(
            result.get("assessment_summary")
        ),
        "resolved_items": normalised_resolved_items,
        "confirmed_business_rules": [
            safe_text(item)
            for item in safe_list(confirmed_rules)
            if safe_text(item)
        ],
        "remaining_gaps": normalise_issue_list(
            result.get("remaining_gaps"),
            "GAP"
        ),
        "new_clarification_questions": normalise_question_list(
            result.get("new_clarification_questions")
        ),
        "updated_test_scenarios": normalise_scenarios(
            result.get("updated_test_scenarios")
        ),
        "outstanding_risks": [
            safe_text(item)
            for item in safe_list(outstanding_risks)
            if safe_text(item)
        ],
        "readiness": readiness,
        "recommendation": safe_text(result.get("recommendation"))
    }
