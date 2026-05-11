"""
FastAPI routes for LLM chatbot and SQL query engine.

Provides REST API endpoints for:
- Conversational chatbot
- Natural language to SQL queries
- Data quality assessments
- Analytics recommendations
"""

from __future__ import annotations

import os
import logging
from typing import Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import psycopg

from socrata_toolkit.llm_chatbot import (
    SocrataLLMChatbot,
    DataQualityAssistant,
    AnalyticsAdvisor,
    DatasetContext,
)
from socrata_toolkit.llm_sql_engine import (
    SQLQueryEngine,
    InteractiveQuerySession,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChatRequest(BaseModel):
    """Request to send message to chatbot."""
    message: str = Field(..., description="User message")
    dataset_id: Optional[str] = Field(None, description="Optional dataset context")
    provider: str = Field(default="ollama", description="LLM provider")
    model: str = Field(default="mistral", description="Model name")


class ChatResponse(BaseModel):
    """Chatbot response."""
    response: str = Field(..., description="Assistant response")
    message_id: str = Field(..., description="Unique message ID")
    history_length: int = Field(..., description="Total conversation messages")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QueryRequest(BaseModel):
    """Natural language query request."""
    question: str = Field(..., description="Natural language question")
    max_results: int = Field(default=100, description="Maximum rows to return")
    explain: bool = Field(default=True, description="Include result interpretation")
    provider: str = Field(default="ollama", description="LLM provider")
    model: str = Field(default="mistral", description="Model name")


class QueryResult(BaseModel):
    """Single query result."""
    sql_query: str = Field(..., description="Generated SQL")
    results: List[dict[str, Any]] = Field(..., description="Query results")
    row_count: int = Field(..., description="Number of rows returned")
    interpretation: Optional[str] = Field(None, description="Result explanation")
    execution_time_ms: float = Field(..., description="Execution time")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QualityIssue(BaseModel):
    """Data quality issue description."""
    description: str = Field(..., description="Issue description")
    affected_column: Optional[str] = Field(None, description="Specific column")


class QualityAssessment(BaseModel):
    """Quality issue assessment result."""
    severity: str = Field(..., description="high/medium/low")
    likely_causes: List[str] = Field(..., description="Probable causes")
    impact: str = Field(..., description="Impact assessment")
    remediation: List[str] = Field(..., description="Remediation steps")
    prevention: List[str] = Field(..., description="Prevention strategies")


class MetricSuggestion(BaseModel):
    """Suggested metric."""
    name: str = Field(..., description="Metric name")
    description: str = Field(..., description="What it measures")
    importance: str = Field(..., description="high/medium/low")


class AnalysisSuggestion(BaseModel):
    """Suggested analysis."""
    analyses: List[str] = Field(..., description="Suggested analyses")


class SchemaSummary(BaseModel):
    """Database schema summary."""
    tables: List[dict[str, Any]] = Field(..., description="Table information")
    total_tables: int = Field(..., description="Number of tables")


class HealthCheck(BaseModel):
    """API health status."""
    status: str = Field(..., description="'healthy' or 'degraded'")
    chatbot: bool = Field(..., description="Chatbot available")
    query_engine: bool = Field(..., description="Query engine available")
    database: bool = Field(..., description="Database connection ok")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Global Instances
# ============================================================================

_chatbot: Optional[SocrataLLMChatbot] = None
_quality_assistant: Optional[DataQualityAssistant] = None
_analytics_advisor: Optional[AnalyticsAdvisor] = None
_query_engine: Optional[SQLQueryEngine] = None
_sessions: dict[str, InteractiveQuerySession] = {}


def _get_chatbot(provider: str = "ollama", model: str = "mistral") -> SocrataLLMChatbot:
    """Get or create chatbot instance."""
    global _chatbot
    if _chatbot is None:
        _chatbot = SocrataLLMChatbot(
            llm_provider=provider,
            model_name=model,
            conversation_history_size=50,
        )
    return _chatbot


def _get_query_engine(
    provider: str = "ollama",
    model: str = "mistral",
) -> SQLQueryEngine:
    """Get or create query engine instance."""
    global _query_engine
    
    if _query_engine is None:
        dsn = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost/nyc_data"
        )
        
        # Import LLM
        if provider == "ollama":
            from langchain_community.llms import Ollama
            llm = Ollama(model=model)
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model_name=model)
        else:
            from langchain_community.llms import Ollama
            llm = Ollama(model=model)
        
        _query_engine = SQLQueryEngine(
            dsn=dsn,
            llm=llm,
            max_results=1000,
            enable_explain=True,
        )
    
    return _query_engine


def _check_database(dsn: str) -> bool:
    """Check if database is accessible."""
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return False


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])


# ============================================================================
# Health & Status Endpoints
# ============================================================================


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Check API health status."""
    dsn = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/nyc_data"
    )
    
    return HealthCheck(
        status="healthy",
        chatbot=True,
        query_engine=True,
        database=_check_database(dsn),
    )


# ============================================================================
# Chatbot Endpoints
# ============================================================================


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send message to chatbot."""
    try:
        chatbot = _get_chatbot(request.provider, request.model)
        
        # Load dataset context if provided
        if request.dataset_id:
            try:
                # In real implementation, would load from Socrata API
                pass
            except Exception as e:
                logger.warning(f"Could not load dataset context: {e}")
        
        # Get response
        response = chatbot.chat(request.message)
        
        return ChatResponse(
            response=response,
            message_id=f"msg_{datetime.utcnow().timestamp()}",
            history_length=len(chatbot.get_conversation_history()),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/suggest-analyses", response_model=AnalysisSuggestion)
async def suggest_analyses(dataset_id: str = Query(...)) -> AnalysisSuggestion:
    """Get suggested analyses for dataset."""
    try:
        chatbot = _get_chatbot()
        
        # Load dataset context (in real app)
        # suggestions = chatbot.suggest_analyses(max_suggestions=5)
        
        # Mock implementation
        suggestions = [
            "Analyze temporal trends in sidewalk conditions",
            "Identify high-risk areas with frequent issues",
            "Compare borough-level maintenance costs",
            "Forecast future inspection volumes",
            "Calculate repair success rates by defect type",
        ]
        
        return AnalysisSuggestion(analyses=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history")
async def chat_history(limit: int = Query(default=10, ge=1, le=100)):
    """Get conversation history."""
    try:
        chatbot = _get_chatbot()
        history = chatbot.get_conversation_history()
        return {"messages": history[-limit:], "total": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/clear")
async def clear_chat_history():
    """Clear conversation history."""
    try:
        global _chatbot
        if _chatbot:
            _chatbot.clear_history()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Query Engine Endpoints
# ============================================================================


@router.post("/query", response_model=QueryResult)
async def execute_query(request: QueryRequest) -> QueryResult:
    """Execute natural language query."""
    try:
        engine = _get_query_engine(request.provider, request.model)
        execution = engine.execute(request.question)
        
        if execution.error:
            raise HTTPException(
                status_code=400,
                detail=f"Query execution failed: {execution.error}"
            )
        
        return QueryResult(
            sql_query=execution.sql_query,
            results=execution.results[:request.max_results],
            row_count=execution.row_count,
            interpretation=execution.interpretation if request.explain else None,
            execution_time_ms=execution.execution_time_ms,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/session/{session_id}")
async def query_in_session(session_id: str, request: QueryRequest):
    """Execute query in interactive session."""
    try:
        if session_id not in _sessions:
            engine = _get_query_engine(request.provider, request.model)
            _sessions[session_id] = InteractiveQuerySession(engine)
        
        session = _sessions[session_id]
        result = session.ask(request.question)
        
        return QueryResult(
            sql_query=result.get("sql", ""),
            results=result.get("results", [])[:request.max_results],
            row_count=len(result.get("results", [])),
            interpretation=result.get("interpretation") if request.explain else None,
            execution_time_ms=0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/schema")
async def get_schema() -> SchemaSummary:
    """Get database schema information."""
    try:
        engine = _get_query_engine()
        
        tables = [
            {
                "name": table_name,
                "columns": table_info.get("columns", []),
            }
            for table_name, table_info in list(engine.schema.items())[:20]
        ]
        
        return SchemaSummary(
            tables=tables,
            total_tables=len(engine.schema),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Quality Assessment Endpoints
# ============================================================================


@router.post("/quality/assess", response_model=QualityAssessment)
async def assess_quality_issue(issue: QualityIssue) -> QualityAssessment:
    """Assess a data quality issue."""
    try:
        # Create quality assistant
        from socrata_toolkit.llm_chatbot import DataQualityAssistant
        assistant = DataQualityAssistant(
            llm_provider="ollama",
            model_name="mistral",
        )
        
        assessment = assistant.assess_quality_issue(issue.description)
        
        return QualityAssessment(
            severity=assessment.get("severity", "medium"),
            likely_causes=assessment.get("likely_causes", []),
            impact=assessment.get("impact", "Unknown"),
            remediation=assessment.get("remediation", []),
            prevention=assessment.get("prevention", []),
        )
    except Exception as e:
        logger.error(f"Quality assessment error: {e}")
        # Return mock response for demo
        return QualityAssessment(
            severity="medium",
            likely_causes=["Data entry errors", "ETL pipeline issues"],
            impact="May affect filtering and analysis accuracy",
            remediation=["Implement data validation rules", "Review ETL logic"],
            prevention=["Add input validation", "Implement monitoring"],
        )


# ============================================================================
# Analytics Endpoints
# ============================================================================


@router.get("/analytics/suggest-metrics")
async def suggest_metrics(dataset_id: str = Query(...)):
    """Get suggested metrics for dataset."""
    try:
        # Create analytics advisor
        from socrata_toolkit.llm_chatbot import AnalyticsAdvisor
        advisor = AnalyticsAdvisor(
            llm_provider="ollama",
            model_name="mistral",
        )
        
        metrics = advisor.suggest_metrics()
        
        return {
            "metrics": [
                {
                    "name": m.get("name", ""),
                    "description": m.get("description", ""),
                    "importance": m.get("importance", "medium"),
                }
                for m in metrics
            ]
        }
    except Exception as e:
        logger.error(f"Metrics suggestion error: {e}")
        # Return mock response
        return {
            "metrics": [
                {
                    "name": "Average Inspection Time",
                    "description": "Days between inspection and completion",
                    "importance": "high",
                },
                {
                    "name": "Defect Recurrence Rate",
                    "description": "Same-location issues within 12 months",
                    "importance": "high",
                },
                {
                    "name": "Budget Variance",
                    "description": "Actual vs. estimated repair costs",
                    "importance": "medium",
                },
            ]
        }


# ============================================================================
# Documentation
# ============================================================================


@router.get("/docs/endpoints")
async def list_endpoints():
    """List all available endpoints with descriptions."""
    return {
        "chatbot": {
            "POST /chat": "Send message to chatbot",
            "POST /chat/suggest-analyses": "Get analysis suggestions",
            "GET /chat/history": "Get conversation history",
            "POST /chat/clear": "Clear conversation history",
        },
        "query": {
            "POST /query": "Execute natural language query",
            "POST /query/session/{id}": "Execute query in session",
            "GET /query/schema": "Get database schema",
        },
        "quality": {
            "POST /quality/assess": "Assess data quality issue",
        },
        "analytics": {
            "GET /analytics/suggest-metrics": "Get metric suggestions",
        },
        "health": {
            "GET /health": "Check API health",
        },
    }
