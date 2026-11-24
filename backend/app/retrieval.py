"""Search approved, category-matched SQL records. SQL remains the source of truth."""

import logging
import os
import re
from functools import lru_cache
from threading import Lock

from sqlalchemy import select
from .db import Article, DemoRoster
from .repairs import ARTICLE_ID, matches

lock = Lock()


@lru_cache(maxsize=1)
def vector_resources(model_path):
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_path, local_files_only=True)
    collection = chromadb.EphemeralClient(
        settings=Settings(anonymized_telemetry=False)
    ).get_or_create_collection("rideops_guides", metadata={"hnsw:space": "cosine"})
    return model, collection


def ranked_articles(db, ticket):
    articles = [
        a
        for a in db.scalars(
            select(Article).where(
                Article.approved.is_(True), Article.category == ticket["category"]
            )
        )
        if a.id != ARTICLE_ID
        or (matches(ticket) and db.get(DemoRoster, ticket["ticket_id"]))
    ]
    if not articles:
        return []
    description = ticket["description"].lower()
    model_path = os.getenv("RIDEOPS_EMBEDDING_MODEL")
    if model_path:
        try:
            with lock:
                model, collection = vector_resources(model_path)
                ids = [str(a.id) for a in articles]
                texts = [a.title + " " + a.issue for a in articles]
                vectors = model.encode([description, *texts], normalize_embeddings=True)
                collection.upsert(
                    ids=ids,
                    embeddings=vectors[1:].tolist(),
                    metadatas=[{"guide": i} for i in ids],
                )
                result = collection.query(
                    query_embeddings=[vectors[0].tolist()],
                    where={"guide": {"$in": ids}},
                    n_results=min(4, len(ids)),
                )
                by_id = {str(a.id): a for a in articles}
                return [
                    by_id[i]
                    for i, d in zip(result["ids"][0], result["distances"][0])
                    if d <= 0.45
                ]
        except Exception:
            logging.getLogger(__name__).warning(
                "Semantic search unavailable. Using keyword retrieval."
            )

    def terms(text):
        return set(re.findall(r"[a-z0-9]+", text.lower())) - {
            "the",
            "and",
            "for",
            "but",
            "not",
            "with",
            "still",
        }

    query = terms(description)

    def score(a):
        words = terms(a.issue + " " + a.title)
        return len(words & query) / max(1, len(words | query))

    return [a for a in sorted(articles, key=score, reverse=True) if score(a) >= 0.22][
        :4
    ]
