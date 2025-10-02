from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..utils.database import Base

class Instance(Base):
    __tablename__ = "instances"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    gpu_type = Column(String, nullable=False)  # T4, A10G, A100
    status = Column(String, default="provisioning")  # provisioning, running, paused, stopped, error
    
    azure_resource_id = Column(String, nullable=True)
    public_ip = Column(String, nullable=True)
    ssh_port = Column(Integer, default=22)
    jupyter_url = Column(String, nullable=True)
    api_endpoint = Column(String, nullable=True)
    
    cost_per_hour = Column(Float, nullable=False)
    total_cost = Column(Float, default=0.0)
    savings_from_autopause = Column(Float, default=0.0)
    
    is_spot_instance = Column(Boolean, default=True)
    auto_pause_enabled = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    gpu_utilization = Column(Float, default=0.0)
    
    template_id = Column(String, ForeignKey("templates.id"), nullable=True)
    environment_vars = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="instances")
    template = relationship("Template", back_populates="instances")
    usage_records = relationship("UsageRecord", back_populates="instance")
    
class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instance_id = Column(String, ForeignKey("instances.id"), nullable=False)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0)
    
    cost = Column(Float, default=0.0)
    was_paused = Column(Boolean, default=False)
    gpu_utilization_avg = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="usage_records")
    instance = relationship("Instance", back_populates="usage_records")