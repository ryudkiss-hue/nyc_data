"""Analytical Skills workflows — structured, reusable analysis frameworks.

Integrates 31 portable analytical skills from the data-analytics-skills library:
- Business Metrics Calculator (SaaS/ecommerce KPIs)
- A/B Test Analysis (experiment design, significance testing)
- Analysis QA Checklist (pre-delivery quality gates)
- Cohort Analysis (retention, behavior tracking)
- Root-Cause Investigation (metric change diagnosis)
- And 26 more specialized analytical workflows

Claude AI integration provides dynamic, conversational guidance through each skill.
"""

from __future__ import annotations

import os

try:
    import anthropic  # noqa: F401
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

import streamlit as st


def render_analytical_skills_page() -> None:
    """Render the Analytical Skills page with structured workflow guides."""
    st.subheader("📊 Analytical Skills Library")
    st.caption(
        "31 portable, structured analytical workflows for quality, rigor, and consistency."
    )

    # Skills organized by category
    st.markdown("### 🔍 Data Quality & Validation")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Data Quality Audit", use_container_width=True):
            st.session_state["skill_focus"] = "data_quality_audit"
            st.rerun()
    with col2:
        if st.button("Query Validation", use_container_width=True):
            st.session_state["skill_focus"] = "query_validation"
            st.rerun()

    st.markdown("### 📊 Business Metrics & KPIs")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Business Metrics Calculator", use_container_width=True):
            st.session_state["skill_focus"] = "business_metrics"
            st.rerun()
    with col2:
        if st.button("Metric Reconciliation", use_container_width=True):
            st.session_state["skill_focus"] = "metric_reconciliation"
            st.rerun()
    with col3:
        if st.button("Impact Quantification", use_container_width=True):
            st.session_state["skill_focus"] = "impact_quantification"
            st.rerun()

    st.markdown("### 📈 Data Analysis & Investigation")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("A/B Test Analysis", use_container_width=True):
            st.session_state["skill_focus"] = "ab_test_analysis"
            st.rerun()
    with col2:
        if st.button("Root-Cause Investigation", use_container_width=True):
            st.session_state["skill_focus"] = "root_cause_investigation"
            st.rerun()
    with col3:
        if st.button("Cohort Analysis", use_container_width=True):
            st.session_state["skill_focus"] = "cohort_analysis"
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Funnel Analysis", use_container_width=True):
            st.session_state["skill_focus"] = "funnel_analysis"
            st.rerun()
    with col2:
        if st.button("Segmentation Analysis", use_container_width=True):
            st.session_state["skill_focus"] = "segmentation_analysis"
            st.rerun()
    with col3:
        if st.button("Time-Series Analysis", use_container_width=True):
            st.session_state["skill_focus"] = "time_series_analysis"
            st.rerun()

    st.markdown("### 🎨 Data Storytelling & Visualization")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Insight Synthesis", use_container_width=True):
            st.session_state["skill_focus"] = "insight_synthesis"
            st.rerun()
    with col2:
        if st.button("Visualization Builder", use_container_width=True):
            st.session_state["skill_focus"] = "visualization_builder"
            st.rerun()
    with col3:
        if st.button("Data Narrative Builder", use_container_width=True):
            st.session_state["skill_focus"] = "data_narrative"
            st.rerun()

    st.markdown("### ✅ Quality Assurance & Delivery")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Analysis QA Checklist", use_container_width=True):
            st.session_state["skill_focus"] = "analysis_qa_checklist"
            st.rerun()
    with col2:
        if st.button("Executive Summary Generator", use_container_width=True):
            st.session_state["skill_focus"] = "executive_summary"
            st.rerun()

    st.divider()

    # Display skill details if selected
    skill = st.session_state.get("skill_focus")
    if skill:
        _render_skill_workflow(skill)


def _render_skill_workflow(skill: str) -> None:
    """Render workflow guide for selected skill."""
    skill_details = {
        "business_metrics": {
            "title": "Business Metrics Calculator",
            "description": "Calculate SaaS metrics (MRR, churn, LTV, CAC), ecommerce KPIs with industry benchmarks.",
            "steps": [
                "1. Define metric type (MRR, ARR, churn, LTV, CAC, CAC payback)",
                "2. Provide dataset or manual inputs",
                "3. Calculate with industry benchmarks",
                "4. Compare against targets",
                "5. Export insights and recommendations",
            ],
            "example": "Calculate LTV:CAC ratio for inspection services — SaaS-style metric.",
        },
        "ab_test_analysis": {
            "title": "A/B Test Analysis",
            "description": "Rigorous A/B test statistical analysis with significance testing and sample size validation.",
            "steps": [
                "1. Define control and treatment groups",
                "2. Specify hypothesis and success metric",
                "3. Run significance test (t-test, Chi-square)",
                "4. Check sample ratio mismatch (SRM)",
                "5. Report confidence intervals and effect size",
            ],
            "example": "Test if new inspection workflow increases completion rate — statistical rigor.",
        },
        "analysis_qa_checklist": {
            "title": "Analysis QA Checklist",
            "description": "Pre-delivery quality assurance for analysis work — completeness, clarity, assumptions.",
            "steps": [
                "1. Review question clarity and scope",
                "2. Validate data sources and freshness",
                "3. Check assumptions and dependencies",
                "4. Verify calculations and logic",
                "5. Ensure findings are actionable",
                "6. Confirm stakeholder alignment",
            ],
            "example": "Gate all quality analyses before sharing with leadership.",
        },
        "cohort_analysis": {
            "title": "Cohort Analysis",
            "description": "Time-based cohort analysis with retention tracking and behavior curves.",
            "steps": [
                "1. Define cohort boundaries (weekly, monthly, by event)",
                "2. Compute retention rates over time",
                "3. Track KPI trends per cohort",
                "4. Compare cohort behavior",
                "5. Identify churn patterns",
            ],
            "example": "Track inspection team cohorts — retention by hire date.",
        },
        "root_cause_investigation": {
            "title": "Root-Cause Investigation",
            "description": "Structured diagnosis of metric changes with hypothesis testing.",
            "steps": [
                "1. Detect metric change (spike/drop)",
                "2. Isolate time window",
                "3. Generate hypotheses",
                "4. Test each hypothesis with data",
                "5. Narrow to most likely causes",
                "6. Recommend actions",
            ],
            "example": "Inspection volume dropped 15% — diagnose if staffing, seasonality, or policy.",
        },
        "insight_synthesis": {
            "title": "Insight Synthesis",
            "description": "Extract key findings as actionable business insights from analysis.",
            "steps": [
                "1. Identify findings from data",
                "2. Translate to business language",
                "3. Assess impact and urgency",
                "4. Recommend specific actions",
                "5. Frame for stakeholder audience",
            ],
            "example": "Turn quality score trends into operational priorities.",
        },
        "visualization_builder": {
            "title": "Visualization Builder",
            "description": "Chart type selection and design guidance for effective data storytelling.",
            "steps": [
                "1. Identify data structure (time series, distribution, comparison)",
                "2. Choose chart type (line, bar, scatter, heatmap)",
                "3. Apply design principles (color, labels, legend)",
                "4. Test clarity with audience",
                "5. Iterate on feedback",
            ],
            "example": "Visualize SLA compliance trends — line chart with color-coded breaches.",
        },
        "executive_summary": {
            "title": "Executive Summary Generator",
            "description": "Concise executive-ready summaries from detailed analysis.",
            "steps": [
                "1. Identify 3-5 key findings",
                "2. Quantify impact",
                "3. Recommend actions",
                "4. Limit to 1 page",
                "5. Use executive language",
            ],
            "example": "One-page brief for leadership on quality trends and SLA status.",
        },
    }

    details = skill_details.get(skill, {})
    if not details:
        st.warning("Skill workflow not yet configured.")
        return

    st.markdown(f"### {details['title']}")
    st.write(details["description"])

    st.markdown("#### Workflow Steps")
    for step in details["steps"]:
        st.write(f"• {step}")

    st.markdown("#### Example Application")
    st.info(f"📌 {details['example']}")

    st.markdown("---")

    # Claude AI-powered skill guidance
    if HAS_ANTHROPIC and os.getenv("ANTHROPIC_API_KEY"):
        st.markdown("### 💬 Interactive Guidance")
        _render_skill_mentor_chat(skill, details)
    else:
        st.info(
            "💡 **Claude AI guidance unavailable.** Set `ANTHROPIC_API_KEY` environment variable "
            "to enable conversational skill mentoring."
        )

    st.markdown("---")
    if st.button("✓ Complete this skill workflow"):
        st.success("Workflow marked complete. Results ready for next stage.")
        del st.session_state["skill_focus"]
        st.rerun()


def _get_skill_system_prompt(skill: str, skill_details: dict) -> str:
    """Generate a Claude system prompt for the given skill."""
    title = skill_details.get("title", skill)
    description = skill_details.get("description", "")
    steps = "\n".join(
        f"  {step}" for step in skill_details.get("steps", [])
    )
    example = skill_details.get("example", "")

    return f"""You are an expert analytical mentor specializing in the {title} skill.

**Skill Description:** {description}

**Workflow Steps:**
{steps}

**Example Application:** {example}

Your role:
1. Guide the user through this analytical workflow step-by-step
2. Ask clarifying questions about their specific data, problem, and objective
3. Provide concrete, actionable advice tailored to their situation
4. Help them understand when and how to apply this skill
5. Suggest tools, patterns, or frameworks relevant to their use case
6. Identify potential pitfalls and how to avoid them

Be conversational, encouraging, and focused on practical outcomes. If the user describes a problem
outside this skill's scope, gently redirect them to a more relevant analytical skill."""


def _render_skill_mentor_chat(skill: str, skill_details: dict) -> None:
    """Render Claude AI mentor chat interface for interactive skill guidance."""
    chat_key = f"skill_chat_{skill}"

    # Initialize chat history in session state
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state[chat_key]:
            role = message["role"]
            content = message["content"]
            with st.chat_message(role):
                st.markdown(content)

    # Chat input
    user_input = st.chat_input(
        "Ask about this skill or describe your analysis problem..."
    )

    if user_input:
        # Add user message to history
        st.session_state[chat_key].append({"role": "user", "content": user_input})

        # Display user message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

        # Get Claude response
        try:
            import anthropic as _anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            if not api_key:
                st.error("ANTHROPIC_API_KEY not set.")
                return

            client = _anthropic.Anthropic(api_key=api_key)

            system_prompt = _get_skill_system_prompt(skill, skill_details)

            # Build messages list from chat history
            messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state[chat_key]
            ]

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )

            assistant_response = response.content[0].text

            # Add assistant response to history
            st.session_state[chat_key].append(
                {"role": "assistant", "content": assistant_response}
            )

            # Display assistant response
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)

            st.rerun()

        except Exception as e:
            st.error(f"Error getting Claude response: {str(e)}")
            # Remove the user message if Claude failed
            st.session_state[chat_key].pop()
