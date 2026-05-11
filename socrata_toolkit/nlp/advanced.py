from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NLPResult:
    tokens: list[str]
    lemmas: list[str]
    entities: list[dict[str, str]]
    pos_tags: list[tuple[str, str]]
    sentiment: float
    summary: str


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "for", "to", "of", "in", "on", "with", "is", "are", "was", "were",
}


def preprocess_text(text: str) -> tuple[list[str], list[str]]:
    raw_tokens = [t.strip(".,!?;:()[]{}\"'").lower() for t in text.split()]
    tokens = [t for t in raw_tokens if t and t not in STOP_WORDS]
    # lightweight lemma fallback
    lemmas = [t[:-1] if t.endswith("s") and len(t) > 3 else t for t in tokens]
    return tokens, lemmas


def pos_and_ner(text: str) -> tuple[list[tuple[str, str]], list[dict[str, str]]]:
    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        pos = [(t.text, t.pos_) for t in doc]
        ents = [{"text": e.text, "label": e.label_} for e in doc.ents]
        return pos, ents
    except Exception:
        toks = text.split()
        pos = [(t, "NOUN" if t[:1].isupper() else "X") for t in toks]
        ents = [{"text": t, "label": "PROPN"} for t in toks if t[:1].isupper()]
        return pos, ents


def sentiment_score(text: str) -> float:
    try:
        from textblob import TextBlob

        return float(TextBlob(text).sentiment.polarity)
    except Exception:
        low = text.lower()
        score = 0.0
        for w in ["good", "safe", "improve", "success"]:
            if w in low:
                score += 0.2
        for w in ["bad", "danger", "delay", "fail"]:
            if w in low:
                score -= 0.2
        return max(-1.0, min(1.0, score))


def summarize_text(text: str, max_sentences: int = 2) -> str:
    sents = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    return ". ".join(sents[:max_sentences]) + ("." if sents else "")


def translate_text(text: str, target_lang: str = "es") -> str:
    try:
        from transformers import pipeline

        task = f"translation_en_to_{target_lang}"
        translator = pipeline(task)
        return translator(text, max_length=256)[0]["translation_text"]
    except Exception:
        return f"[translation unavailable -> {target_lang}] {text}"


def analyze_text(text: str) -> NLPResult:
    tokens, lemmas = preprocess_text(text)
    pos, ents = pos_and_ner(text)
    sent = sentiment_score(text)
    summary = summarize_text(text)
    return NLPResult(tokens=tokens, lemmas=lemmas, entities=ents, pos_tags=pos, sentiment=sent, summary=summary)
