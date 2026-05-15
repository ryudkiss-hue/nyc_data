#!/usr/bin/env python3
"""
Example demonstrating LangChain chatbot integration.

Run with:
    python examples/chatbot_example.py
"""

from socrata_toolkit.llm_chatbot import (
    AnalyticsAdvisor,
    DataQualityAssistant,
    DatasetContext,
    SocrataLLMChatbot,
)


def example_basic_chatbot():
    """Basic chatbot usage with Ollama."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Chatbot with Dataset Context")
    print("=" * 60)

    # Initialize chatbot
    chatbot = SocrataLLMChatbot(
        llm_provider="ollama",
        model_name="mistral",
        conversation_history_size=20,
    )

    # Create dataset context
    context = DatasetContext(
        fourfour="2bnn-jtbk",
        title="NYC Sidewalk Inspection Records",
        description="Historical inspection data for NYC sidewalks including location, condition, and defect types",
        columns=[
            {"name": "inspection_id", "type": "integer"},
            {"name": "location", "type": "string"},
            {"name": "latitude", "type": "float"},
            {"name": "longitude", "type": "float"},
            {"name": "inspection_date", "type": "date"},
            {"name": "condition", "type": "string"},
            {"name": "defect_type", "type": "string"},
            {"name": "severity", "type": "string"},
            {"name": "borough", "type": "string"},
            {"name": "estimated_repair_cost", "type": "decimal"},
        ],
        sample_values={
            "condition": ["good", "fair", "poor"],
            "defect_type": ["crack", "pothole", "raised_edge", "settlement"],
            "severity": ["minor", "moderate", "critical"],
            "borough": ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"],
        },
        row_count=150000,
        quality_score=0.92,
    )

    chatbot.set_dataset_context(context)

    # Simulate conversation
    questions = [
        "What are the most common sidewalk defects in NYC?",
        "How many critical issues were found last year?",
        "Which borough has the most repair needs?",
    ]

    for question in questions:
        print(f"\nUser: {question}")
        print("-" * 40)
        try:
            response = chatbot.chat(question)
            print(f"Assistant: {response}\n")
        except Exception as e:
            print(f"[Note: This example requires Ollama running locally]")
            print(f"Error: {e}\n")

    # Show conversation history
    print("\n" + "=" * 60)
    print("Conversation History:")
    print("=" * 60)
    for msg in chatbot.get_conversation_history()[:3]:
        print(f"[{msg['role'].upper()}] {msg['content'][:100]}...")


def example_suggested_analyses():
    """Get analysis suggestions."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Suggested Analyses")
    print("=" * 60)

    chatbot = SocrataLLMChatbot(
        llm_provider="ollama",
        model_name="mistral",
    )

    context = DatasetContext(
        fourfour="2bnn-jtbk",
        title="NYC Sidewalk Inspection Records",
        description="Historical inspection data for NYC sidewalks",
        columns=[
            {"name": "inspection_id", "type": "integer"},
            {"name": "inspection_date", "type": "date"},
            {"name": "condition", "type": "string"},
            {"name": "repair_cost", "type": "decimal"},
        ],
        row_count=150000,
    )

    chatbot.set_dataset_context(context)

    print("\nSuggested analyses for this dataset:")
    print("-" * 40)

    try:
        suggestions = chatbot.suggest_analyses(max_suggestions=5)
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
    except Exception as e:
        print(f"[Note: Requires running Ollama: ollama serve]")
        print(f"Example suggestions would include:")
        print("1. Analyze seasonal trends in sidewalk degradation")
        print("2. Identify high-risk areas with frequent critical issues")
        print("3. Calculate average repair time by borough")
        print("4. Forecast maintenance budget based on historical patterns")
        print("5. Compare condition improvements post-repair")


def example_column_explanation():
    """Explain a specific column."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Column Explanations")
    print("=" * 60)

    chatbot = SocrataLLMChatbot(
        llm_provider="ollama",
        model_name="mistral",
    )

    context = DatasetContext(
        fourfour="2bnn-jtbk",
        title="NYC Sidewalk Inspection Records",
        description="Historical inspection data for NYC sidewalks",
        columns=[
            {
                "name": "severity",
                "type": "string",
                "description": "Severity level of identified defects",
            },
            {
                "name": "condition",
                "type": "string",
                "description": "Overall sidewalk condition rating",
            },
        ],
    )

    chatbot.set_dataset_context(context)

    columns_to_explain = ["severity", "condition"]

    print("\nColumn Explanations:")
    print("-" * 40)

    for column_name in columns_to_explain:
        try:
            explanation = chatbot.explain_column(column_name)
            print(f"\n{column_name}:")
            print(f"  {explanation}")
        except Exception as e:
            print(f"\n{column_name}:")
            print(f"  [Explanation would be generated here]")


def example_query_validation():
    """Validate if a query is feasible."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Query Validation")
    print("=" * 60)

    chatbot = SocrataLLMChatbot(
        llm_provider="ollama",
        model_name="mistral",
    )

    context = DatasetContext(
        fourfour="2bnn-jtbk",
        title="NYC Sidewalk Inspection Records",
        description="Sidewalk inspection data with location and condition info",
        columns=[
            {"name": "inspection_id", "type": "integer"},
            {"name": "location", "type": "string"},
            {"name": "condition", "type": "string"},
            {"name": "repair_cost", "type": "decimal"},
            {"name": "inspection_date", "type": "date"},
        ],
    )

    chatbot.set_dataset_context(context)

    queries = [
        "Show me the most expensive repairs in Manhattan",
        "Calculate the average inspection time per location",
        "Predict future maintenance costs using machine learning",
    ]

    print("\nQuery Feasibility Assessment:")
    print("-" * 40)

    for query in queries:
        print(f"\nQuery: {query}")
        try:
            result = chatbot.validate_query(query)
            print(f"  Feasible: {result.get('feasible', False)}")
            print(f"  Reason: {result.get('reason', 'Unknown')}")
        except Exception as e:
            print(f"  [Assessment would be performed here]")


def example_data_quality_assistant():
    """Demonstrate data quality advisor."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Data Quality Assistant")
    print("=" * 60)

    quality_assistant = DataQualityAssistant(
        llm_provider="ollama",
        model_name="mistral",
    )

    context = DatasetContext(
        fourfour="2bnn-jtbk",
        title="NYC Sidewalk Inspection Records",
        description="Sidewalk inspection data",
        columns=[
            {"name": "condition", "type": "string"},
            {"name": "location", "type": "string"},
            {"name": "repair_cost", "type": "decimal"},
        ],
    )

    quality_assistant.set_dataset_context(context)

    issue = """
    We're observing:
    - 18% null values in the 'condition' column
    - Inconsistent location formatting (some addresses, some coordinates)
    - Repair costs sometimes exceed budget estimates by 50%
    """

    print("\nQuality Issue Assessment:")
    print("-" * 40)
    print(f"Issue Description:\n{issue}\n")

    try:
        assessment = quality_assistant.assess_quality_issue(issue)
        print(f"Severity: {assessment.get('severity', 'unknown')}")
        print(f"Likely Causes: {', '.join(assessment.get('likely_causes', []))}")
        print(f"Impact: {assessment.get('impact', 'unknown')}")
        print(f"Recommendations: {', '.join(assessment.get('remediation', []))}")
    except Exception as e:
        print("[Assessment would be performed with Ollama running]")
        print(f"Expected output: severity, causes, impact, remediation steps")

    print("\n" + "-" * 40)
    print("Recommended Validations for 'condition' column:")
    try:
        validations = quality_assistant.recommend_validations("condition")
        for v in validations:
            print(f"  - {v}")
    except Exception as e:
        print("  - Check for required values (no nulls)")
        print("  - Validate against allowed values")
        print("  - Check data type consistency")


def example_analytics_advisor():
    """Demonstrate analytics advisor."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Analytics Advisor")
    print("=" * 60)

    advisor = AnalyticsAdvisor(
        llm_provider="ollama",
        model_name="mistral",
    )

    context = DatasetContext(
        fourfour="2bnn-jtbk",
        title="NYC Sidewalk Inspection Records",
        description="Comprehensive sidewalk inspection and maintenance data",
        columns=[
            {"name": "inspection_id", "type": "integer"},
            {"name": "inspection_date", "type": "date"},
            {"name": "condition", "type": "string"},
            {"name": "defect_type", "type": "string"},
            {"name": "repair_cost", "type": "decimal"},
            {"name": "completion_date", "type": "date"},
            {"name": "borough", "type": "string"},
        ],
    )

    advisor.set_dataset_context(context)

    print("\nSuggested KPIs and Metrics:")
    print("-" * 40)

    try:
        metrics = advisor.suggest_metrics()
        for metric in metrics[:5]:
            print(f"\n{metric.get('name', 'Unknown')}:")
            print(f"  Description: {metric.get('description', '')}")
            print(f"  Importance: {metric.get('importance', 'medium')}")
    except Exception as e:
        print("Example metrics:")
        print("\nAverage Repair Time:")
        print("  Description: Days between inspection and repair completion")
        print("  Importance: high")
        print("\nDefect Recurrence Rate:")
        print("  Description: Percentage of same-location issues in 12 months")
        print("  Importance: high")

    print("\n" + "-" * 40)
    print("Pattern Identification:")

    findings = """
    - 42% of critical issues found in winter months (Nov-Mar)
    - Manhattan averages 3.2x more complaints than Staten Island
    - Pothole repairs have 28% recurrence rate within 6 months
    - Average repair time increased 35% year-over-year
    - Budget overruns highest in Q4 (average +18%)
    """

    print(f"Findings:\n{findings}")

    try:
        patterns = advisor.identify_patterns(findings)
        print("\nIdentified Patterns:")
        for pattern in patterns:
            print(f"  - {pattern}")
    except Exception as e:
        print("\nIdentified Patterns:")
        print("  - Seasonal variation in sidewalk condition (weather impact)")
        print("  - Geographic disparities in maintenance funding")
        print("  - Systemic issues with pothole repair quality")
        print("  - Capacity constraints affecting repair timelines")


if __name__ == "__main__":
    print("\n")
    print("🤖 NYC Sidewalk Data Toolkit - LangChain Chatbot Examples")
    print("=" * 60)
    print("\nThese examples demonstrate:")
    print("1. Basic chatbot with conversational context")
    print("2. Suggested analyses for datasets")
    print("3. Column explanations for data dictionary")
    print("4. Query feasibility validation")
    print("5. Data quality issue assessment")
    print("6. Analytics advisor with pattern identification")
    print("\n" + "=" * 60)

    # Run examples
    example_basic_chatbot()
    example_suggested_analyses()
    example_column_explanation()
    example_query_validation()
    example_data_quality_assistant()
    example_analytics_advisor()

    print("\n" + "=" * 60)
    print("✅ Examples Complete!")
    print("=" * 60)
    print("\nTo use these features in your project:")
    print("1. Install dependencies: pip install langchain langchain-community ollama")
    print("2. Install Ollama: https://ollama.ai")
    print("3. Run Ollama server: ollama serve")
    print("4. Download a model: ollama pull mistral")
    print("5. Import and use the classes in your code")
    print("\nFor more details, see: docs/LANGCHAIN_INTEGRATION_GUIDE.md")
    print()
