"""
HelpWise AI — Knowledge retrieval for /api/kb/ask

Primary path: Hugging Face sentence-transformers embeddings (all-MiniLM-L6-v2)
stored in ChromaDB, ranked by cosine similarity. Answers are still *copied*
from articles (extractive). This is NOT a generative LLM.

Fallback if embeddings/Chroma cannot load: previous in-memory TF-IDF + intent.
Fallback if nothing is similar enough: tell the user to create a ticket.
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from schemas import KBArticle, KBAskHit, KBAskResponse
import llm as kb_llm

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._+-]*", re.IGNORECASE)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are",
    "my", "me", "i", "it", "this", "that", "when", "how", "what", "why", "can", "please",
    "help", "issue", "error", "problem", "not", "from", "you", "your", "we", "our",
}

_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "vpn": ("anyconnect", "cisco", "certificate", "tls"),
    "anyconnect": ("vpn", "cisco", "certificate"),
    "wifi": ("wireless", "802", "eap", "ssid", "helpwise-secure"),
    "wi-fi": ("wireless", "802", "eap", "ssid"),
    "wireless": ("wifi", "802", "eap"),
    "mfa": ("authenticator", "okta", "entra", "reset"),
    "authenticator": ("mfa", "okta"),
    "outlook": ("office", "email", "crash"),
    "email": ("outlook", "office"),
    "jetbrains": ("intellij", "pycharm", "webstorm", "license", "ide"),
    "pycharm": ("jetbrains", "ide", "license"),
    "intellij": ("jetbrains", "ide", "license"),
    "license": ("jetbrains", "ide"),
}

_INTENT_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ("kb-105", (r"wifi", r"wi-?fi", r"wireless", r"ssid", r"802\.1x", r"helpwise-secure")),
    ("kb-101", (r"vpn", r"anyconnect", r"cisco", r"tls handshake", r"0x800b0109")),
    ("kb-103", (r"outlook", r"0xc0000005", r"email.+(crash|open|start|won'?t)")),
    ("kb-104", (r"\bmfa\b", r"authenticator", r"\bokta\b", r"entra", r"locked out", r"lost my phone", r"can'?t log in", r"cannot log in", r"new phone")),
    ("kb-102", (r"jetbrains", r"pycharm", r"intellij", r"webstorm", r"ide license", r"developer license", r"install.*(pycharm|intellij|ide)")),
]

_TOPIC_LABELS = {
    "kb-101": "a VPN / home-network connection problem",
    "kb-102": "a software license (JetBrains / IDE) request",
    "kb-103": "Outlook or email not starting",
    "kb-104": "a login / MFA / authenticator problem",
    "kb-105": "office Wi-Fi setup",
}

_INTENT_BOOST = 0.42
_TITLE_BOOST = 0.12
_TAG_BOOST = 0.08

_EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_DEFAULT_CHROMA_DIR = Path(__file__).resolve().parent / "chroma_data"
_COLLECTION_NAME = "helpwise_kb"

_embed_model = None
_chroma_client = None
_chroma_fp: Optional[str] = None
_chroma_collection = None

_SEMANTIC_DISCLAIMER = (
    "Articles were ranked with Hugging Face MiniLM embeddings in ChromaDB. "
    "No generative LLM wrote this answer; steps are copied from the matching article."
)
_TFIDF_DISCLAIMER = (
    "Embedding/ChromaDB was unavailable, so in-memory TF-IDF plus intent phrases were used. "
    "No generative LLM wrote this answer."
)


def _tokenize(text: str) -> List[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text or "") if tok.lower() not in _STOPWORDS]


def _expand_query_tokens(tokens: Sequence[str]) -> List[str]:
    expanded: List[str] = list(tokens)
    for tok in tokens:
        expanded.extend(_SYNONYMS.get(tok, ()))
    return expanded


def _tf(tokens: Sequence[str]) -> Dict[str, float]:
    counts: Dict[str, float] = {}
    for tok in tokens:
        counts[tok] = counts.get(tok, 0.0) + 1.0
    if not counts:
        return counts
    n = float(len(tokens))
    return {tok: c / n for tok, c in counts.items()}


def _idf(docs: Sequence[Sequence[str]]) -> Dict[str, float]:
    n = len(docs) or 1
    df: Dict[str, int] = {}
    for tokens in docs:
        for tok in set(tokens):
            df[tok] = df.get(tok, 0) + 1
    return {tok: math.log((n + 1) / (freq + 1)) + 1.0 for tok, freq in df.items()}


def _tfidf_vector(tf: Dict[str, float], idf: Dict[str, float]) -> Dict[str, float]:
    return {tok: weight * idf.get(tok, 1.0) for tok, weight in tf.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(val * b.get(key, 0.0) for key, val in a.items())
    na = math.sqrt(sum(val * val for val in a.values()))
    nb = math.sqrt(sum(val * val for val in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _article_text(article: KBArticle) -> str:
    tags = " ".join(article.tags or [])
    return f"{article.title} {article.excerpt} {article.content} {tags} {article.category}"


def _intent_boost(article_id: str, question: str) -> float:
    q = question.lower()
    for target_id, patterns in _INTENT_RULES:
        if target_id != article_id:
            continue
        for pattern in patterns:
            if re.search(pattern, q, flags=re.IGNORECASE):
                return _INTENT_BOOST
    return 0.0


def _overlap_boost(article: KBArticle, query_tokens: Sequence[str]) -> float:
    query_set = set(query_tokens)
    title_set = set(_tokenize(article.title))
    tag_set = set(_tokenize(" ".join(article.tags or [])))
    boost = 0.0
    if query_set & title_set:
        boost += _TITLE_BOOST * len(query_set & title_set)
    if query_set & tag_set:
        boost += _TAG_BOOST * len(query_set & tag_set)
    return boost


def _confidence_label(score: float) -> str:
    if score >= 0.5:
        return "High"
    if score >= 0.22:
        return "Medium"
    return "Low"


def _user_no_match_answer() -> str:
    return (
        "I could not find a matching how-to article for this question.\n\n"
        "Please create an incident ticket and include what you were trying to do. "
        "An IT agent will help from there."
    )


def _extractive_user_answer(hits: Sequence[KBAskHit]) -> str:
    top = hits[0]
    return (
        "Here is what our knowledge base recommends.\n\n"
        f"{top.content.strip()}\n\n"
        "If this does not fix it, please create an incident ticket so IT can help."
    )


def _finalize_response(
    question: str,
    hits: List[KBAskHit],
    retrieval_method: str,
    vector_database: str,
    disclaimer: str,
) -> KBAskResponse:
    if not hits:
        return KBAskResponse(
            question=question.strip(),
            answer=_user_no_match_answer(),
            matched_articles=hits,
            retrieval_method=retrieval_method,
            generation_mode="no_match",
            llm_used=False,
            vector_database=vector_database,
            disclaimer=disclaimer,
        )

    llm_text = None
    try:
        llm_text = kb_llm.generate_grounded_answer(question, hits)
    except Exception:
        llm_text = None

    if llm_text:
        return KBAskResponse(
            question=question.strip(),
            answer=llm_text,
            matched_articles=hits,
            retrieval_method=retrieval_method,
            generation_mode="flan_t5_small_grounded",
            llm_used=True,
            vector_database=vector_database,
            disclaimer=disclaimer,
        )

    return KBAskResponse(
        question=question.strip(),
        answer=_extractive_user_answer(hits),
        matched_articles=hits,
        retrieval_method=retrieval_method,
        generation_mode="extractive_fallback",
        llm_used=False,
        vector_database=vector_database,
        disclaimer=disclaimer,
    )


def _hits_from_ranked(
    ranked: Sequence[Tuple[float, KBArticle]],
    top_k: int,
    min_score: float,
) -> List[KBAskHit]:
    hits: List[KBAskHit] = []
    for score, article in ranked[: max(top_k, 0)]:
        if score < min_score:
            continue
        hits.append(
            KBAskHit(
                id=article.id,
                title=article.title,
                category=article.category,
                excerpt=article.excerpt,
                content=article.content,
                tags=article.tags,
                score=round(float(score), 4),
            )
        )
    return hits


def _answer_with_tfidf(
    question: str,
    article_list: Sequence[KBArticle],
    top_k: int,
    min_score: float,
) -> KBAskResponse:
    original_tokens = _tokenize(question)
    query_tokens = _expand_query_tokens(original_tokens)
    doc_tokens = [_tokenize(_article_text(article)) for article in article_list]
    idf = _idf(doc_tokens)
    query_vec = _tfidf_vector(_tf(query_tokens), idf)

    scored: List[Tuple[float, KBArticle]] = []
    for article, tokens in zip(article_list, doc_tokens):
        cosine = _cosine(query_vec, _tfidf_vector(_tf(tokens), idf))
        score = cosine + _overlap_boost(article, original_tokens) + _intent_boost(article.id, question)
        scored.append((score, article))
    scored.sort(key=lambda item: item[0], reverse=True)
    hits = _hits_from_ranked(scored, top_k, min_score)
    return _finalize_response(
        question,
        hits,
        retrieval_method="in_memory_tfidf_cosine_plus_intent",
        vector_database="none",
        disclaimer=_TFIDF_DISCLAIMER,
    )


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
    return _embed_model


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        configured = os.getenv("HELPWISE_CHROMA_DIR", str(_DEFAULT_CHROMA_DIR)).strip()
        if configured in {":memory:", "memory"}:
            _chroma_client = chromadb.Client()
        else:
            Path(configured).mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=configured)
    return _chroma_client


def _article_fingerprint(articles: Sequence[KBArticle]) -> str:
    return "|".join(f"{a.id}:{a.updated_at}:{a.title}" for a in sorted(articles, key=lambda item: item.id))


def _ensure_chroma_collection(articles: Sequence[KBArticle]):
    global _chroma_fp, _chroma_collection

    fp = _article_fingerprint(articles)
    client = _get_chroma_client()
    if _chroma_collection is not None and _chroma_fp == fp:
        return _chroma_collection

    try:
        client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    model = _get_embed_model()
    documents = [_article_text(article) for article in articles]
    embeddings = model.encode(documents, normalize_embeddings=True).tolist()
    collection.upsert(
        ids=[article.id for article in articles],
        documents=documents,
        embeddings=embeddings,
        metadatas=[{"title": article.title, "category": article.category} for article in articles],
    )
    _chroma_fp = fp
    _chroma_collection = collection
    return collection


def _answer_with_chroma(
    question: str,
    article_list: Sequence[KBArticle],
    top_k: int,
    min_score: float,
) -> KBAskResponse:
    by_id = {article.id: article for article in article_list}
    collection = _ensure_chroma_collection(article_list)
    model = _get_embed_model()
    query_embedding = model.encode([question], normalize_embeddings=True).tolist()
    n_results = min(max(top_k, 1), len(article_list) or 1)
    raw = collection.query(query_embeddings=query_embedding, n_results=n_results)
    ids = (raw.get("ids") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]

    ranked: List[Tuple[float, KBArticle]] = []
    for doc_id, distance in zip(ids, distances):
        article = by_id.get(doc_id)
        if article is None:
            continue
        # Chroma cosine space: distance ~= 1 - cosine similarity
        similarity = 1.0 - float(distance)
        ranked.append((similarity, article))
    ranked.sort(key=lambda item: item[0], reverse=True)
    hits = _hits_from_ranked(ranked, top_k, min_score)
    return _finalize_response(
        question,
        hits,
        retrieval_method="chromadb_minilm_cosine",
        vector_database="chromadb",
        disclaimer=_SEMANTIC_DISCLAIMER,
    )


def answer_question(
    question: str,
    articles: Iterable[KBArticle],
    top_k: int = 3,
    min_score: Optional[float] = None,
) -> KBAskResponse:
    article_list = list(articles)
    if not article_list:
        return _finalize_response(
            question,
            [],
            retrieval_method="none",
            vector_database="none",
            disclaimer=_TFIDF_DISCLAIMER,
        )

    try:
        semantic_min = 0.28 if min_score is None else min_score
        return _answer_with_chroma(question, article_list, top_k, semantic_min)
    except Exception:
        tfidf_min = 0.08 if min_score is None else min_score
        return _answer_with_tfidf(question, article_list, top_k, tfidf_min)


def answer_question_from_dicts(question: str, raw_articles: Sequence[Dict[str, Any]]) -> KBAskResponse:
    articles = [KBArticle(**item) for item in raw_articles]
    return answer_question(question, articles)
