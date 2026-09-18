import os
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Determine embedding column type based on DB engine
db_url = os.getenv("DATABASE_URL", "sqlite:///./hyderabad_agent.db")
is_sqlite = db_url.startswith("sqlite")

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

if is_sqlite or Vector is None:
    EmbeddingType = Text  # Fallback: store stringified JSON list
else:
    EmbeddingType = Vector(1536)


class Ward(Base):
    __tablename__ = "wards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ghmc_code = Column(String, unique=True, nullable=True)
    description = Column(Text, nullable=True)
    locality = Column(String, nullable=True)
    complaints = relationship("Complaint", back_populates="ward")

class LocalityMetrics(Base):
    __tablename__ = "locality_metrics"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    congestion_index = Column(Float, nullable=False)
    pm25 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    noise_db = Column(Float, nullable=True)
    energy_demand_mw = Column(Float, nullable=True)
    source = Column(String, nullable=True)

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    citizen_email = Column(String, nullable=False)
    citizen_name = Column(String, nullable=True)
    locality = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, nullable=False)
    embedding = Column(EmbeddingType, nullable=True)
    ward = relationship("Ward", back_populates="complaints")

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    embedding = Column(EmbeddingType, nullable=True)
    created_at = Column(DateTime, nullable=False)

