import json
from collections import Counter

import pandas as pd
import streamlit as st

from agent import generate_test_cases
from requirement_analyzer import analyze_requirement, analyze_clarification


st.set_page_config(
    page_title="QA AI Agent | Intelligent Test Assistant",
    page_icon="km_logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Only stable, limited overrides; Streamlit owns the layout and headings. */
.block-container {max-width: 1600px !important; padding: 1.2rem 2rem 3rem !important;}
[data-testid="stSidebar"] {background-color:#edf9f6;}
[data-testid="stSidebar"] .stImage {margin-bottom:.3rem;}
[data-testid="stMetric"] {background:#f0fbf9;border:1px solid #d2eae6;border-radius:14px;padding:16px;}
[data-testid="stMetricValue"] {color:#087f89;}
.stButton > button[kind="primary"] {background:#078f9e;border-color:#078f9e;border-radius:10px;}
.stDownloadButton button,.stButton button {border-radius:10px;}
[data-testid="stExpander"] {border-radius:12px;}
</style>
""", unsafe_allow_html=True)


# -------------------------- Data helpers --------------------------

def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def text(value, fallback="Not specified"):
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def display_items(items, empty="None identified"):
    items = as_list(items)
    if not items:
        st.caption(empty)
        return
    for item in items:
        if isinstance(item, dict):
            st.markdown(f"- {text(item.get('title') or item.get('question') or item.get('item') or item.get('observation') or item)}")
        else:
            st.markdown(f"- {text(item)}")


def csv_bytes(rows, columns=None):
    return pd.DataFrame(rows, columns=columns).to_csv(index=False).encode("utf-8-sig")


def findings_rows(result):
    rows = []
    for kind, field, id_key in [
        ("Requirement gap", "requirement_gaps", "gap_id"),
        ("Ambiguity", "ambiguities", "ambiguity_id"),
        ("Conflict", "conflicting_requirements", "conflict_id"),
    ]:
        for i, item in enumerate(as_list(result.get(field)), 1):
            if not isinstance(item, dict):
                continue
            rows.append({
                "Type": kind,
                "ID": text(item.get(id_key), f"ISSUE-{i:03d}"),
                "Finding": text(item.get("title"), ""),
                "Observation": text(item.get("observation"), ""),
                "Business Impact": text(item.get("business_impact"), ""),
                "QA Impact": text(item.get("qa_impact"), ""),
                "Priority": text(item.get("priority"), ""),
            })
    return rows


def question_rows(questions):
    rows = []
    for i, q in enumerate(as_list(questions), 1):
        if isinstance(q, dict):
            rows.append({
                "Question ID": text(q.get("question_id"), f"Q-{i:03d}"),
                "Area": text(q.get("related_area"), "General"),
                "Question": text(q.get("question"), ""),
                "Why it matters": text(q.get("why_it_matters"), ""),
                "Priority": text(q.get("priority"), ""),
            })
        else:
            rows.append({"Question ID": f"Q-{i:03d}", "Area": "General",
                         "Question": text(q), "Why it matters": "", "Priority": ""})
    return rows


def render_questions(questions):
    rows = question_rows(questions)
    if not rows:
        st.success("No outstanding clarification questions.")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_scenarios(scenarios):
    scenarios = as_dict(scenarios)
    tabs = st.tabs(["Positive", "Negative", "Boundary", "Edge cases"])
    for tab, key in zip(tabs, ["positive", "negative", "boundary", "edge_cases"]):
        with tab:
            items = as_list(scenarios.get(key))
            if not items:
                st.caption("No scenarios identified.")
            for i, item in enumerate(items, 1):
                if isinstance(item, dict):
                    st.markdown(f"**{i}. {text(item.get('scenario'))}**")
                    st.caption(f"Priority: {text(item.get('priority'))}")
                    if item.get("rationale"):
                        st.write(item["rationale"])
                else:
                    st.write(f"{i}. {text(item)}")


def render_dependencies(dependencies):
    items = as_list(dependencies)
    if not items:
        st.caption("No external dependencies identified.")
        return
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            st.write(f"- {text(item)}")
            continue
        with st.expander(text(item.get("system"), f"Dependency {i}")):
            for label, field in [
                ("Purpose", "purpose"), ("Interface", "interface"),
                ("QA considerations", "qa_considerations"),
                ("Confirmation needed", "confirmation_needed"),
            ]:
                st.markdown(f"**{label}:** {text(item.get(field))}")


def render_clarification_history(history):
    if not history:
        return
    st.markdown("#### Clarification history")
    for i, entry in enumerate(history, 1):
        review = as_dict(as_dict(entry).get("ai_assessment"))
        with st.expander(f"Round {i}", expanded=i == len(history)):
            st.markdown("**BA / PO response**")
            st.write(text(entry.get("ba_response")))
            st.markdown("**AI assessment**")
            st.write(text(review.get("assessment_summary")))
            st.markdown(f"**Readiness:** {text(review.get('readiness'))}")
            st.markdown("**Confirmed business rules**")
            display_items(review.get("confirmed_business_rules"))
            st.markdown("**Resolved questions / items**")
            resolved = as_list(review.get("resolved_items"))
            if not resolved:
                st.caption("None returned.")
            for item in resolved:
                if isinstance(item, dict):
                    # Supports both response schemas used by the analyzer.
                    identifier = text(item.get("question_id") or item.get("item"), "")
                    resolution = text(
                        item.get("confirmed_business_rule") or item.get("resolution"), ""
                    )
                    st.write(f"- {identifier}: {resolution}".strip(": "))
                else:
                    st.write(f"- {text(item)}")
            st.markdown("**Remaining gaps**")
            display_items(review.get("remaining_gaps"))
            if review.get("updated_test_scenarios"):
                st.markdown("**Updated QA scenarios**")
                render_scenarios(review["updated_test_scenarios"])
            st.markdown("**Outstanding risks**")
            display_items(review.get("outstanding_risks"))
            st.info(f"Recommendation: {text(review.get('recommendation'))}")


def render_clarification_form(user_story, analysis, history, questions):
    if not questions:
        return
    round_no = len(history) + 1
    st.markdown("#### Submit consolidated BA / PO answers")
    st.caption("Answer all open questions together. Include question IDs when available.")
    with st.form(f"clarification_form_{round_no}"):
        answer = st.text_area(
            "BA / PO response",
            placeholder="Q-001: ...\nQ-002: ...",
            height=160,
            key=f"ba_response_{round_no}",
        )
        submit = st.form_submit_button("Evaluate clarifications", type="primary")
    if submit:
        if not answer.strip():
            st.warning("Enter the BA / PO answers before evaluating.")
            return
        try:
            with st.spinner("Reviewing BA / PO responses..."):
                review = analyze_clarification(
                    user_story=user_story,
                    initial_analysis=analysis,
                    ba_response=answer,
                    previous_reviews=history,
                )
            if not isinstance(review, dict) or not review:
                raise ValueError("The AI returned an empty clarification review.")
            st.session_state.clarification_history = history + [
                {"ba_response": answer, "ai_assessment": review}
            ]
            st.rerun()
        except Exception as exc:
            st.error(f"Clarification evaluation failed: {exc}")


def test_case_rows(result):
    rows = []
    for i, tc in enumerate(as_list(result.get("test_cases")), 1):
        if not isinstance(tc, dict):
            continue
        steps = tc.get("steps", [])
        if isinstance(steps, list):
            steps = "\n".join(f"{n}. {text(s)}" for n, s in enumerate(steps, 1))
        rows.append({
            "Test Case ID": text(tc.get("id"), f"TC-{i:03d}"),
            "Category": text(tc.get("category"), "Uncategorized"),
            "Coverage Area": text(tc.get("coverage_area"), ""),
            "Scenario": text(tc.get("scenario"), ""),
            "Preconditions": text(tc.get("preconditions"), ""),
            "Test Data": text(tc.get("test_data"), ""),
            "Test Steps": text(steps, ""),
            "Expected Result": text(tc.get("expected_result"), ""),
            "Priority": text(tc.get("priority"), ""),
        })
    return rows


def render_test_cases(result):
    rows = test_case_rows(result)
    if not rows:
        st.warning("No test cases were returned.")
        return

    counts = Counter(row["Category"] for row in rows)
    st.markdown("### Coverage at a glance")
    a, b, c, d = st.columns(4)
    a.metric("Total test cases", len(rows))
    b.metric("Categories", len(counts))
    c.metric("High priority", sum(r["Priority"].lower() == "high" for r in rows))
    d.metric("Open gaps", len(as_list(result.get("gaps"))))

    st.markdown("#### Test case explorer")
    filter_a, filter_b, filter_c = st.columns([1, 1, 2])
    with filter_a:
        category = st.selectbox(
            "Category", ["All"] + sorted(counts),
            key="test_category_filter",
        )
    with filter_b:
        priority = st.selectbox(
            "Priority", ["All"] + sorted({r["Priority"] for r in rows}),
            key="test_priority_filter",
        )
    with filter_c:
        search = st.text_input(
            "Search test cases", placeholder="Search scenario, ID or coverage area...",
            key="test_search_filter",
        ).strip().lower()

    filtered = [
        row for row in rows
        if (category == "All" or row["Category"] == category)
        and (priority == "All" or row["Priority"] == priority)
        and (not search or any(search in text(row.get(k), "").lower()
                               for k in ("Test Case ID", "Scenario", "Coverage Area")))
    ]
    st.caption(f"Showing {len(filtered)} of {len(rows)} test cases")

    if not filtered:
        st.info("No test cases match these filters.")
    for row in filtered:
        title = f'{row["Test Case ID"]}  ·  {row["Category"]}  ·  {row["Scenario"]}'
        with st.expander(title):
            col1, col2 = st.columns(2)
            col1.markdown(f'**Coverage area:** {row["Coverage Area"]}')
            col2.markdown(f'**Priority:** {row["Priority"]}')
            st.markdown("**Preconditions**")
            st.write(row["Preconditions"])
            st.markdown("**Test data**")
            st.write(row["Test Data"])
            st.markdown("**Test steps**")
            st.text(row["Test Steps"])
            st.markdown("**Expected result**")
            st.write(row["Expected Result"])

    st.download_button(
        "⬇️ Download all test cases (CSV)",
        data=csv_bytes(rows),
        file_name="AI_Generated_Test_Cases.csv",
        mime="text/csv",
        key="download_test_cases",
        help="Exports all generated cases, regardless of the current filters.",
    )
    with st.expander("Assumptions and requirement gaps"):
        st.markdown("**Assumptions**")
        display_items(result.get("assumptions"))
        st.markdown("**Requirement gaps**")
        display_items(result.get("gaps"))


# -------------------------- Sidebar --------------------------

with st.sidebar:
    st.image("km_logo.png", width=90)
    st.title("QA AI Agent")
    st.caption("Intelligent Test Assistant")
    st.divider()
    st.markdown("**Workflow**")
    st.write("01  ·  Enter a user story")
    st.write("02  ·  Analyze requirements")
    st.write("03  ·  Clarify business rules")
    st.write("04  ·  Generate & export")
    st.divider()
    st.caption("Powered by local Ollama · Qwen 2.5")
    st.caption("AI outputs require QA and BA/PO review.")


# -------------------------- Header and story --------------------------

# Native Streamlit layout avoids the clipped custom banner.
st.title("Intelligent Test Assistant")
st.markdown("**From requirements to confident releases**")
st.write("Find requirement gaps, collaborate with BA / PO teams, and generate actionable QA test coverage.")
step1, step2, step3, step4 = st.columns(4, gap="small")
for column, label in zip(
    (step1, step2, step3, step4),
    ("01 · Enter a story", "02 · Analyze", "03 · Clarify", "04 · Generate & export"),
):
    with column:
        st.info(label)

with st.container(border=True):
    st.caption("START HERE")
    st.subheader("01 · Your requirement")
    user_story = st.text_area(
        "Paste a user story or business requirement",
        height=165,
        placeholder=(
            "As a customer, I want to pay using a gift card and a credit card "
            "so that I can complete my purchase."
        ),
        key="user_story",
    )
    st.caption("Your story is sent to the Ollama instance configured on your machine.")
    reset_col, hint_col = st.columns([1, 4])
    with reset_col:
        if st.button("Clear results", use_container_width=True):
            for key in [
                "requirement_result", "analysis_story", "clarification_history",
                "test_case_result", "test_case_story",
                "test_category_filter", "test_priority_filter", "test_search_filter",
            ]:
                st.session_state.pop(key, None)
            st.rerun()
    with hint_col:
        st.caption("Changing the story hides results from the previous story until you run it again.")

analysis = as_dict(st.session_state.get("requirement_result"))
analysis_current = bool(analysis and st.session_state.get("analysis_story") == user_story)
tests = as_dict(st.session_state.get("test_case_result"))
tests_current = bool(tests and st.session_state.get("test_case_story") == user_story)

st.caption("YOUR WORKSPACE")
st.subheader("02 · Explore your QA insights")
analysis_tab, clarification_tab, generator_tab = st.tabs([
    "🔎 Requirement analysis",
    "💬 BA / PO clarifications",
    "🧪 Test cases",
])

with analysis_tab:
    st.write("Identify gaps, ambiguities, conflicts, dependencies, risks and QA scenarios.")
    if st.button("Analyze requirement", type="primary", key="analyse"):
        if not user_story.strip():
            st.warning("Enter a user story first.")
        else:
            try:
                with st.spinner("Analyzing requirements with Ollama..."):
                    output = analyze_requirement(user_story)
                if not isinstance(output, dict) or not output:
                    raise ValueError("The AI returned an empty analysis.")
                st.session_state.requirement_result = output
                st.session_state.analysis_story = user_story
                st.session_state.clarification_history = []
                st.rerun()
            except Exception as exc:
                st.error(f"Requirement analysis failed: {exc}")

    if analysis_current:
        findings = findings_rows(analysis)
        questions = as_list(analysis.get("clarification_questions"))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Requirement findings", len(findings))
        m2.metric("Clarification questions", len(questions))
        m3.metric("Dependencies", len(as_list(analysis.get("external_dependencies"))))
        m4.metric("Risks", len(as_list(analysis.get("overall_risks"))))

        st.markdown("#### Requirement summary")
        st.write(text(analysis.get("requirement_summary")))
        st.info(f"Initial QA readiness: {text(analysis.get('readiness'))}")

        st.markdown("#### Consolidated findings")
        if findings:
            st.dataframe(pd.DataFrame(findings), use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download requirement findings (CSV)",
                data=csv_bytes(findings),
                file_name="QA_Requirement_Analysis.csv",
                mime="text/csv",
                key="download_requirement_report",
            )
        else:
            st.success("No gaps, ambiguities or conflicts identified.")

        with st.expander("External dependencies"):
            render_dependencies(analysis.get("external_dependencies"))

        st.markdown("#### AI-derived QA coverage")
        render_scenarios(analysis.get("test_scenarios"))

        col_risk, col_assumptions = st.columns(2)
        with col_risk:
            st.markdown("#### Overall risks")
            display_items(analysis.get("overall_risks"))
        with col_assumptions:
            st.markdown("#### AI assumptions")
            display_items(analysis.get("assumptions"))

        st.caption("Validate all AI-generated findings with your BA / PO before sign-off.")
    else:
        st.info("Run requirement analysis to see findings and QA coverage.")

with clarification_tab:
    if not analysis_current:
        st.info("First analyze the requirement in the Requirement analysis tab.")
    else:
        history = as_list(st.session_state.get("clarification_history"))
        render_clarification_history(history)
        if history:
            latest = as_dict(as_dict(history[-1]).get("ai_assessment"))
            questions = as_list(latest.get("new_clarification_questions"))
        else:
            questions = as_list(analysis.get("clarification_questions"))

        st.markdown("#### Outstanding BA / PO questions")
        render_questions(questions)
        render_clarification_form(user_story, analysis, history, questions)

with generator_tab:
    st.write(
        "Generate positive, negative, boundary, edge-case and regression test cases. "
        "Review the results before execution."
    )
    if not analysis_current:
        st.caption("You can generate test cases directly, or analyze requirements first.")
    if st.button("Generate test cases", type="primary", key="generate"):
        if not user_story.strip():
            st.warning("Enter a user story first.")
        else:
            try:
                with st.spinner("Generating test cases with Ollama. This may take a few minutes..."):
                    output = generate_test_cases(user_story)
                if not isinstance(output, dict) or not output:
                    raise ValueError("The AI returned an empty test case response.")
                st.session_state.test_case_result = output
                st.session_state.test_case_story = user_story
                st.rerun()
            except Exception as exc:
                st.session_state.pop("test_case_result", None)
                st.error(f"Test case generation failed: {exc}")

    if tests_current:
        render_test_cases(tests)
    else:
        st.info("Generate test cases to view coverage, search, filter and export.")

st.divider()
st.caption(
    "QA AI Agent · Working prototype · Powered by Ollama · "
    "AI-generated results must be reviewed against approved business requirements."
)
