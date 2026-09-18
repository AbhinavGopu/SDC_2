import os
from sqlalchemy import create_engine, Column, String, Integer, Float, JSON, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

URL = os.getenv("DATABASE_URL", "sqlite:///./smartcity.db")
engine = create_engine(URL, **({"connect_args": {"check_same_thread": False}} if URL.startswith("sqlite") else {"pool_pre_ping": True}))
Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    ward_id = Column(Integer)

class Ward(Base):
    __tablename__ = "wards"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    geometry = Column(JSON, nullable=False)
    provenance = Column(String, nullable=False)

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=False, index=True)
    ward_id = Column(Integer, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    authority = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, default="received", nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(String, nullable=False)
    media = Column(JSON, default=list)
    analysis = Column(JSON, default=dict)

class Observation(Base):
    __tablename__ = "observations"
    id = Column(String, primary_key=True)
    ward_id = Column(Integer, nullable=False, index=True)
    domain = Column(String, nullable=False)
    metric = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    observed_at = Column(String, nullable=False)
    provenance = Column(String, nullable=False)
    source = Column(String, nullable=False)
    license = Column(String, nullable=False)

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    domain = Column(String, nullable=False)
    source = Column(String, nullable=False)
    provenance = Column(String, nullable=False)

class Plan(Base):
    __tablename__ = "plans"
    id = Column(String, primary_key=True)
    ward_id = Column(Integer, nullable=False)
    owner_id = Column(String, nullable=False)
    result = Column(JSON, nullable=False)
    status = Column(String, default="proposed")
    created_at = Column(String, nullable=False)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=False)
    ward_id = Column(Integer, nullable=False)
    status = Column(String, default="queued")
    request = Column(JSON, nullable=False)
    result = Column(JSON)
    error = Column(String)
    created_at = Column(String, nullable=False)

class Audit(Base):
    __tablename__ = "audit"
    id = Column(String, primary_key=True)
    actor_id = Column(String, nullable=False)
    ward_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    created_at = Column(String, nullable=False)

def get_db():
    with Session() as db:
        yield db
