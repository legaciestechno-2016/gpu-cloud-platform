from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from ..utils.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    credits_remaining = Column(Float, default=50.0)
    total_savings = Column(Float, default=0.0)
    stripe_customer_id = Column(String, nullable=True)
    subscription_tier = Column(String, default="free")  # free, starter, business, enterprise
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instances = relationship("Instance", back_populates="user")
    usage_records = relationship("UsageRecord", back_populates="user")