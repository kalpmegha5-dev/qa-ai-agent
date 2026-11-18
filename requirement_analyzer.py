
import requests
import json


# ==================================================
# CONFIGURATION
# ==================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

REQUEST_TIMEOUT = 300
ANALYSIS_TOKENS = 2500
CLARIFICATION_TOKENS = 3000


# ==================================================
# OLLAMA CONNECTION
# ==================================================

def call_ollama(prompt, num_predict=2500):
    """Send prompt to local Ollama and return JSON."""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": num_predict,
                    "num_ctx": 8192
                }
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        response_data = response.json()
        ai_response = response_data.get("response", "")

        if not ai_response or not ai_response.strip():
            raise ValueError("Ollama returned an empty response.")

        result = json.loads(ai_response)

        if not isinstance(result, dict):
            raise ValueError("AI response is not a JSON object.")

        # Detect incomplete generation where possible.
        if response_data.get("done") is False:
            raise ValueError(
                "AI response generation did not complete."
            )

        return result

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Ollama response timed out. Try a shorter requirement "
            "or reduce the analysis output size."
        )

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Ollama connection failed: {e}"
        )

    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(
            f"Invalid AI response: {e}"
        )


# ==================================================
# RESPONSE VALIDATION
# ==================================================

def validate_fields(result, required_fields, function_name):
    """Check that required JSON fields exist."""

    for field in required_fields:
        if field not in result:
            raise ValueError(
                f"{function_name} is missing required field: {field}"
            )


def safe_text(value, default=""):
    """Safely convert values into displayable text."""

    if value is None:
        return default

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


# ==================================================
# NORMALISATION FUNCTIONS
# ==================================================

def normalise_issue_list(items, id_field, prefix):
    """Standardise requirement gaps, ambiguities and conflicts."""

    if not isinstance(items, list):
        return []

    normalised = []

    for index, item in enumerate(items, start=1):

        if isinstance(item, str):
            item = {
                "title": item,
                "observation": item
            }

        if not isinstance(item, dict):
            continue

        item = dict(item)

        item[id_field] = safe_text(
            item.get(id_field),
            f"{prefix}-{index:03d}"
        )

        item["title"] = safe_text(
            item.get("title"),
            "Finding"
        )

        item["observation"] = safe_text(
            item.get("observation")
        )

        item["business_impact"] = safe_text(
            item.get("business_impact"),
            "To be assessed"
        )

        item["qa_impact"] = safe_text(
            item.get("qa_impact"),
            "To be assessed"
        )

        item["priority"] = safe_text(
            item.get("priority"),
            "Medium"
        )

        normalised.append(item)

    return normalised


def normalise_question_list(items):
    """Standardise BA/PO clarification questions."""

    if not isinstance(items, list):
        return []

    normalised = []

    for index, item in enumerate(items, start=1):

        if isinstance(item, str):
            item = {
                "question": item
            }

        if not isinstance(item, dict):
            continue

        item = dict(item)

        question = safe_text(item.get("question"))

        if not question:
            continue

        item["question_id"] = safe_text(
            item.get("question_id"),
            f"Q-{index:03d}"
        )

        item["related_area"] = safe_text(
            item.get("related_area"),
            "General"
        )

        item["question"] = question

        item["why_it_matters"] = safe_text(
            item.get("why_it_matters"),
            "Business confirmation is required."
        )

        item["priority"] = safe_text(
            item.get("priority"),
            "Medium"
        )

        if not isinstance(item.get("related_gap_ids"), list):
            item["related_gap_ids"] = []

        normalised.append(item)

    return normalised


def normalise_scenario_list(items):
    """Standardise AI-generated QA scenarios."""

    if not isinstance(items, list):
        return []

    normalised = []

    for item in items:

        if isinstance(item, str):
            item = {
                "scenario": item
            }

        if not isinstance(item, dict):
            continue

        item = dict(item)

        scenario = safe_text(item.get("scenario"))

        if not scenario:
            continue

        item["scenario"] = scenario

        item["rationale"] = safe_text(
            item.get("rationale"),
            "Validates expected system behaviour."
        )

        item["priority"] = safe_text(
            item.get("priority"),
            "Medium"
        )

        normalised.append(item)

    return normalised


def normalise_scenarios(scenarios):
    """Ensure all four QA coverage categories exist."""

    if not isinstance(scenarios, dict):
        scenarios = {}

    categories = [
        "positive",
        "negative",
        "boundary",
        "edge_cases"
    ]

    normalised = {}

    for category in categories:
        normalised[category] = normalise_scenario_list(
            scenarios.get(category, [])
        )

    return normalised


def normalise_dependencies(dependencies):
    """Standardise external dependency information."""

    if not isinstance(dependencies, list):
        return []

    normalised = []

    for item in dependencies:

        if isinstance(item, str):
            item = {
                "system": item
            }

        if not isinstance(item, dict):
            continue

        item = dict(item)

        item["system"] = safe_text(
            item.get("system"),
            "External system"
        )

        item["purpose"] = safe_text(
            item.get("purpose"),
            "To be confirmed"
        )

        item["interface"] = safe_text(
            item.get("interface"),
            "To be confirmed"
        )

        item["qa_considerations"] = safe_text(
            item.get("qa_considerations"),
            "Integration testing required"
        )

        item["confirmation_needed"] = safe_text(
            item.get("confirmation_needed"),
            "Yes"
        )

        normalised.append(item)

    return normalised


def normalise_requirement_result(result):
    """Standardise the complete requirement analysis."""

    result["requirement_gaps"] = normalise_issue_list(
        result.get("requirement_gaps"),
        "gap_id",
        "GAP"
    )

    result["ambiguities"] = normalise_issue_list(
        result.get("ambiguities"),
        "ambiguity_id",
        "AMB"
    )

    result["conflicting_requirements"] = normalise_issue_list(
        result.get("conflicting_requirements"),
        "conflict_id",
        "CON"
    )

    result["external_dependencies"] = normalise_dependencies(
        result.get("external_dependencies")
    )

    result["clarification_questions"] = normalise_question_list(
        result.get("clarification_questions")
    )

    result["test_scenarios"] = normalise_scenarios(
        result.get("test_scenarios")
    )

    for field in [
        "overall_risks",
        "assumptions"
    ]:
        if not isinstance(result.get(field), list):
            result[field] = []

    result["requirement_summary"] = safe_text(
        result.get("requirement_summary")
    )

    result["readiness"] = safe_text(
        result.get("readiness"),
        "Not Ready"
    )

    return result


# ==================================================
# 1. COMPREHENSIVE REQUIREMENT ANALYSIS
# ==================================================

def analyze_requirement(user_story):
    """
    Analyse a user story from a Senior QA Manager perspective.
    """

    if not user_story or not user_story.strip():
        raise ValueError("Please enter a requirement or user story.")

    prompt = f"""
You are a Senior QA Manager with 13+ years of experience
in e-commerce, retail, payments and enterprise applications.

Analyse the following requirement independently.

USER STORY:
{user_story}

OBJECTIVE:
Identify requirement gaps, ambiguities, risks, dependencies,
business clarification questions and comprehensive QA scenarios.

IMPORTANT RULES:

1. Do not merely summarise the user story.
2. Identify missing business decisions.
3. Derive test scenarios independently.
4. Never ask BA/PO to create test scenarios.
5. Do not invent business rules.
6. Separate assumptions from confirmed requirements.
7. Avoid duplicate findings and questions.
8. Do not classify invalid behaviour as positive.
9. Evaluate all four QA scenario categories.
10. Return concise but meaningful JSON.

ANALYSIS AREAS:

1. REQUIREMENT GAPS

Identify missing:
- Business rules and acceptance criteria
- Validations and mandatory conditions
- Payment and transaction rules
- Failure and exception handling
- Retry and recovery behaviour
- Order processing rules

Explain the gap, business impact, QA impact and priority.

2. AMBIGUITIES

Identify unclear statements, undefined behaviour,
multiple interpretations and missing acceptance criteria.

3. CONFLICTS

Identify only genuine contradictory requirements.
Return an empty array if no conflict exists.

4. EXTERNAL DEPENDENCIES

Identify relevant external systems and interfaces.
Mark inferred systems as assumptions.
Do not claim unmentioned integrations are confirmed.

5. QA SCENARIO GENERATION

Derive scenarios independently.

POSITIVE:
Successful valid business workflows.

NEGATIVE:
Invalid input, declined payments, failures, timeouts,
duplicate requests and unsuccessful processing.

BOUNDARY:
Minimum and maximum amounts, zero values, exact balances,
partial balances and amount limits where applicable.

EDGE CASES:
Delayed responses, retries, concurrent requests,
partial failures, inconsistent system states and recovery.

For every scenario include:
- Scenario description
- Rationale
- Priority

For payment-related order placement, evaluate these
coverage areas where relevant:

- Credit card payment
- Gift card payment
- Split payment
- Insufficient gift card balance
- Expired or declined card
- Payment gateway timeout
- Duplicate payment request
- Payment succeeds but order creation fails
- Gift card deduction followed by order failure
- Zero-value order
- Payment reversal and recovery

These are testing considerations, not confirmed business rules.

Aim for meaningful coverage of at least:
3 positive, 5 negative, 3 boundary and 5 edge scenarios
when applicable.

Do not create irrelevant or duplicate scenarios.

6. BA/PO CLARIFICATION QUESTIONS

Consolidate all material business questions.

Consider:
- Supported payment methods
- Split payment rules
- Gift card balance handling
- Card validation and decline behaviour
- Payment timeout and retry rules
- Duplicate transaction prevention
- Order creation failure
- Refund and reversal handling
- Zero-value orders

Ask only questions requiring business confirmation.
Explain why each matters.
Link questions to related gap IDs.
Do not ask BA/PO to provide test scenarios.

7. RISKS AND READINESS

Identify financial, operational, customer experience
and data integrity risks.

Readiness:
READY = Sufficiently clear for testing.
PARTIALLY READY = Some clarifications remain.
NOT READY = Critical business rules are missing.

OUTPUT:

Return ONLY valid JSON using this exact structure:

{{
  "requirement_summary": "Short business summary",

  "requirement_gaps": [
    {{
      "gap_id": "GAP-001",
      "title": "Gap title",
      "observation": "Missing requirement",
      "business_impact": "Business impact",
      "qa_impact": "Testing impact",
      "priority": "High"
    }}
  ],

  "ambiguities": [
    {{
      "ambiguity_id": "AMB-001",
      "title": "Ambiguity title",
      "observation": "What is unclear",
      "business_impact": "Impact",
      "qa_impact": "Testing impact",
      "priority": "Medium"
    }}
  ],

  "conflicting_requirements": [],

  "external_dependencies": [
    {{
      "system": "System name",
      "purpose": "Purpose",
      "interface": "Known or assumed interface",
      "qa_considerations": "Testing considerations",
      "confirmation_needed": "Yes"
    }}
  ],

  "test_scenarios": {{
    "positive": [
      {{
        "scenario": "Successful scenario",
        "rationale": "Reason",
        "priority": "High"
      }}
    ],
    "negative": [
      {{
        "scenario": "Failure scenario",
        "rationale": "Reason",
        "priority": "High"
      }}
    ],
    "boundary": [
      {{
        "scenario": "Boundary scenario",
        "rationale": "Reason",
        "priority": "Medium"
      }}
    ],
    "edge_cases": [
      {{
        "scenario": "Edge case",
        "rationale": "Reason",
        "priority": "High"
      }}
    ]
  }},

  "clarification_questions": [
    {{
      "question_id": "Q-001",
      "related_area": "Payment",
      "question": "Specific BA/PO question",
      "why_it_matters": "Reason",
      "priority": "High",
      "related_gap_ids": ["GAP-001"]
    }}
  ],

  "overall_risks": [
    "Specific risk"
  ],

  "assumptions": [
    "Clearly labelled assumption"
  ],

  "readiness": "Not Ready"
}}

FINAL CHECK:

Verify all four scenario categories.
Check positive and negative classification.
Check for duplicate scenarios and questions.
Check that business questions are consolidated.
Check that assumptions are not treated as facts.
Check that readiness reflects requirement completeness.

Return JSON only. No Markdown.
"""

    result = call_ollama(
        prompt,
        num_predict=ANALYSIS_TOKENS
    )

    required_fields = [
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

    validate_fields(
        result,
        required_fields,
        "Requirement analysis"
    )

    return normalise_requirement_result(result)


# ==================================================
# 2. CONSOLIDATED BA / PO CLARIFICATION EVALUATION
# ==================================================

def analyze_clarification(
    user_story,
    initial_analysis,
    ba_response,
    previous_reviews=None
):
    """
    Evaluate consolidated BA/PO responses.
    Preserve confirmed rules and avoid repeated questions.
    """

    if not ba_response or not ba_response.strip():
        raise ValueError(
            "Please enter the BA/PO clarification response."
        )

    previous_reviews = previous_reviews or []

    prompt = f"""
You are a Senior QA Manager evaluating BA/PO
clarifications for an e-commerce requirement.

ORIGINAL USER STORY:
{user_story}

INITIAL QA ANALYSIS:
{json.dumps(initial_analysis, ensure_ascii=False)}

PREVIOUS CLARIFICATION ROUNDS:
{json.dumps(previous_reviews, ensure_ascii=False)}

LATEST BA/PO RESPONSE:
{ba_response}

YOUR RESPONSIBILITIES:

1. Evaluate each original clarification question.
2. Identify fully answered, partially answered
   and unanswered questions.
3. Extract explicitly confirmed business rules.
4. Preserve all previously confirmed business rules.
5. Identify genuinely new gaps.
6. Never repeat resolved questions.
7. Ask only material unanswered business questions.
8. Do not ask BA/PO to create test scenarios.
9. Do not invent answers or business rules.
10. Update all four QA scenario categories.
11. Reflect confirmed rules in updated scenarios.
12. Do not continue clarification unnecessarily.

READINESS:

READY:
Critical business behaviour is sufficiently clear.

PARTIALLY READY:
Some non-critical clarifications remain.

NOT READY:
Important business decisions remain unresolved.

Return ONLY valid JSON using this structure:

{{
  "assessment_summary": "Assessment of BA/PO responses",

  "resolved_items": [
    {{
      "question_id": "Q-001",
      "original_question": "Original question",
      "confirmed_business_rule": "Confirmed rule"
    }}
  ],

  "confirmed_business_rules": [
    "Explicitly confirmed business rule"
  ],

  "remaining_gaps": [
    {{
      "gap_id": "GAP-001",
      "title": "Outstanding gap",
      "observation": "What remains unclear",
      "priority": "High"
    }}
  ],

  "new_clarification_questions": [
    {{
      "question_id": "Q-NEW-001",
      "related_area": "Payment",
      "question": "New question",
      "why_it_matters": "Reason",
      "priority": "High"
    }}
  ],

  "updated_test_scenarios": {{
    "positive": [
      {{
        "scenario": "Positive scenario",
        "rationale": "Reason",
        "priority": "High"
      }}
    ],
    "negative": [
      {{
        "scenario": "Negative scenario",
        "rationale": "Reason",
        "priority": "High"
      }}
    ],
    "boundary": [
      {{
        "scenario": "Boundary scenario",
        "rationale": "Reason",
        "priority": "Medium"
      }}
    ],
    "edge_cases": [
      {{
        "scenario": "Edge case",
        "rationale": "Reason",
        "priority": "High"
      }}
    ]
  }},

  "outstanding_risks": [
    "Unresolved risk"
  ],

  "readiness": "Partially Ready",

  "recommendation": "Recommended next action"
}}

FINAL CHECK:

- Preserve all confirmed rules.
- Do not repeat resolved questions.
- Do not invent answers.
- Do not treat assumptions as confirmed facts.
- Ask only material business questions.
- Update scenarios using confirmed rules.
- Use only Ready, Partially Ready or Not Ready.
- Return valid JSON only.
"""

    result = call_ollama(
        prompt,
        num_predict=CLARIFICATION_TOKENS
    )

    required_fields = [
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

    validate_fields(
        result,
        required_fields,
        "Clarification analysis"
    )

    for field in [
        "resolved_items",
        "confirmed_business_rules",
        "remaining_gaps",
        "outstanding_risks"
    ]:
        if not isinstance(result.get(field), list):
            result[field] = []

    result["new_clarification_questions"] = (
        normalise_question_list(
            result.get("new_clarification_questions")
        )
    )

    result["updated_test_scenarios"] = (
        normalise_scenarios(
            result.get("updated_test_scenarios")
        )
    )

    result["assessment_summary"] = safe_text(
        result.get("assessment_summary")
    )

    result["readiness"] = safe_text(
        result.get("readiness"),
        "Partially Ready"
    )

    result["recommendation"] = safe_text(
        result.get("recommendation")
    )

    return result
