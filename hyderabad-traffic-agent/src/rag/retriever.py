from src.rag.ingestion import get_embedding
from src.rag.vector_db import VectorDBWrapper


def retrieve_context(query: str, db, limit: int = 3, category: str = None, ward_id: int = None) -> dict:
    """
    Retrieves relevant knowledge documents and matching complaints.
    Returns a dict containing lists of matched documents and complaints.
    """
    query_emb = get_embedding(query)
    
    matched_docs = VectorDBWrapper.similarity_search_documents(db, query_emb, limit=limit, category=category)
    matched_complaints = VectorDBWrapper.similarity_search_complaints(db, query_emb, limit=limit, ward_id=ward_id)
    
    return {
        "documents": matched_docs,
        "complaints": matched_complaints
    }


def format_context_for_prompt(retrieved: dict) -> str:
    """
    Formats the retrieved dictionary into a clean string context for LLM consumption.
    """
    context_parts = []
    
    if retrieved.get("documents"):
        context_parts.append("### Relevant Infrastructure Guidelines & Standards:")
        for doc in retrieved["documents"]:
            context_parts.append(f"- **{doc.title}** ({doc.category}): {doc.content}")
            
    if retrieved.get("complaints"):
        context_parts.append("\n### Similar Citizen Complaints in Hyderabad:")
        for comp in retrieved["complaints"]:
            status_str = f"Status: {comp.status}" if comp.status else ""
            locality_str = f"Locality: {comp.locality}" if comp.locality else ""
            context_parts.append(f"- [{comp.category.upper()} - {comp.severity.upper()}] {comp.description} ({locality_str} | {status_str})")
            
    return "\n".join(context_parts)
