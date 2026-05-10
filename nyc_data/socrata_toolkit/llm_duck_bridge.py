from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests


@dataclass
class LLMAugmentConfig:
    endpoint: str = "http://localhost:1234/v1/chat/completions"
    model: str = "local-model"
    temperature: float = 0.1
    timeout: int = 60


DEFAULT_TAXONOMY = [
    "sidewalk_repair_needed",
    "ada_accessibility_issue",
    "contract_conflict",
    "budget_schedule_risk",
    "inspector_quality_issue",
    "other",
]


def build_prompt(text: str, taxonomy: list[str]) -> str:
    return (
        "Classify the NYC DOT sidewalk-related text into one taxonomy label and provide confidence (0-1). "
        f"taxonomy={taxonomy}. Return strict JSON with keys: label, confidence, rationale. Text: {text}"
    )


def llm_classify_text(text: str, cfg: LLMAugmentConfig, taxonomy: list[str] | None = None) -> dict[str, Any]:
    taxonomy = taxonomy or DEFAULT_TAXONOMY
    payload = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "messages": [
            {"role": "system", "content": "You are a strict JSON classifier."},
            {"role": "user", "content": build_prompt(text, taxonomy)},
        ],
    }
    resp = requests.post(cfg.endpoint, json=payload, timeout=cfg.timeout)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"label": "other", "confidence": 0.0, "rationale": content}


def augment_dataframe_with_llm(
    df: pd.DataFrame,
    text_column: str,
    cfg: LLMAugmentConfig,
    taxonomy: list[str] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    labels, confs, reasons = [], [], []
    for txt in out[text_column].fillna("").astype(str):
        result = llm_classify_text(txt, cfg=cfg, taxonomy=taxonomy)
        labels.append(result.get("label", "other"))
        confs.append(float(result.get("confidence", 0.0)))
        reasons.append(result.get("rationale", ""))
    out["llm_label"] = labels
    out["llm_confidence"] = confs
    out["llm_rationale"] = reasons
    return out
