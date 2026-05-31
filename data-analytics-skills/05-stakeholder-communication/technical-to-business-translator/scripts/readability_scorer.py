"""
Score the readability of text using Flesch-Kincaid grade level and related metrics.

Targets for business writing:
  - Executive audience: grade 8–10, sentences ≤ 20 words avg
  - Business analyst: grade 10–12
  - Technical peer: grade 12+ acceptable

Usage:
    python readability_scorer.py --input draft.txt
    python readability_scorer.py --text "Sentence one. Sentence two."
"""

import argparse
import re
import sys


def count_syllables(word: str) -> int:
    word = word.lower().strip(".,;:!?\"'")
    if not word:
        return 0
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith("le"):
        count = max(1, count - 1)
    return max(1, count)


def score_text(text: str) -> dict:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"\b[a-zA-Z'-]+\b", text)

    if not sentences or not words:
        return {"error": "Text too short to score"}

    word_count = len(words)
    sentence_count = len(sentences)
    syllable_count = sum(count_syllables(w) for w in words)

    avg_words_per_sentence = word_count / sentence_count
    avg_syllables_per_word = syllable_count / word_count

    # Flesch Reading Ease (higher = easier; 60–70 is plain English)
    flesh_ease = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
    flesh_ease = round(max(0, min(100, flesh_ease)), 1)

    # Flesch-Kincaid Grade Level
    fk_grade = 0.39 * avg_words_per_sentence + 11.8 * avg_syllables_per_word - 15.59
    fk_grade = round(max(1, fk_grade), 1)

    # Long sentences (> 25 words)
    long_sentences = [s for s in sentences if len(s.split()) > 25]

    # Passive voice indicator (rough heuristic)
    passive_count = len(re.findall(r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b", text))

    if fk_grade <= 8:
        grade_label = "Very accessible (elementary)"
    elif fk_grade <= 10:
        grade_label = "Accessible (executive-ready)"
    elif fk_grade <= 12:
        grade_label = "Moderate (business analyst)"
    else:
        grade_label = "Dense (technical audience)"

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_words_per_sentence": round(avg_words_per_sentence, 1),
        "avg_syllables_per_word": round(avg_syllables_per_word, 2),
        "flesch_reading_ease": flesh_ease,
        "flesch_kincaid_grade": fk_grade,
        "grade_label": grade_label,
        "long_sentences_count": len(long_sentences),
        "passive_voice_count": passive_count,
        "target_grade_executive": "8–10",
        "target_grade_business": "10–12",
    }


def main():
    parser = argparse.ArgumentParser(description="Score text readability.")
    parser.add_argument("--input", help="Path to text file")
    parser.add_argument("--text", help="Text string to score")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        parser.error("Provide --input or --text")

    result = score_text(text)
    print("\nReadability Score:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        technical = (
            "The multivariate regression model demonstrated statistically significant "
            "heteroscedasticity in the residuals, necessitating robust standard errors "
            "for accurate coefficient estimation. The Breusch-Pagan test confirmed this "
            "at p=0.002."
        )
        plain = (
            "Our analysis found that the relationship between marketing spend and revenue "
            "is not uniform — it varies by customer segment. We adjusted for this to ensure "
            "the estimates are reliable."
        )
        for label, text in [("Technical:", technical), ("Plain language:", plain)]:
            r = score_text(text)
            print(f"{label} Grade {r['flesch_kincaid_grade']} — {r['grade_label']}")
    else:
        main()
