"""
Local grounded generator for HelpWise KB answers.

Model: google/flan-t5-small (Hugging Face, ~80MB, CPU).
Answers must be strictly grounded in the retrieved article text.
If generation is repetitive, hallucinated, or uncertain, returns None
to trigger the verified extractive fallback.
"""

from __future__ import annotations

import os
import re
from typing import Optional, Sequence

from schemas import KBAskHit

LLM_MODEL_NAME = os.getenv("HELPWISE_LLM_MODEL", "google/flan-t5-small")
LLM_ENABLED = os.getenv("HELPWISE_LLM_ENABLED", "1").strip() not in {"0", "false", "off"}

_tokenizer = None
_model = None

_FOREIGN_KEYWORDS = {
    "anyconnect",
    "cisco",
    "vpn",
    "outlook",
    "office365",
    "jetbrains",
    "pycharm",
    "intellij",
    "webstorm",
    "okta",
    "authenticator",
    "mfa",
    "wifi",
    "wi-fi",
    "ssid",
    "802.1x",
    "peap",
}


def _load_model():
    global _tokenizer, _model
    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    _tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
    _model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL_NAME)
    _model.eval()
    return _tokenizer, _model


def _build_prompt(question: str, hits: Sequence[KBAskHit]) -> str:
    hit = hits[0]
    return (
        "Rewrite the knowledge-article steps for an employee. "
        "Use only facts in the article. Keep product and network names from the article. "
        "Do not invent URLs, passwords, policies, or other products. "
        "Write a short numbered list.\n\n"
        f"Employee question: {question.strip()}\n"
        f"Article title: {hit.title}\n"
        f"Article steps: {hit.content.strip()}\n"
        "Friendly steps:"
    )


def _source_terms(hit: KBAskHit) -> set[str]:
    combined = f"{hit.title} {hit.content}".lower()
    terms = set(re.findall(r"[a-z0-9]+", combined))
    terms.update(re.findall(r"[a-z0-9][a-z0-9-]{2,}", combined))
    return terms


def _has_repeated_content(text: str) -> bool:
    """Detects repetitive loops or duplicated sentences in generated text."""
    normalized = re.sub(r"\s+", " ", text).strip().lower()

    # Split into candidate sentences / clauses
    clauses = [
        c.strip()
        for c in re.split(r"[.!?;\n]|(?=step\s*\d+:?)", normalized)
        if len(c.strip()) > 10
    ]
    seen = set()
    for clause in clauses:
        # Strip leading numbers or 'step x:'
        cleaned = re.sub(r"^(step\s*\d+:?|\d+[.)]\s*)", "", clause).strip()
        if len(cleaned) > 12:
            if cleaned in seen:
                return True
            seen.add(cleaned)

    # Check for repeated 3-grams
    words = re.findall(r"\b[a-z0-9-]+\b", normalized)
    if len(words) >= 6:
        trigrams = [tuple(words[i : i + 3]) for i in range(len(words) - 2)]
        counts: dict[tuple[str, ...], int] = {}
        for tri in trigrams:
            counts[tri] = counts.get(tri, 0) + 1
            if counts[tri] >= 3:
                return True

    return False


def _is_grounded(text: str, hits: Sequence[KBAskHit]) -> bool:
    """
    Strict validation to ensure generated text does not hallucinate,
    repeat, or introduce unsupported troubleshooting instructions.
    """
    if not hits or not text or len(text.strip()) < 15:
        return False

    hit = hits[0]
    source_words = _source_terms(hit)
    output_words = set(re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower()))
    if not output_words:
        return False

    # 1. Reject repetitive loops or duplicate step structures
    if _has_repeated_content(text):
        return False

    # 2. Reject foreign tool / product leakage not present in this article
    leaked_foreign = (output_words & _FOREIGN_KEYWORDS) - source_words
    if leaked_foreign:
        return False

    # 3. Reject common small-model hallucinations not supported by the article
    unsupported_patterns = [
        r"install\s+a\s+vpn\s+on\s+your\s+computer",
        r"download\s+the\s+vpn\s+software",
        r"restart\s+your\s+computer",
        r"check\s+your\s+internet\s+connection",
        r"reinstall\s+windows",
        r"contact\s+your\s+internet\s+service\s+provider",
    ]
    for pattern in unsupported_patterns:
        if re.search(pattern, text.lower()) and not re.search(pattern, hit.content.lower()):
            return False

    # 4. Require substantial keyword overlap with the source article content
    meaningful_overlap = output_words & source_words
    # Must share at least 3 distinct significant technical terms
    if len(meaningful_overlap) < 3:
        return False

    return True


def generate_grounded_answer(question: str, hits: Sequence[KBAskHit]) -> Optional[str]:
    """
    Generates a grounded answer using FLAN-T5-small.
    Returns None if generation is disabled, fails, or violates grounding rules.
    """
    if not LLM_ENABLED or not hits:
        return None

    try:
        tokenizer, model = _load_model()
        prompt = _build_prompt(question, hits)
        encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)

        generated = model.generate(
            **encoded,
            max_new_tokens=140,
            num_beams=2,
            repetition_penalty=1.8,
            no_repeat_ngram_size=3,
            early_stopping=True,
        )
        text = tokenizer.decode(generated[0], skip_special_tokens=True).strip()

        # Clean any trailing partial tokens
        text = re.sub(r"\s+", " ", text).strip()

        if not text or not _is_grounded(text, hits):
            return None

        return text
    except Exception:
        return None
