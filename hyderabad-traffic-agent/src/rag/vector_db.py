import json
import numpy as np
from src.db.models import Complaint, KnowledgeDocument


class VectorDBWrapper:
    @staticmethod
    def is_sqlite(db) -> bool:
        return str(db.bind.url).startswith("sqlite")

    @classmethod
    def similarity_search_documents(cls, db, query_embedding: list[float], limit: int = 3, category: str = None):
        """
        Performs similarity search on KnowledgeDocument table.
        Falls back to NumPy-based cosine similarity on SQLite.
        """
        if cls.is_sqlite(db):
            query = db.query(KnowledgeDocument)
            if category:
                query = query.filter(KnowledgeDocument.category == category)
            docs = query.all()
            if not docs:
                return []
            
            q_vec = np.array(query_embedding, dtype=np.float32)
            # Normalize query vector if it isn't
            q_norm = np.linalg.norm(q_vec)
            if q_norm > 0:
                q_vec = q_vec / q_norm

            results = []
            for doc in docs:
                if not doc.embedding:
                    continue
                try:
                    doc_vec = np.array(json.loads(doc.embedding), dtype=np.float32)
                    doc_norm = np.linalg.norm(doc_vec)
                    if doc_norm > 0:
                        doc_vec = doc_vec / doc_norm
                    sim = float(np.dot(q_vec, doc_vec))
                    results.append((doc, sim))
                except Exception:
                    continue
            
            results.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, sim in results[:limit]]
        else:
            query = db.query(KnowledgeDocument)
            if category:
                query = query.filter(KnowledgeDocument.category == category)
            query = query.order_by(KnowledgeDocument.embedding.cosine_distance(query_embedding))
            return query.limit(limit).all()

    @classmethod
    def similarity_search_complaints(cls, db, query_embedding: list[float], limit: int = 3, ward_id: int = None):
        """
        Performs similarity search on Complaint table.
        Falls back to NumPy-based cosine similarity on SQLite.
        """
        if cls.is_sqlite(db):
            query = db.query(Complaint)
            if ward_id is not None:
                query = query.filter(Complaint.ward_id == ward_id)
            complaints = query.all()
            if not complaints:
                return []
            
            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm > 0:
                q_vec = q_vec / q_norm

            results = []
            for c in complaints:
                if not c.embedding:
                    continue
                try:
                    c_vec = np.array(json.loads(c.embedding), dtype=np.float32)
                    c_norm = np.linalg.norm(c_vec)
                    if c_norm > 0:
                        c_vec = c_vec / c_norm
                    sim = float(np.dot(q_vec, c_vec))
                    results.append((c, sim))
                except Exception:
                    continue
            
            results.sort(key=lambda x: x[1], reverse=True)
            return [c for c, sim in results[:limit]]
        else:
            query = db.query(Complaint)
            if ward_id is not None:
                query = query.filter(Complaint.ward_id == ward_id)
            query = query.order_by(Complaint.embedding.cosine_distance(query_embedding))
            return query.limit(limit).all()
