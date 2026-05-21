"""Backward-compatible shim for Flask API and legacy imports."""

from .nlp.integration import triage_complaints

__all__ = ["triage_complaints"]
