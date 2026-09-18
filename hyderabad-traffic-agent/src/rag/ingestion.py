import os
import json
import hashlib
from datetime import datetime, timezone
from openai import OpenAI
from src.db.models import KnowledgeDocument


def get_embedding(text: str) -> list[float]:
    """
    Generates embedding for the text. If OPENAI_API_KEY is actual and valid,
    uses OpenAI Embedding API. Otherwise, falls back to deterministic mock embedding.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and api_key != "mock-key":
        try:
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[text]
            )
            return response.data[0].embedding
        except Exception:
            # Fallback to mock on API failure
            pass
            
    # Deterministic mock embedding (length 1536)
    key_terms = [
        "drainage", "waterlogging", "drain", "pipe", "water",
        "signal", "timing", "atsc", "traffic", "junction",
        "widening", "widen", "flyover", "bridge",
        "pm2.5", "aqi", "sprinkler", "dust", "pollution",
        "energy", "grid", "transformer", "streetlight", "power"
    ]
    
    text_lower = text.lower()
    dimension = 1536
    vec = [0.0] * dimension
    
    # Overlay term frequencies in the first dimensions
    for idx, term in enumerate(key_terms):
        if term in text_lower:
            vec[idx] = 10.0
            
    text_bytes = text.encode('utf-8')
    for i in range(len(key_terms), dimension):
        h = hashlib.md5(text_bytes + str(i).encode('utf-8')).hexdigest()
        val = int(h[:8], 16) / 4294967295.0
        vec[i] = val
        
    mag = sum(x*x for x in vec) ** 0.5
    if mag == 0:
        return [0.0] * dimension
    return [x / mag for x in vec]



def ingest_text_document(title: str, content: str, category: str, db) -> KnowledgeDocument:
    """
    Ingests a knowledge text document into the DB with its embedding.
    """
    embedding_list = get_embedding(content)
    is_sqlite_db = str(db.bind.url).startswith("sqlite")
    
    doc = KnowledgeDocument(
        title=title,
        content=content,
        category=category,
        embedding=json.dumps(embedding_list) if is_sqlite_db else embedding_list,
        created_at=datetime.now(timezone.utc)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
