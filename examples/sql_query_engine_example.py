#!/usr/bin/env python3
"""
Example demonstrating Wolfram-like SQL Query Engine using LangChain.

This example shows natural language to SQL translation with:
- Automatic schema understanding
- Query validation and optimization
- Live database execution
- Result interpretation

Run with:
    export DATABASE_URL="postgresql://user:password@localhost/nyc_data"
    python examples/sql_query_engine_example.py
"""

import os

from langchain_community.llms import Ollama

from socrata_toolkit.llm_sql_engine import (
    InteractiveQuerySession,
    QueryOptimizer,
    SQLQueryEngine,
)


def example_basic_query():
    """Basic natural language to SQL query."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Natural Language Query")
    print("=" * 70)

    # Initialize LLM
    llm = Ollama(model="mistral")

    # Get database connection
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    # Initialize query engine
    engine = SQLQueryEngine(
        dsn=dsn,
        llm=llm,
        max_results=100,
        enable_explain=True,
    )

    # Natural language question
    question = "How many sidewalk inspections were completed in the last 30 days?"

    print(f"\nUser Question: {question}\n")
    print("-" * 70)

    try:
        # Execute query
        execution = engine.execute(question)

        print(f"Generated SQL:\n{execution.sql_query}\n")
        print(f"Execution Time: {execution.execution_time_ms:.2f} ms")
        print(f"Results: {execution.row_count} rows\n")

        if execution.results:
            print("Sample Results (first 3):")
            for i, result in enumerate(execution.results[:3], 1):
                print(f"  {i}. {result}")

        if execution.interpretation:
            print(f"\nInterpretation: {execution.interpretation}")

        if execution.error:
            print(f"Error: {execution.error}")

    except Exception as e:
        print(f"[Example: Would execute with real database connection]")
        print(f"Error: {e}")


def example_follow_up_questions():
    """Interactive session with follow-up questions."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Interactive Session with Follow-up Questions")
    print("=" * 70)

    llm = Ollama(model="mistral")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    engine = SQLQueryEngine(dsn=dsn, llm=llm)
    session = InteractiveQuerySession(engine)

    questions = [
        "What are the top 5 neighborhoods with the most potholes?",
        "How many of those are in Manhattan?",
        "What's the average repair cost for those potholes?",
    ]

    print("\nSimulating conversation with context awareness:\n")
    print("-" * 70)

    try:
        for i, question in enumerate(questions, 1):
            print(f"\nQuestion {i}: {question}")

            result = session.ask(question)

            print(f"SQL: {result['sql']}")
            print(f"Results: {len(result['results'])} rows")

            if result["interpretation"]:
                print(f"Interpretation: {result['interpretation']}")

        # Show conversation
        print("\n" + "-" * 70)
        print("Full Conversation History:")
        for item in session.get_conversation():
            print(f"  Q: {item['question']}")
            print(
                f"  A: {item['interpretation'][:100]}..."
                if item["interpretation"]
                else "  A: [No interpretation]"
            )

    except Exception as e:
        print(f"[Example: Demonstrates multi-turn conversation with context]")
        print(f"Error: {e}")


def example_schema_exploration():
    """Explore database schema."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Schema Exploration")
    print("=" * 70)

    llm = Ollama(model="mistral")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    engine = SQLQueryEngine(dsn=dsn, llm=llm)

    print("\nAvailable Schema:")
    print("-" * 70)

    if engine.schema:
        for table_name, table_info in list(engine.schema.items())[:5]:
            print(f"\nTable: {table_name}")
            if "columns" in table_info:
                for col in table_info["columns"][:5]:
                    print(f"  - {col['name']} ({col['type']})")
    else:
        print("Schema not loaded. Example schema:")
        print("\nTable: sidewalk_inspections")
        print("  - inspection_id (bigint)")
        print("  - location (text)")
        print("  - borough (text)")
        print("  - inspection_date (date)")
        print("  - condition (text)")
        print("  - defect_type (text)")
        print("  - repair_cost (numeric)")
        print("\nTable: maintenance_records")
        print("  - record_id (bigint)")
        print("  - inspection_id (bigint)")
        print("  - start_date (date)")
        print("  - completion_date (date)")
        print("  - crew_assigned (text)")

    # Explain a table
    print("\n" + "-" * 70)
    print("Table Explanation:")

    try:
        explanation = engine.explain_table("sidewalk_inspections")
        print(f"\nsidewalk_inspections:\n{explanation}")
    except Exception as e:
        print(f"\nsidewalk_inspections:")
        print("This table contains historical records of NYC sidewalk inspections,")
        print("including location, condition assessment, identified defects, and")
        print("severity classification. Used for tracking maintenance needs and trends.")


def example_query_validation():
    """Validate queries for safety and correctness."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Query Validation")
    print("=" * 70)

    llm = Ollama(model="mistral")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    engine = SQLQueryEngine(dsn=dsn, llm=llm)

    test_queries = [
        ("SELECT * FROM sidewalk_inspections LIMIT 100", "✓ Safe - read only"),
        ("DELETE FROM sidewalk_inspections WHERE id=1", "✗ Dangerous - delete"),
        ("DROP TABLE sidewalk_inspections", "✗ Dangerous - drop table"),
    ]

    print("\nQuery Safety Validation:\n")
    print("-" * 70)

    for query, description in test_queries:
        is_valid, message = engine.validate_query(query)
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"\n{description}")
        print(f"Query: {query}")
        print(f"Status: {status} - {message}")


def example_query_optimization():
    """Get query optimization suggestions."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Query Optimization Suggestions")
    print("=" * 70)

    llm = Ollama(model="mistral")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    engine = SQLQueryEngine(dsn=dsn, llm=llm)
    optimizer = QueryOptimizer(engine, llm)

    sample_query = """
    SELECT 
        borough,
        COUNT(*) as inspection_count,
        AVG(CAST(repair_cost AS FLOAT)) as avg_cost
    FROM sidewalk_inspections
    WHERE inspection_date >= '2024-01-01'
    GROUP BY borough
    ORDER BY inspection_count DESC
    """

    print(f"\nOriginal Query:\n{sample_query}\n")
    print("-" * 70)

    try:
        # Get optimizations
        print("\nOptimization Suggestions:")
        optimizations = optimizer.suggest_optimizations(sample_query)

        for i, opt in enumerate(optimizations[:3], 1):
            print(f"\n{i}. {opt.get('optimization', 'Unknown optimization')}")
            print(f"   Benefit: {opt.get('benefit', 'Unknown benefit')}")

        # Get alternatives
        print("\n" + "-" * 70)
        print("\nAlternative Formulations:")
        alternatives = optimizer.suggest_alternatives(sample_query)

        for i, alt in enumerate(alternatives[:2], 1):
            print(f"\n{i}. {alt[:100]}...")

    except Exception as e:
        print(f"[Example: Would show optimization suggestions]")
        print(f"Error: {e}")
        print("\nExample Suggestions:")
        print("1. Add index on (borough, inspection_date)")
        print("2. Use window functions for running totals")
        print("3. Materialize frequently accessed aggregations")


def example_complex_analysis():
    """Complex multi-step analysis."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Complex Multi-Step Analysis")
    print("=" * 70)

    llm = Ollama(model="mistral")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    engine = SQLQueryEngine(dsn=dsn, llm=llm)
    session = InteractiveQuerySession(engine)

    analysis_questions = [
        "What's the total repair budget by borough for 2024?",
        "Which borough spent the most per inspection?",
        "What's the year-over-year change in spending?",
    ]

    print("\nComplex Analysis Workflow:\n")
    print("-" * 70)

    for i, question in enumerate(analysis_questions, 1):
        print(f"\nStep {i}: {question}")

        try:
            result = session.ask(question)
            print(f"  SQL: {result['sql'][:80]}...")
            print(f"  Results: {len(result['results'])} rows")
            if result["interpretation"]:
                print(f"  Insight: {result['interpretation'][:100]}...")
        except Exception as e:
            print(f"  [Would execute with real database]")


def example_error_handling():
    """Demonstrate error handling."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Error Handling")
    print("=" * 70)

    llm = Ollama(model="mistral")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    engine = SQLQueryEngine(dsn=dsn, llm=llm)

    problematic_questions = [
        "How many unicorns are in the database?",  # Non-existent table
        "What's the color of the wind?",  # Non-sensical question
        "Show me proprietary data",  # Potentially sensitive
    ]

    print("\nError Handling Examples:\n")
    print("-" * 70)

    for i, question in enumerate(problematic_questions, 1):
        print(f"\n{i}. Question: {question}")

        try:
            execution = engine.execute(question)

            if execution.error:
                print(f"   Error: {execution.error}")
            elif execution.row_count == 0:
                print(f"   No results found (query executed successfully)")
            else:
                print(f"   Returned {execution.row_count} results")

        except Exception as e:
            print(f"   Exception: {str(e)[:100]}...")


def example_execution_history():
    """View query execution history."""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Execution History & Audit Trail")
    print("=" * 70)

    llm = Ollama(model="mistral")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/nyc_data")

    engine = SQLQueryEngine(dsn=dsn, llm=llm)

    # Simulate some queries
    sample_questions = [
        "How many inspections per borough?",
        "What's the average repair cost?",
    ]

    print("\nExecution History:\n")
    print("-" * 70)

    for question in sample_questions:
        try:
            engine.execute(question)
        except:
            pass

    # Display history
    print("\nRecent Queries:")
    for i, execution in enumerate(engine.get_execution_history(limit=5), 1):
        print(f"\n{i}. {execution.natural_language}")
        print(f"   SQL: {execution.sql_query[:70]}...")
        print(f"   Status: {'✓ Success' if not execution.error else '✗ Error'}")
        if not execution.error:
            print(f"   Rows: {execution.row_count}, Time: {execution.execution_time_ms:.2f}ms")
        print(f"   Timestamp: {execution.timestamp}")


if __name__ == "__main__":
    print("\n")
    print("🚀 NYC Sidewalk Data Toolkit - SQL Query Engine Examples")
    print("=" * 70)
    print("\nThese examples demonstrate:")
    print("1. Natural language to SQL translation")
    print("2. Interactive sessions with follow-up questions")
    print("3. Database schema exploration")
    print("4. Query validation and safety checks")
    print("5. Query optimization suggestions")
    print("6. Complex multi-step analysis")
    print("7. Error handling and edge cases")
    print("8. Execution history and audit trails")
    print("\n" + "=" * 70)

    # Run examples
    try:
        example_basic_query()
        example_follow_up_questions()
        example_schema_exploration()
        example_query_validation()
        example_query_optimization()
        example_complex_analysis()
        example_error_handling()
        example_execution_history()
    except Exception as e:
        print(f"\nNote: Some examples require a running PostgreSQL database.")
        print(f"Set DATABASE_URL environment variable to connect to your database.")
        print(f"\nError: {e}")

    print("\n" + "=" * 70)
    print("✅ Examples Complete!")
    print("=" * 70)
    print("\nTo use this feature in your project:")
    print("1. Install dependencies: pip install langchain langchain-community ollama")
    print("2. Install Ollama: https://ollama.ai")
    print("3. Run Ollama server: ollama serve")
    print("4. Download a model: ollama pull mistral")
    print("5. Set DATABASE_URL environment variable")
    print("6. Import and use the classes in your code")
    print("\nFor more details, see: docs/LANGCHAIN_INTEGRATION_GUIDE.md")
    print()
