from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Ward(Base):
    __tablename__ = "wards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ghmc_code = Column(String, unique=True, nullable=True)
    description = Column(Text, nullable=True)
    locality = Column(String, nullable=True)

class Citizen(Base):
    __tablename__ = "citizens"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    ward_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

class Planner(Base):
    __tablename__ = "planners"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    ward_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
