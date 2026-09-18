from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.db.db import SessionLocal
from src.agent.core_agent import generate_recommendation

router = APIRouter()

class AgentRequest(BaseModel):
    ward_id: int
    prompt: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 3
    category: str = None
    ward_id: int = None

@router.get("/health")
def agent_health():
    return {"status": "agent route online"}

@router.post("/recommendation")
def agent_recommendation(request: AgentRequest):
    db = SessionLocal()
    try:
        recommendation = generate_recommendation(request.ward_id, request.prompt, db)
        return {"response": recommendation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/search")
def agent_search(request: SearchRequest):
    db = SessionLocal()
    try:
        from src.rag.retriever import retrieve_context
        results = retrieve_context(request.query, db, limit=request.limit, category=request.category, ward_id=request.ward_id)
        
        serialized_docs = []
        for doc in results.get("documents", []):
            serialized_docs.append({
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "category": doc.category,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            })
            
        serialized_complaints = []
        for comp in results.get("complaints", []):
            serialized_complaints.append({
                "id": comp.id,
                "citizen_name": comp.citizen_name or "Anonymous",
                "locality": comp.locality,
                "description": comp.description,
                "category": comp.category,
                "severity": comp.severity,
                "ward_id": comp.ward_id,
                "status": comp.status,
                "created_at": comp.created_at.isoformat() if comp.created_at else None
            })
            
        return {
            "documents": serialized_docs,
            "complaints": serialized_complaints
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

