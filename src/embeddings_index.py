# src/embeddings_index.py
from typing import List, Dict
from sentence_transformers import SentenceTransformer, CrossEncoder
from .config import pinecone_index
import uuid

# load models once
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

CHUNK_SIZE = 600
CHUNK_OVERLAP = 150

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(words):
            break
    return chunks

def index_resume_text(resume_text: str, user_id: str = "user1"):
    """Index resume into Pinecone for this user. Overwrites old entries (simple approach)."""
    chunks = chunk_text(resume_text)
    if not chunks:
        return

    vectors = []
    embeddings = embed_model.encode(chunks, convert_to_numpy=True)

    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        vec_id = f"{user_id}-{uuid.uuid4().hex}"
        vectors.append({
            "id": vec_id,
            "values": emb.tolist(),
            "metadata": {
                "user_id": user_id,
                "text": chunk
            }
        })

    # Optional: delete old vectors for this user first
    # pinecone_index.delete(filter={"user_id": {"$eq": user_id}})

    pinecone_index.upsert(vectors)

def retrieve_relevant_snippets(jd_text: str, user_id: str = "user1", top_k: int = 8) -> List[Dict]:
    """Retrieve + rerank resume chunks relevant to this JD."""
    jd_emb = embed_model.encode([jd_text])[0].tolist()

    # query Pinecone
    res = pinecone_index.query(
        vector=jd_emb,
        top_k=20,
        include_metadata=True,
        filter={"user_id": {"$eq": user_id}}
    )
    matches = res.get("matches", [])

    if not matches:
        return []

    # rerank with cross-encoder
    pairs = [(jd_text, m["metadata"]["text"]) for m in matches]
    scores = rerank_model.predict(pairs)

    scored = list(zip(matches, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]

    # return list of dicts: {text, score}
    return [{"text": m["metadata"]["text"], "score": float(s)} for m, s in top]