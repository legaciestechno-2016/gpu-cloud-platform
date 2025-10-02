from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..utils.database import Base

class Template(Base):
    __tablename__ = "templates"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)  # llm, image-gen, ml-training, jupyter
    
    docker_image = Column(String, nullable=False)
    gpu_required = Column(String, nullable=False)  # T4, A10G, A100
    min_memory_gb = Column(Integer, default=16)
    
    exposed_ports = Column(JSON, default=[])
    environment_vars = Column(JSON, default={})
    startup_script = Column(String, nullable=True)
    
    is_featured = Column(Boolean, default=False)
    deploy_count = Column(Integer, default=0)
    avg_deploy_time_seconds = Column(Float, default=45.0)
    
    huggingface_model_id = Column(String, nullable=True)
    estimated_cost_per_hour = Column(Float, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instances = relationship("Instance", back_populates="template")