
import streamlit as st
import pandas as pd

from agent import generate_test_cases
from requirement_analyzer import (
    analyze_requirement,
    analyze_clarification
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="QA AI Agent",
    page_icon="🧪",
    layout="wide"
)


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def safe_dict(value):
    return value if isinstance(value, dict) else {}


def safe_list(value):
    return value if isinstance(value, list) else []


def safe_text(value, default="Not provided"):
    return str(value) if value is not None else default


# ==================================================
# CONSOLIDATED REQUIREMENT FINDINGS
# ==================================================

def render_consolidated_findings(result):

    findings = []

    categories = [
        ("Requirement Gap", "requirement_gaps", "gap_id"),
        ("Ambiguity", "ambiguities", "ambiguity_id"),
        ("Conflict", "conflicting_requirements", "conflict_id")
    ]

    for category, key, id_field in categories:

        for index, item in enumerate(
            safe_list(result.get(key)), start=1
        ):

            if not isinstance(item, dict):
                continue

            findings.append({
                "Type": category,
                "ID": item.get(
                    id_field,
                    f"ISSUE-{index:03d}"
                ),
                "Finding": item.get("title", "Issue"),
                "Observation": item.get("observation", ""),
                "Business Impact": item.get("business_impact", ""),
                "QA Impact": item.get("qa_impact", ""),
                "Priority": item.get(
                    "priority",
                    "Not specified"
                )
            })

    st.subheader("🔎 Consolidated Requirement Findings")

    if findings:

        st.dataframe(
            pd.DataFrame(findings),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "No requirement gaps, ambiguities or conflicts identified."
        )


# ==================================================
# CONSOLIDATED BA / PO CLARIFICATION QUESTIONS
# ==================================================

def render_clarification_questions(questions):

    questions = safe_list(questions)

    st.subheader(
        "💬 Consolidated BA / PO Clarification Questions"
    )

    if not questions:

        st.success(
            "No outstanding clarification questions."
        )
        return

    question_rows = []

    for index, question in enumerate(
        questions,
        start=1
    ):

        if not isinstance(question, dict):
            continue

        question_rows.append({
            "Question ID": question.get(
                "question_id",
                f"Q-{index:03d}"
            ),
            "Related Area": question.get(
                "related_area",
                "General"
            ),
            "Clarification Required": question.get(
                "question",
                ""
            ),
            "Why It Matters": question.get(
                "why_it_matters",
                ""
            ),
            "Priority": question.get(
                "priority",
                "Not specified"
            )
        })

    if question_rows:

        st.dataframe(
            pd.DataFrame(question_rows),
            use_container_width=True,
            hide_index=True
        )

    st.info(
        "Please answer all clarification questions together "
        "in the response box below."
    )


# ==================================================
# QA SCENARIO DISPLAY
# ==================================================

def render_scenario_section(title, scenarios):

    st.markdown(f"#### {title}")

    scenarios = safe_list(scenarios)

    if not scenarios:

        st.caption("No scenarios identified.")
        return

    for index, item in enumerate(
        scenarios,
        start=1
    ):

        if isinstance(item, dict):

            scenario = safe_text(
                item.get("scenario")
            )

            priority = safe_text(
                item.get("priority"),
                "Not specified"
            )

            rationale = safe_text(
                item.get("rationale"),
                ""
            )

            st.markdown(
                f"**{index}. {scenario}**"
            )

            st.caption(
                f"Priority: {priority}"
            )

            if rationale:
                st.write(rationale)

        else:

            st.write(f"{index}. {item}")


def render_scenarios(scenarios):

    scenarios = safe_dict(scenarios)

    scenario_tabs = st.tabs([
        "Positive",
        "Negative",
        "Boundary",
        "Edge Cases"
    ])

    categories = [
        ("positive", "Positive Scenarios"),
        ("negative", "Negative Scenarios"),
        ("boundary", "Boundary Scenarios"),
        ("edge_cases", "Edge Cases")
    ]

    for tab, (key, title) in zip(
        scenario_tabs,
        categories
    ):

        with tab:

            render_scenario_section(
                title,
                scenarios.get(key, [])
            )


# ==================================================
# EXTERNAL DEPENDENCIES
# ==================================================

def render_dependencies(dependencies):

    dependencies = safe_list(dependencies)

    st.subheader("🔗 External Dependencies")

    if not dependencies:

        st.info(
            "No external dependencies were identified."
        )
        return

    for dependency in dependencies:

        if not isinstance(dependency, dict):

            st.write(f"- {dependency}")
            continue

        with st.expander(
            safe_text(
                dependency.get("system"),
                "External system"
            )
        ):

            st.write(
                "**Purpose:**",
                safe_text(
                    dependency.get("purpose")
                )
            )

            st.write(
                "**Interface:**",
                safe_text(
                    dependency.get("interface")
                )
            )

            st.write(
                "**QA Considerations:**",
                safe_text(
                    dependency.get("qa_considerations")
                )
            )

            st.write(
                "**Confirmation Needed:**",
                safe_text(
                    dependency.get("confirmation_needed")
                )
            )


# ==================================================
# CONSOLIDATED CLARIFICATION RESPONSE FORM
# ==================================================

def render_clarification_form(
    questions,
    result,
    user_story,
    history,
    round_number
):

    if not questions:
        return

    st.markdown("### 📝 Consolidated BA / PO Response")

    st.write(
        """
        Answer all the questions together below.
        Include the question IDs wherever possible.
        You do not need to answer questions that have
        already been resolved in previous rounds.
        """
    )

    with st.form(
        key=f"clarification_form_{round_number}"
    ):

        ba_response = st.text_area(
            "Enter all BA / PO answers together",
            height=220,
            placeholder=(
                "Q-001: ...\n"
                "Q-002: ...\n"
                "Q-003: ..."
            ),
            key=f"ba_response_{round_number}"
        )

        submitted = st.form_submit_button(
            "Evaluate All Clarifications"
        )

    if submitted:

        if not ba_response.strip():

            st.warning(
                "Please enter the BA / PO response."
            )

        else:

            try:

                with st.spinner(
                    "AI is evaluating all clarification responses..."
                ):

                    review = analyze_clarification(
                        user_story=user_story,
                        initial_analysis=result,
                        ba_response=ba_response,
                        previous_reviews=history
                    )

                if not isinstance(review, dict) or not review:

                    raise ValueError(
                        "AI returned an empty clarification assessment."
                    )

                updated_history = list(history)

                updated_history.append({
                    "ba_response": ba_response,
                    "ai_assessment": review
                })

                st.session_state[
                    "clarification_history"
                ] = updated_history

                st.rerun()

            except Exception as e:

                st.error(
                    f"Clarification evaluation failed: {e}"
                )


# ==================================================
# CLARIFICATION HISTORY
# ==================================================

def render_clarification_history(history):

    if not history:
        return

    st.divider()

    st.subheader(
        "🤖 BA / PO Clarification Assessment"
    )

    for index, history_item in enumerate(
        history,
        start=1
    ):

        review = safe_dict(
            history_item.get("ai_assessment")
        )

        with st.expander(
            f"Clarification Round {index}",
            expanded=(index == len(history))
        ):

            st.markdown("**BA / PO Response:**")

            st.write(
                safe_text(
                    history_item.get("ba_response")
                )
            )

            st.markdown("**AI Assessment:**")

            st.write(
                safe_text(
                    review.get("assessment_summary")
                )
            )

            st.markdown("**Updated Readiness:**")

            st.write(
                safe_text(
                    review.get("readiness")
                )
            )

            confirmed_rules = safe_list(
                review.get("confirmed_business_rules")
            )

            st.markdown("**Confirmed Business Rules:**")

            if confirmed_rules:

                for rule in confirmed_rules:
                    st.write(f"- {rule}")

            else:

                st.caption(
                    "No new confirmed rules returned."
                )

            resolved_items = safe_list(
                review.get("resolved_items")
            )

            st.markdown("**Resolved Questions:**")

            if resolved_items:

                for item in resolved_items:

                    if isinstance(item, dict):

                        st.write(
                            f"- {item.get('question_id', '')}: "
                            f"{item.get('confirmed_business_rule', '')}"
                        )

                    else:

                        st.write(f"- {item}")

            else:

                st.caption(
                    "No resolved items returned."
                )

            remaining_gaps = safe_list(
                review.get("remaining_gaps")
            )

            st.markdown("**Outstanding Requirement Findings:**")

            if remaining_gaps:

                for gap in remaining_gaps:

                    if isinstance(gap, dict):

                        st.write(
                            f"- **{gap.get('title', 'Gap')}**: "
                            f"{gap.get('observation', '')} "
                            f"(Priority: {gap.get('priority', 'Not specified')})"
                        )

                    else:

                        st.write(f"- {gap}")

            else:

                st.success(
                    "No remaining gaps identified."
                )

            updated_scenarios = safe_dict(
                review.get("updated_test_scenarios")
            )

            if updated_scenarios:

                st.markdown("**Updated QA Coverage:**")

                render_scenarios(
                    updated_scenarios
                )

            outstanding_risks = safe_list(
                review.get("outstanding_risks")
            )

            if outstanding_risks:

                st.markdown("**Outstanding Risks:**")

                for risk in outstanding_risks:
                    st.write(f"- {risk}")

            st.info(
                "Recommendation: "
                + safe_text(
                    review.get("recommendation")
                )
            )


# ==================================================
# TEST CASE GENERATOR DISPLAY
# ==================================================

def render_test_cases(test_result):

    test_cases = [
        tc for tc in safe_list(
            test_result.get("test_cases")
        )
        if isinstance(tc, dict)
    ]

    st.subheader(
        f"📋 Generated Test Cases ({len(test_cases)})"
    )

    if not test_cases:

        st.warning(
            "No test cases were returned. Please try again."
        )
        return

    for index, test_case in enumerate(
        test_cases,
        start=1
    ):

        test_id = safe_text(
            test_case.get("id"),
            f"TC-{index:03d}"
        )

        with st.expander(
            f"{test_id} | "
            f"{safe_text(test_case.get('category'), 'General')} | "
            f"{safe_text(test_case.get('scenario'))}"
        ):

            st.write(
                "**Coverage Area:**",
                safe_text(
                    test_case.get("coverage_area")
                )
            )

            st.write(
                "**Preconditions:**",
                safe_text(
                    test_case.get("preconditions")
                )
            )

            st.write(
                "**Test Data:**",
                safe_text(
                    test_case.get("test_data")
                )
            )

            st.markdown("**Test Steps:**")

            steps = test_case.get(
                "steps",
                []
            )

            if isinstance(steps, list):

                for step_index, step in enumerate(
                    steps,
                    start=1
                ):

                    st.write(
                        f"{step_index}. {step}"
                    )

            else:

                st.write(
                    safe_text(steps)
                )

            st.write(
                "**Expected Result:**",
                safe_text(
                    test_case.get("expected_result")
                )
            )

            st.write(
                "**Priority:**",
                safe_text(
                    test_case.get("priority")
                )
            )

    export_data = []

    for tc in test_cases:

        steps = tc.get("steps", [])

        if isinstance(steps, list):

            steps = "\n".join(
                f"{i}. {step}"
                for i, step in enumerate(
                    steps,
                    start=1
                )
            )

        export_data.append({
            "Test Case ID": tc.get("id", ""),
            "Category": tc.get("category", ""),
            "Coverage Area": tc.get("coverage_area", ""),
            "Scenario": tc.get("scenario", ""),
            "Preconditions": tc.get("preconditions", ""),
            "Test Data": tc.get("test_data", ""),
            "Test Steps": steps,
            "Expected Result": tc.get("expected_result", ""),
            "Priority": tc.get("priority", "")
        })

    csv = pd.DataFrame(
        export_data
    ).to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download Test Cases as CSV",
        data=csv,
        file_name="AI_Generated_Test_Cases.csv",
        mime="text/csv",
        key="download_test_cases"
    )


# ==================================================
# APPLICATION HEADER
# ==================================================

st.title("🧪 QA AI Agent")

st.subheader("Intelligent Test Assistant")

st.write(
    """
    Analyse user stories, identify requirement gaps,
    assess business risks, derive comprehensive QA coverage
    and generate detailed test cases using AI.
    """
)

st.divider()


# ==================================================
# USER STORY INPUT
# ==================================================

st.subheader("📝 Enter Requirement / User Story")

user_story = st.text_area(
    "Paste your user story or requirement",
    height=180,
    placeholder=(
        "As a customer, I want to place an online order "
        "using my credit card or gift card so that I can "
        "complete my purchase."
    ),
    key="user_story"
)


# ==================================================
# APPLICATION TABS
# ==================================================

tab1, tab2 = st.tabs([
    "🔍 Comprehensive QA Analysis",
    "🧪 Test Case Generator"
])


# ==================================================
# TAB 1: COMPREHENSIVE QA ANALYSIS
# ==================================================

with tab1:

    st.subheader(
        "AI-Powered Requirement & QA Analysis"
    )

    st.write(
        """
        One-click analysis of requirement gaps, business risks,
        dependencies and positive, negative, boundary and
        edge-case scenarios.
        """
    )

    if st.button(
        "🚀 Analyse Complete Requirement",
        key="analyse"
    ):

        if not user_story.strip():

            st.warning(
                "Please enter a user story first."
            )

        else:

            try:

                with st.spinner(
                    "AI is performing comprehensive QA analysis..."
                ):

                    result = analyze_requirement(
                        user_story
                    )

                if not isinstance(result, dict) or not result:

                    raise ValueError(
                        "Empty or invalid AI analysis."
                    )

                st.session_state[
                    "requirement_result"
                ] = result

                st.session_state[
                    "analysis_story"
                ] = user_story

                st.session_state[
                    "clarification_history"
                ] = []

            except Exception as e:

                st.error(
                    f"Requirement analysis failed: {e}"
                )

    result = safe_dict(
        st.session_state.get(
            "requirement_result"
        )
    )

    if (
        result
        and st.session_state.get("analysis_story") == user_story
    ):

        st.divider()

        # ------------------------------------------
        # REQUIREMENT SUMMARY
        # ------------------------------------------

        st.subheader("📋 Requirement Summary")

        st.write(
            safe_text(
                result.get("requirement_summary")
            )
        )

        st.write(
            "**Initial QA Readiness:**",
            safe_text(
                result.get("readiness")
            )
        )

        # ------------------------------------------
        # CONSOLIDATED FINDINGS
        # ------------------------------------------

        render_consolidated_findings(
            result
        )

        # ------------------------------------------
        # EXTERNAL DEPENDENCIES
        # ------------------------------------------

        render_dependencies(
            result.get("external_dependencies")
        )

        # ------------------------------------------
        # AI-DERIVED QA COVERAGE
        # ------------------------------------------

        st.divider()

        st.subheader(
            "🧪 AI-Derived QA Test Coverage"
        )

        render_scenarios(
            result.get("test_scenarios")
        )

        # ------------------------------------------
        # RISKS AND ASSUMPTIONS
        # ------------------------------------------

        st.divider()

        st.subheader("⚠️ Overall Risks")

        for risk in safe_list(
            result.get("overall_risks")
        ):

            st.write(f"- {risk}")

        st.subheader("📝 AI Assumptions")

        assumptions = safe_list(
            result.get("assumptions")
        )

        if assumptions:

            for assumption in assumptions:
                st.write(f"- {assumption}")

        else:

            st.caption(
                "No assumptions identified."
            )

        # ------------------------------------------
        # CLARIFICATION WORKFLOW
        # ------------------------------------------

        initial_questions = safe_list(
            result.get("clarification_questions")
        )

        history = st.session_state.get(
            "clarification_history",
            []
        )

        st.divider()

        if not history:

            # First clarification round

            render_clarification_questions(
                initial_questions
            )

            if initial_questions:

                render_clarification_form(
                    questions=initial_questions,
                    result=result,
                    user_story=user_story,
                    history=[],
                    round_number=1
                )

            else:

                st.success(
                    "No BA / PO clarification is currently required."
                )

        else:

            # Display previous clarification assessments

            render_clarification_history(
                history
            )

            # Check only the latest AI assessment

            latest_review = safe_dict(
                history[-1].get("ai_assessment")
            )

            new_questions = safe_list(
                latest_review.get(
                    "new_clarification_questions"
                )
            )

            st.divider()

            if new_questions:

                st.warning(
                    "AI has identified additional unresolved "
                    "requirement questions."
                )

                render_clarification_questions(
                    new_questions
                )

                round_number = len(history) + 1

                render_clarification_form(
                    questions=new_questions,
                    result=result,
                    user_story=user_story,
                    history=history,
                    round_number=round_number
                )

            else:

                st.success(
                    "Clarification completed. No further "
                    "questions were returned by AI."
                )

        # ------------------------------------------
        # DOWNLOAD INITIAL QA ANALYSIS
        # ------------------------------------------

        report_rows = []

        for category, items, id_field in [
            (
                "Requirement Gap",
                result.get("requirement_gaps"),
                "gap_id"
            ),
            (
                "Ambiguity",
                result.get("ambiguities"),
                "ambiguity_id"
            ),
            (
                "Conflict",
                result.get("conflicting_requirements"),
                "conflict_id"
            )
        ]:

            for item in safe_list(items):

                if isinstance(item, dict):

                    report_rows.append({
                        "Category": category,
                        "ID": item.get(id_field, ""),
                        "Title": item.get("title", ""),
                        "Observation": item.get("observation", ""),
                        "Business Impact": item.get("business_impact", ""),
                        "QA Impact": item.get("qa_impact", ""),
                        "Priority": item.get("priority", "")
                    })

        if report_rows:

            report_csv = pd.DataFrame(
                report_rows
            ).to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Download QA Requirement Analysis",
                data=report_csv,
                file_name="QA_Requirement_Analysis.csv",
                mime="text/csv",
                key="download_requirement_report"
            )

        st.info(
            """
            AI-generated findings are recommendations.
            Validate business rules and assumptions with the
            Product Owner or Business Analyst before sign-off.
            """
        )


# ==================================================
# TAB 2: TEST CASE GENERATOR
# ==================================================

with tab2:

    st.subheader(
        "AI Test Case Generator"
    )

    st.write(
        """
        Generate detailed positive, negative, boundary and edge
        test cases from the user story.
        """
    )

    if st.button(
        "🧪 Generate Test Cases",
        key="generate"
    ):

        if not user_story.strip():

            st.warning(
                "Please enter a user story first."
            )

        else:

            try:

                with st.spinner(
                    "AI is generating detailed test cases..."
                ):

                    test_result = generate_test_cases(
                        user_story
                    )

                if not isinstance(test_result, dict) or not test_result:

                    raise ValueError(
                        "AI returned an empty or invalid test case response."
                    )

                st.session_state[
                    "test_case_result"
                ] = test_result

                st.session_state[
                    "test_case_story"
                ] = user_story

            except Exception as e:

                st.session_state.pop(
                    "test_case_result",
                    None
                )

                st.error(
                    f"Test case generation failed: {e}"
                )

    test_result = safe_dict(
        st.session_state.get(
            "test_case_result"
        )
    )

    if (
        test_result
        and st.session_state.get("test_case_story") == user_story
    ):

        st.divider()

        render_test_cases(
            test_result
        )

        assumptions = safe_list(
            test_result.get("assumptions")
        )

        if assumptions:

            st.subheader("📝 AI Assumptions")

            for assumption in assumptions:
                st.write(f"- {assumption}")

        gaps = safe_list(
            test_result.get("gaps")
        )

        if gaps:

            st.subheader("⚠️ Requirement Gaps")

            for gap in gaps:
                st.write(f"- {gap}")

        st.info(
            """
            Review generated test cases against approved business
            rules before using them in execution.
            """
        )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "QA AI Agent | Comprehensive Requirement Analysis "
    "& Intelligent Test Case Generation | Powered by Ollama"
)
