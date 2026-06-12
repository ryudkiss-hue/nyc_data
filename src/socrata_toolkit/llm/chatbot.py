"""
LangChain-based chatbot integration for NYC Sidewalk Data Toolkit.

Supports multiple LLM backends:
- Ollama (open-source, self-hosted)
- OpenAI (GPT-3.5/GPT-4)
- Hugging Face (open-source models)

Features:
- Conversational context management
- Vector-based semantic search for data exploration
- Dataset description generation
- Data quality insights
- Query suggestion and optimization
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from langchain_community.embeddings import HuggingFaceEmbeddings, OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_core.language_model import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


@dataclass
class ChatMessage:
    """Represents a message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    metadata: dict[str, Any] | None = None

@dataclass
class DatasetContext:
    """Context about a dataset for the chatbot."""
    fourfour: str
    title: str
    description: str
    columns: list[dict[str, str]]
    sample_values: dict[str, list[Any]] | None = None
    quality_score: float | None = None
    row_count: int | None = None

class SocrataLLMChatbot:
    """
    Conversational AI assistant for Socrata datasets.

    Uses LangChain with pluggable LLM backends for context-aware
    data exploration and analysis.
    """

    def __init__(
        self,
        llm_provider: str = "ollama",
        model_name: str = "mistral",
        embedding_provider: str = "ollama",
        conversation_history_size: int = 20,
    ):
        """
        Initialize chatbot with specified LLM backend.

        Args:
            llm_provider: "ollama", "openai", or "huggingface"
            model_name: Model identifier (e.g., "mistral", "gpt-3.5-turbo")
            embedding_provider: Provider for embeddings
            conversation_history_size: Max conversation turns to keep in memory
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.embedding_provider = embedding_provider
        self.conversation_history: list[ChatMessage] = []
        self.max_history = conversation_history_size
        self.dataset_context: DatasetContext | None = None

        # Initialize LLM
        self.llm = self._init_llm()

        # Initialize embeddings
        self.embeddings = self._init_embeddings()

    def _init_llm(self) -> BaseLanguageModel:
        """Initialize LLM based on provider."""
        if self.llm_provider == "ollama":
            return Ollama(model=self.model_name)
        elif self.llm_provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable not set")
                return ChatOpenAI(model_name=self.model_name, api_key=api_key)
            except ImportError:
                raise ImportError("Install langchain-openai for OpenAI support")
        elif self.llm_provider == "huggingface":
            try:
                from langchain_community.llms import HuggingFaceHub
                api_token = os.getenv("HUGGINGFACE_API_TOKEN")
                if not api_token:
                    raise ValueError("HUGGINGFACE_API_TOKEN environment variable not set")
                return HuggingFaceHub(
                    repo_id=self.model_name,
                    huggingfacehub_api_token=api_token
                )
            except ImportError:
                raise ImportError("Install huggingface-hub for Hugging Face support")
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")

    def _init_embeddings(self):
        """Initialize embeddings model."""
        if self.embedding_provider == "ollama":
            return OllamaEmbeddings(model=self.model_name)
        elif self.embedding_provider == "huggingface":
            return HuggingFaceEmbeddings()
        else:
            return None

    def set_dataset_context(self, context: DatasetContext) -> None:
        """Set the current dataset being discussed."""
        self.dataset_context = context

    def _build_system_prompt(self) -> str:
        """Build system prompt with dataset context."""
        base_prompt = """You are an expert data analyst assistant for NYC's Socrata data platform.
Your role is to help users explore, understand, and analyze datasets.

Be concise, accurate, and helpful. Use the provided dataset context to give specific insights.
When discussing data:
- Reference specific column names
- Suggest relevant queries or analyses
- Point out data quality considerations
- Explain patterns or anomalies

If you don't have relevant context, ask clarifying questions."""

        if self.dataset_context:
            context_str = f"""
Current Dataset Context:
- Title: {self.dataset_context.title}
- Description: {self.dataset_context.description}
- Dataset ID: {self.dataset_context.fourfour}
- Rows: {self.dataset_context.row_count or 'unknown'}
- Quality Score: {self.dataset_context.quality_score or 'unknown'}

Columns:
{json.dumps([{'name': col['name'], 'type': col.get('type', 'string')} for col in self.dataset_context.columns], indent=2)}
"""
            return base_prompt + context_str

        return base_prompt

    def chat(self, user_message: str) -> str:
        """
        Process user message and return assistant response.

        Args:
            user_message: User's input message

        Returns:
            Assistant's response
        """
        # Add user message to history
        self.conversation_history.append(ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

        # Build conversation context
        system_prompt = self._build_system_prompt()

        # Create prompt template with conversation history
        history_str = self._format_conversation_history()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"{history_str}\n\nUser: {user_message}")
        ])

        # Generate response
        chain = prompt | self.llm | StrOutputParser()
        response = chain.invoke({})

        # Add assistant response to history
        self.conversation_history.append(ChatMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

        # Trim conversation history
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        return response

    def _format_conversation_history(self) -> str:
        """Format conversation history for prompt."""
        if not self.conversation_history:
            return ""

        # Keep only recent history
        recent = self.conversation_history[-10:]
        history_lines = []
        for msg in recent:
            prefix = "Assistant:" if msg.role == "assistant" else "User:"
            history_lines.append(f"{prefix} {msg.content}")

        return "\n".join(history_lines)

    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Get conversation history as list of dicts."""
        return [asdict(msg) for msg in self.conversation_history]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()

    def suggest_analyses(self, max_suggestions: int = 5) -> list[str]:
        """
        Generate suggested analyses for current dataset.

        Args:
            max_suggestions: Number of suggestions to return

        Returns:
            List of analysis suggestions
        """
        if not self.dataset_context:
            return []

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data analysis expert. Suggest specific analyses for datasets."),
            ("human", f"""Based on this dataset:
Title: {self.dataset_context.title}
Description: {self.dataset_context.description}

Suggest {max_suggestions} specific analyses or queries a user might want to run.
Return as JSON list of strings.

Example format: {{"suggestions": ["Find records with null values", "Calculate average by date"]}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        result = chain.invoke({})

        suggestions = result.get("suggestions", [])
        return suggestions[:max_suggestions]

    def explain_column(self, column_name: str) -> str:
        """
        Generate explanation for a specific column.

        Args:
            column_name: Column to explain

        Returns:
            Explanation of the column
        """
        if not self.dataset_context:
            return "No dataset context available"

        # Find column info
        col_info = next(
            (col for col in self.dataset_context.columns if col["name"] == column_name),
            None
        )

        if not col_info:
            return f"Column '{column_name}' not found in dataset"

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data dictionary expert. Explain dataset columns clearly and concisely."),
            ("human", f"""Explain this column in the context of NYC sidewalk data:

Column Name: {column_name}
Type: {col_info.get('type', 'string')}
Description: {col_info.get('description', 'No description available')}
Dataset: {self.dataset_context.title}

Provide a 2-3 sentence explanation suitable for analysts and non-technical users.""")
        ])

        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({})

    def validate_query(self, query_description: str) -> dict[str, Any]:
        """
        Validate if a user's query is feasible with current dataset.

        Args:
            query_description: Natural language description of desired query

        Returns:
            Dict with validation result and feasibility assessment
        """
        if not self.dataset_context:
            return {"feasible": False, "reason": "No dataset context"}

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data feasibility expert. Assess if queries are possible with given data."),
            ("human", f"""Can we answer this question with this dataset?

Question: {query_description}

Available columns: {', '.join(col['name'] for col in self.dataset_context.columns)}
Dataset size: {self.dataset_context.row_count or 'unknown'} rows

Return JSON with:
- feasible: boolean
- reason: explanation
- suggestions: list of alternative queries if not feasible

Format: {{"feasible": true/false, "reason": "...", "suggestions": []}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        return chain.invoke({})

class DataQualityAssistant(SocrataLLMChatbot):
    """
    Specialized chatbot for data quality assessment and monitoring.
    """

    def assess_quality_issue(self, issue_description: str) -> dict[str, Any]:
        """
        Provide analysis and recommendations for a data quality issue.

        Args:
            issue_description: Description of the quality issue

        Returns:
            Assessment with recommendations
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in data quality management.
Analyze quality issues and suggest remediation strategies.
Consider root causes, impact, and solutions."""),
            ("human", f"""Data Quality Issue:
{issue_description}

Provide analysis in JSON format with:
- severity: high/medium/low
- likely_causes: list of probable causes
- impact: assessment of data impact
- remediation: list of specific solutions
- prevention: how to prevent in future""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        return chain.invoke({})

    def recommend_validations(self, column_name: str) -> list[str]:
        """
        Recommend data validations for a column.

        Args:
            column_name: Column to recommend validations for

        Returns:
            List of suggested validations
        """
        if not self.dataset_context:
            return []

        col_info = next(
            (col for col in self.dataset_context.columns if col["name"] == column_name),
            None
        )

        if not col_info:
            return []

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data validation expert. Recommend specific, implementable validations."),
            ("human", f"""Recommend data quality checks for:

Column: {column_name}
Type: {col_info.get('type', 'string')}
Dataset: {self.dataset_context.title}

Return JSON with validation list:
{{"validations": ["check1", "check2", ...]}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        result = chain.invoke({})
        return result.get("validations", [])

class AnalyticsAdvisor(SocrataLLMChatbot):
    """
    Specialized chatbot for advanced analytics and insights.
    """

    def suggest_metrics(self) -> list[dict[str, str]]:
        """
        Suggest relevant metrics for the dataset.

        Returns:
            List of suggested metrics with descriptions
        """
        if not self.dataset_context:
            return []

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a business analytics expert. Suggest relevant, actionable metrics."),
            ("human", f"""For this dataset: {self.dataset_context.title}

Description: {self.dataset_context.description}

Suggest key performance indicators and metrics.

Return JSON:
{{"metrics": [{{"name": "metric_name", "description": "what it measures", "importance": "high/medium/low"}}]}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        result = chain.invoke({})
        return result.get("metrics", [])

    def identify_patterns(self, findings: str) -> list[str]:
        """
        Analyze findings to identify patterns and insights.

        Args:
            findings: Raw findings or summary of data exploration

        Returns:
            List of identified patterns and insights
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data scientist. Extract meaningful patterns and insights from findings."),
            ("human", f"""Analyze these findings and identify patterns:

{findings}

Return JSON with patterns:
{{"patterns": ["pattern1", "pattern2", ...]}}""")
        ])

        chain = prompt | self.llm | JsonOutputParser()
        result = chain.invoke({})
        return result.get("patterns", [])
