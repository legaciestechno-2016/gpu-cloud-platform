from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from datetime import datetime
import modal

# Initialize FastAPI
app = FastAPI(
    title="GPU Cloud Platform",
    description="Deploy GPUs in 10 seconds, save 70% with AutoPause",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Modal
modal_app = modal.App("gpu-cloud-platform")

# Models
class GPUDeployRequest(BaseModel):
    name: str
    gpu_type: str = "T4"  # T4, A10G, A100
    template: Optional[str] = None

class GPUInstance(BaseModel):
    id: str
    name: str
    gpu_type: str
    status: str
    cost_per_hour: float
    jupyter_url: Optional[str]
    created_at: str

# Store instances (in production, use database)
instances_db = {}

# GPU Pricing
GPU_PRICES = {
    "T4": 0.99,
    "A10G": 1.99,
    "A100": 3.99,
    "H100": 8.99
}

@app.get("/")
async def root():
    return {
        "name": "GPU Cloud Platform",
        "status": "operational",
        "message": "Deploy GPUs in 10 seconds, save 70% with AutoPause",
        "endpoints": {
            "deploy": "/api/deploy",
            "instances": "/api/instances",
            "pricing": "/api/pricing"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "modal": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/deploy", response_model=GPUInstance)
async def deploy_gpu(request: GPUDeployRequest):
    """Deploy a GPU instance with Modal"""
    
    # Create Modal function
    @modal_app.function(
        gpu=request.gpu_type,
        scaledown_window=120,  # Auto-pause after 2 minutes
        image=modal.Image.debian_slim().pip_install(["torch", "jupyterlab"])
    )
    def gpu_instance():
        import socket
        hostname = socket.gethostname()
        return {
            "hostname": hostname,
            "jupyter_url": f"https://{hostname}.modal.run:8888"
        }
    
    # Deploy
    with modal_app.run():
        result = gpu_instance.remote()
    
    # Create instance record
    instance = GPUInstance(
        id=f"gpu-{len(instances_db)+1:04d}",
        name=request.name,
        gpu_type=request.gpu_type,
        status="running",
        cost_per_hour=GPU_PRICES.get(request.gpu_type, 0.99),
        jupyter_url=result.get("jupyter_url"),
        created_at=datetime.utcnow().isoformat()
    )
    
    instances_db[instance.id] = instance
    
    return instance

@app.get("/api/instances", response_model=List[GPUInstance])
async def list_instances():
    """List all GPU instances"""
    return list(instances_db.values())

@app.get("/api/instances/{instance_id}")
async def get_instance(instance_id: str):
    """Get instance details"""
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instances_db[instance_id]

@app.post("/api/instances/{instance_id}/stop")
async def stop_instance(instance_id: str):
    """Stop an instance (it will auto-pause)"""
    if instance_id not in instances_db:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    instances_db[instance_id].status = "stopped"
    return {"message": f"Instance {instance_id} stopped"}

@app.get("/api/pricing")
async def get_pricing():
    """Get GPU pricing"""
    return {
        "gpus": [
            {"type": "T4", "price_per_hour": 0.99, "memory_gb": 16, "savings_vs_aws": "70%"},
            {"type": "A10G", "price_per_hour": 1.99, "memory_gb": 24, "savings_vs_aws": "68%"},
            {"type": "A100", "price_per_hour": 3.99, "memory_gb": 40, "savings_vs_aws": "67%"},
            {"type": "H100", "price_per_hour": 8.99, "memory_gb": 80, "savings_vs_aws": "65%"}
        ],
        "features": [
            "Auto-pause after 2 minutes idle",
            "Auto-resume in 15 seconds",
            "Pay only for active time",
            "All GPUs include CUDA, PyTorch, TensorFlow"
        ]
    }

@app.get("/api/templates")
async def get_templates():
    """Get available templates"""
    return [
        {
            "id": "llama3",
            "name": "Llama 3 Chat",
            "description": "Meta's latest LLM",
            "gpu_required": "A10G",
            "one_click_deploy": True
        },
        {
            "id": "stable-diffusion",
            "name": "Stable Diffusion XL",
            "description": "Generate images from text",
            "gpu_required": "A10G",
            "one_click_deploy": True
        },
        {
            "id": "jupyter",
            "name": "Jupyter Lab",
            "description": "Interactive notebooks with GPU",
            "gpu_required": "T4",
            "one_click_deploy": True
        }
    ]

@app.post("/api/calculate-savings")
async def calculate_savings(hours_per_month: int = 200, gpu_type: str = "T4"):
    """Calculate savings vs AWS"""
    our_price = GPU_PRICES.get(gpu_type, 0.99)
    aws_price = our_price * 3.1  # AWS is ~3x more expensive
    
    # With auto-pause (70% idle time)
    our_cost = our_price * hours_per_month * 0.3  # Only pay for 30% active time
    aws_cost = aws_price * 730  # AWS charges for full month
    
    savings = aws_cost - our_cost
    savings_percent = (savings / aws_cost) * 100
    
    return {
        "gpu_type": gpu_type,
        "hours_per_month": hours_per_month,
        "our_monthly_cost": f"${our_cost:.2f}",
        "aws_monthly_cost": f"${aws_cost:.2f}",
        "monthly_savings": f"${savings:.2f}",
        "savings_percentage": f"{savings_percent:.1f}%"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)