# LangChain Chatbot & SQL Query Engine Integration Guide

## Overview

This guide covers the complete integration of LangChain-based AI assistants for the NYC Sidewalk Data Toolkit, including:

1. **Conversational Chatbot** - Multi-turn conversations with context awareness
2. **SQL Query Engine** - Natural language to SQL translation (Wolfram-like functionality)
3. **Specialized Assistants** - Data quality and analytics advisors

## Installation & Setup

### 1. Install Dependencies

```bash
# Using Poetry
poetry add langchain langchain-community ollama openai huggingface-hub pydantic

# Or via pip
pip install langchain langchain-community ollama openai huggingface-hub pydantic
```

### 2. Configure LLM Provider

Choose one of these options:

#### Option A: Ollama (Recommended - Open Source, Self-Hosted)

```bash
# Install Ollama from https://ollama.ai
# Download a model
ollama pull mistral

# Run Ollama server
ollama serve
```

#### Option B: OpenAI

```bash
# Set environment variable
export OPENAI_API_KEY="sk-..."

# Or in Python
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
```

#### Option C: Hugging Face

```bash
export HUGGINGFACE_API_TOKEN="hf_..."
```

## Quick Start

### 1. Chatbot Usage

```python
from socrata_toolkit.llm_chatbot import SocrataLLMChatbot, DatasetContext

# Initialize chatbot with Ollama
chatbot = SocrataLLMChatbot(
    llm_provider="ollama",
    model_name="mistral",
    conversation_history_size=20
)

# Set dataset context
context = DatasetContext(
    fourfour="example-dataset-id",
    title="NYC Sidewalk Inspection Records",
    description="Historical inspection data for NYC sidewalks",
    columns=[
        {"name": "inspection_id", "type": "integer"},
        {"name": "location", "type": "string"},
        {"name": "inspection_date", "type": "date"},
        {"name": "condition", "type": "string"},
    ],
    row_count=50000,
    quality_score=0.95
)

chatbot.set_dataset_context(context)

# Have a conversation
response = chatbot.chat("What are the most common sidewalk conditions?")
print(response)

# Continue conversation
response = chatbot.chat("How many records do we have for Manhattan?")
print(response)
```

### 2. SQL Query Engine Usage

```python
from socrata_toolkit.llm_sql_engine import SQLQueryEngine, InteractiveQuerySession
from langchain_community.llms import Ollama

# Initialize LLM
llm = Ollama(model="mistral")

# Initialize query engine
engine = SQLQueryEngine(
    dsn="postgresql://user:password@localhost/nyc_data",
    llm=llm,
    max_results=1000
)

# Execute natural language query
execution = engine.execute("How many sidewalk inspections were completed in Brooklyn last year?")

print(f"SQL: {execution.sql_query}")
print(f"Results: {len(execution.results)} rows")
print(f"Interpretation: {execution.interpretation}")

# Interactive session with follow-up questions
session = InteractiveQuerySession(engine)

result1 = session.ask("How many potholes were reported in the Bronx?")
result2 = session.ask("What about Manhattan?")
result3 = session.ask("Which borough had the most complaints?")
```

## Advanced Usage

### 1. Data Quality Assistant

```python
from socrata_toolkit.llm_chatbot import DataQualityAssistant, DatasetContext

# Initialize specialized assistant
quality_assistant = DataQualityAssistant(
    llm_provider="openai",
    model_name="gpt-3.5-turbo"
)

quality_assistant.set_dataset_context(context)

# Assess quality issues
issue = """We're seeing 15% null values in the 'condition' column and 
inconsistent formatting in location strings."""

assessment = quality_assistant.assess_quality_issue(issue)
print(assessment)
# Output:
# {
#   "severity": "medium",
#   "likely_causes": ["Data entry errors", "ETL failures", "Legacy data"],
#   "impact": "Can affect filtering and analysis accuracy",
#   "remediation": ["Run data standardization", "Implement validation rules"],
#   "prevention": ["Add input validation", "Improve documentation"]
# }

# Get validation recommendations
validations = quality_assistant.recommend_validations("condition")
print(validations)
```

### 2. Analytics Advisor

```python
from socrata_toolkit.llm_chatbot import AnalyticsAdvisor

# Initialize analytics assistant
advisor = AnalyticsAdvisor(
    llm_provider="ollama",
    model_name="mistral"
)

advisor.set_dataset_context(context)

# Get suggested metrics
metrics = advisor.suggest_metrics()
for metric in metrics:
    print(f"- {metric['name']}: {metric['description']} (Importance: {metric['importance']})")

# Identify patterns from findings
findings = """
- 45% of inspections in Q4 found critical issues
- Manhattan has 2x the complaint rate of other boroughs
- Spring months show 30% fewer issues than winter
"""

patterns = advisor.identify_patterns(findings)
for pattern in patterns:
    print(f"- {pattern}")
```

### 3. Query Optimization

```python
from socrata_toolkit.llm_sql_engine import QueryOptimizer

# Initialize optimizer
optimizer = QueryOptimizer(engine, llm)

# Get optimization suggestions
optimizations = optimizer.suggest_optimizations(
    "SELECT * FROM sidewalk_inspections WHERE condition = 'poor' ORDER BY inspection_date"
)

for opt in optimizations:
    print(f"Optimization: {opt['optimization']}")
    print(f"Expected benefit: {opt['benefit']}")
```

## Integration with CLI

Add chatbot commands to the CLI:

```python
# In socrata_toolkit/cli.py

import click
from socrata_toolkit.llm_chatbot import SocrataLLMChatbot, DatasetContext
from socrata_toolkit.llm_sql_engine import SQLQueryEngine, InteractiveQuerySession

@main.command("chat")
@click.option("--dataset", help="Dataset 4-4 to discuss")
@click.option("--provider", default="ollama", help="LLM provider (ollama/openai/huggingface)")
@click.option("--model", help="Model name")
def chat_cmd(dataset, provider, model):
    """Start interactive chatbot session."""
    chatbot = SocrataLLMChatbot(
        llm_provider=provider,
        model_name=model or provider
    )
    
    # If dataset provided, load context
    if dataset:
        client = _client()
        meta = client.get_metadata(domain, dataset)
        context = DatasetContext(
            fourfour=dataset,
            title=meta.get("name", ""),
            description=meta.get("description", ""),
            columns=[{"name": col["name"], "type": col.get("type", "string")} 
                    for col in meta.get("columns", [])],
            row_count=meta.get("rows_total_count", 0)
        )
        chatbot.set_dataset_context(context)
    
    # Interactive loop
    import readline
    print(f"Chat initialized with {provider} ({model})")
    print("Type 'exit' to quit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() == 'exit':
                break
            response = chatbot.chat(user_input)
            print(f"Assistant: {response}\n")
        except KeyboardInterrupt:
            break

@main.command("query")
@click.option("--question", help="Natural language question")
@click.option("--interactive", is_flag=True, help="Start interactive session")
@click.option("--dsn", help="Database connection string")
@click.option("--provider", default="ollama")
@click.option("--model", default="mistral")
def query_cmd(question, interactive, dsn, provider, model):
    """Query database using natural language."""
    from langchain_community.llms import Ollama
    from langchain_openai import ChatOpenAI
    
    # Initialize LLM
    if provider == "ollama":
        llm = Ollama(model=model)
    elif provider == "openai":
        llm = ChatOpenAI(model_name=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Initialize engine
    engine = SQLQueryEngine(dsn=dsn, llm=llm)
    
    if interactive:
        session = InteractiveQuerySession(engine)
        print("Interactive query session (type 'exit' to quit)")
        while True:
            try:
                q = input("Question: ").strip()
                if q.lower() == 'exit':
                    break
                result = session.ask(q)
                print(f"SQL: {result['sql']}")
                print(f"Results: {len(result['results'])} rows")
                if result['interpretation']:
                    print(f"Interpretation: {result['interpretation']}")
                print()
            except KeyboardInterrupt:
                break
    else:
        execution = engine.execute(question)
        click.echo(f"SQL Query:\n{execution.sql_query}\n")
        click.echo(f"Results: {execution.row_count} rows")
        if execution.results:
            import json
            click.echo(json.dumps(execution.results[:5], indent=2, default=str))
        if execution.interpretation:
            click.echo(f"\nInterpretation: {execution.interpretation}")
```

## API Integration

### FastAPI Integration

```python
# In socrata_toolkit/api/llm_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from socrata_toolkit.llm_chatbot import SocrataLLMChatbot
from socrata_toolkit.llm_sql_engine import SQLQueryEngine

router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])

class ChatRequest(BaseModel):
    message: str
    dataset_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    history_length: int

class QueryRequest(BaseModel):
    question: str
    max_results: int = 100

class QueryResponse(BaseModel):
    sql_query: str
    results: List[Dict[str, Any]]
    row_count: int
    interpretation: str | None

# Global instances
chatbot = SocrataLLMChatbot(llm_provider="ollama", model_name="mistral")
query_engine = None  # Initialized with DSN

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send message to chatbot."""
    try:
        response = chatbot.chat(request.message)
        return ChatResponse(
            response=response,
            history_length=len(chatbot.conversation_history)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute natural language query."""
    if not query_engine:
        raise HTTPException(status_code=500, detail="Query engine not initialized")
    
    try:
        execution = query_engine.execute(request.question)
        return QueryResponse(
            sql_query=execution.sql_query,
            results=execution.results[:request.max_results],
            row_count=execution.row_count,
            interpretation=execution.interpretation
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions")
async def get_suggestions(dataset_id: str):
    """Get analysis suggestions for dataset."""
    try:
        suggestions = chatbot.suggest_analyses()
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Streamlit Integration

```python
# In socrata_toolkit/streamlit_llm.py

import streamlit as st
from socrata_toolkit.llm_chatbot import SocrataLLMChatbot, DatasetContext
from socrata_toolkit.llm_sql_engine import SQLQueryEngine, InteractiveQuerySession

st.set_page_config(page_title="Data Assistant", layout="wide")

st.title("🤖 NYC Data Assistant")

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    provider = st.selectbox("LLM Provider", ["ollama", "openai", "huggingface"])
    model = st.text_input("Model Name", "mistral")

# Initialize chatbot
if "chatbot" not in st.session_state:
    st.session_state.chatbot = SocrataLLMChatbot(
        llm_provider=provider,
        model_name=model
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat interface
st.header("Chat with Your Data")

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Ask me anything about your data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get response
    response = st.session_state.chatbot.chat(prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    with st.chat_message("assistant"):
        st.markdown(response)

# Suggested analyses
if st.session_state.chatbot.dataset_context:
    st.divider()
    st.header("Suggested Analyses")
    suggestions = st.session_state.chatbot.suggest_analyses()
    for i, suggestion in enumerate(suggestions, 1):
        if st.button(f"📊 {suggestion}"):
            st.session_state.messages.append({
                "role": "user",
                "content": suggestion
            })
            st.rerun()
```

## Performance Tuning

### 1. Model Selection

**For Speed:**
- Ollama: `tinyllama` (fast, minimal resources)
- OpenAI: `gpt-3.5-turbo` (fast, accurate)

**For Accuracy:**
- Ollama: `mistral` (balanced)
- OpenAI: `gpt-4` (most capable)

### 2. Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor

def batch_query(engine, questions: List[str], max_workers: int = 5):
    """Execute multiple queries in parallel."""
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(engine.execute, question)
            for question in questions
        ]
        
        for future in futures:
            results.append(future.result())
    
    return results
```

### 3. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_translate(question: str, engine: SQLQueryEngine) -> str:
    """Cache SQL translations."""
    return engine.translate_to_sql(question)
```

## Troubleshooting

### Issue: LLM Connection Error

```
langchain_core.exceptions.LLMException: Failed to connect to Ollama
```

**Solution:**
- Ensure Ollama is running: `ollama serve`
- Check model is available: `ollama list`
- Verify localhost connection in firewall

### Issue: SQL Validation Errors

```
Query validation failed: relation "sidewalk_inspections" does not exist
```

**Solution:**
- Verify table names with `\dt` in psql
- Check database DSN is correct
- Ensure user has SELECT permissions

### Issue: LLM Hallucination (Generating Wrong SQL)

**Solution:**
- Provide more context in dataset description
- Use more capable models (mistral > tinyllama)
- Validate all translated queries before execution
- Use EXPLAIN to dry-run queries

## Configuration Examples

### Production Setup with OpenAI

```python
# config/llm.yaml
llm:
  provider: openai
  model: gpt-4
  temperature: 0.3
  max_tokens: 2000

database:
  dsn: postgresql://prod_user:${DB_PASSWORD}@prod.db.example.com/nyc_data
  max_connections: 10

cache:
  type: redis
  ttl_seconds: 3600

logging:
  level: INFO
  format: json
```

```python
# Load in Python
import yaml
import os

with open("config/llm.yaml") as f:
    config = yaml.safe_load(f)

# Override with env vars
config["llm"]["model"] = os.getenv("LLM_MODEL", config["llm"]["model"])

llm = ChatOpenAI(
    model_name=config["llm"]["model"],
    temperature=config["llm"]["temperature"]
)
```

### Development Setup with Ollama

```yaml
# config/llm.dev.yaml
llm:
  provider: ollama
  model: mistral
  temperature: 0.7
  
database:
  dsn: postgresql://dev:dev@localhost/nyc_data_dev

cache:
  type: memory
  ttl_seconds: 300
```

## Best Practices

1. **Always Validate Queries** - Never execute untranslated user input
2. **Set Row Limits** - Use `max_results` to prevent memory issues
3. **Log Everything** - Track query translations and results for debugging
4. **Test Models** - Benchmark different models for your use case
5. **Monitor Costs** - OpenAI API calls can be expensive; use Ollama for dev
6. **Document Schemas** - Better descriptions = better SQL generation
7. **Handle Errors** - Wrap LLM calls in try-except blocks
8. **Version Models** - Track which model version produced which results

## Advanced Examples

### Multi-turn Data Exploration

```python
session = InteractiveQuerySession(engine)

# Start exploration
r1 = session.ask("What are the top 5 inspection issues?")
# → Auto-translates to SQL

r2 = session.ask("How many of those are in Brooklyn?")
# → Maintains context from r1

r3 = session.ask("What's the average fix time?")
# → Can reference previous results

# Analyze conversation
history = session.get_conversation()
for item in history:
    print(f"Q: {item['question']}")
    print(f"A: {item['interpretation']}")
```

### Custom Domain Vocabulary

```python
# Extend system prompt with domain knowledge
custom_context = """
This is NYC Department of Transportation sidewalk data.
Common terms:
- "pothole" = defect_type:'pothole'
- "crack" = defect_type:'crack'
- "raised edge" = defect_type:'raised_edge'
Borough codes: MN=Manhattan, BK=Brooklyn, QN=Queens, BX=Bronx, SI=Staten Island
"""

# Incorporate into queries
enhanced_question = custom_context + "\nQuestion: " + user_question
```

## See Also

- [LangChain Documentation](https://langchain.readthedocs.io/)
- [Ollama Models](https://ollama.ai/library)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Vector Database Setup](../docs/vector_search.md)
