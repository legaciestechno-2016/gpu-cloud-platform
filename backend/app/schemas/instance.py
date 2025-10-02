from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class InstanceCreate(BaseModel):
    name: Optional[str] = None
    gpu_type: str  # T4, A10G, A100
    template_id: Optional[str] = None
    use_spot: bool = True
    auto_pause_enabled: bool = True
    docker_image: Optional[str] = None
    environment_vars: Optional[Dict[str, str]] = None

class InstanceUpdate(BaseModel):
    name: Optional[str] = None
    auto_pause_enabled: Optional[bool] = None
    environment_vars: Optional[Dict[str, str]] = None

class InstanceResponse(BaseModel):
    id: str
    user_id: int
    name: str
    gpu_type: str
    status: str
    public_ip: Optional[str]
    ssh_port: int
    jupyter_url: Optional[str]
    api_endpoint: Optional[str]
    cost_per_hour: float
    total_cost: float
    savings_from_autopause: float
    is_spot_instance: bool
    auto_pause_enabled: bool
    gpu_utilization: float
    created_at: datetime
    started_at: Optional[datetime]
    paused_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class InstanceMetrics(BaseModel):
    gpu_utilization: float
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    cpu_utilization: float
    memory_used_gb: float
    memory_total_gb: float
    network_in_mbps: float
    network_out_mbps: float
    temperature_celsius: float

class InstanceAction(BaseModel):
    action: str  # start, stop, pause, resume, delete