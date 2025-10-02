from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from ..utils.database import get_db
from ..utils.auth import get_current_active_user
from ..models.user import User
from ..models.template import Template
from ..schemas.instance import InstanceCreate
import json

router = APIRouter()

# Pre-defined templates for MVP
DEFAULT_TEMPLATES = [
    {
        "id": "llama3-chat",
        "name": "Llama 3 Chat",
        "description": "Meta's Llama 3 8B Chat model with web interface",
        "category": "llm",
        "docker_image": "huggingface/text-generation-inference:latest",
        "gpu_required": "A10G",
        "min_memory_gb": 24,
        "exposed_ports": [8080],
        "environment_vars": {
            "MODEL_ID": "meta-llama/Meta-Llama-3-8B-Instruct",
            "MAX_BATCH_TOKENS": "4096",
            "MAX_TOTAL_TOKENS": "8192"
        },
        "is_featured": True,
        "estimated_cost_per_hour": 1.99
    },
    {
        "id": "stable-diffusion-xl",
        "name": "Stable Diffusion XL",
        "description": "Latest SDXL model for high-quality image generation",
        "category": "image-gen",
        "docker_image": "runpod/stable-diffusion:web-ui-10.2.1",
        "gpu_required": "A10G",
        "min_memory_gb": 16,
        "exposed_ports": [7860],
        "environment_vars": {
            "WEBUI_ARGS": "--xformers --api"
        },
        "is_featured": True,
        "estimated_cost_per_hour": 1.99
    },
    {
        "id": "jupyter-lab",
        "name": "Jupyter Lab + PyTorch",
        "description": "Full ML development environment with GPU support",
        "category": "jupyter",
        "docker_image": "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        "gpu_required": "T4",
        "min_memory_gb": 16,
        "exposed_ports": [8888],
        "environment_vars": {
            "JUPYTER_TOKEN": "gpu-cloud-2025"
        },
        "startup_script": "pip install jupyterlab && jupyter lab --ip=0.0.0.0 --allow-root",
        "is_featured": True,
        "estimated_cost_per_hour": 0.99
    },
    {
        "id": "comfyui",
        "name": "ComfyUI",
        "description": "Node-based Stable Diffusion workflow tool",
        "category": "image-gen",
        "docker_image": "yanwk/comfyui-boot:latest",
        "gpu_required": "A10G",
        "min_memory_gb": 16,
        "exposed_ports": [8188],
        "environment_vars": {},
        "is_featured": False,
        "estimated_cost_per_hour": 1.99
    },
    {
        "id": "whisper-large",
        "name": "Whisper Large v3",
        "description": "OpenAI's speech recognition model",
        "category": "ml-training",
        "docker_image": "onerahmet/openai-whisper-asr-webservice:latest",
        "gpu_required": "T4",
        "min_memory_gb": 16,
        "exposed_ports": [9000],
        "environment_vars": {
            "ASR_MODEL": "large-v3"
        },
        "is_featured": False,
        "estimated_cost_per_hour": 0.99
    }
]

@router.get("/", response_model=List[dict])
async def list_templates(
    featured_only: bool = False,
    category: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """List available templates"""
    
    # For MVP, return pre-defined templates
    templates = DEFAULT_TEMPLATES
    
    if featured_only:
        templates = [t for t in templates if t.get("is_featured")]
    
    if category:
        templates = [t for t in templates if t.get("category") == category]
    
    # Track deploy count from database
    for template in templates:
        db_template = db.query(Template).filter(Template.id == template["id"]).first()
        if db_template:
            template["deploy_count"] = db_template.deploy_count
        else:
            template["deploy_count"] = 0
    
    return templates

@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get template details"""
    
    template = next((t for t in DEFAULT_TEMPLATES if t["id"] == template_id), None)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return template

@router.post("/{template_id}/deploy")
async def deploy_template(
    template_id: str,
    instance_name: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Deploy a template with one click"""
    
    template = next((t for t in DEFAULT_TEMPLATES if t["id"] == template_id), None)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Create or update template in database
    db_template = db.query(Template).filter(Template.id == template_id).first()
    if not db_template:
        db_template = Template(
            id=template_id,
            name=template["name"],
            description=template["description"],
            category=template["category"],
            docker_image=template["docker_image"],
            gpu_required=template["gpu_required"],
            min_memory_gb=template["min_memory_gb"],
            exposed_ports=template["exposed_ports"],
            environment_vars=template["environment_vars"],
            estimated_cost_per_hour=template["estimated_cost_per_hour"]
        )
        db.add(db_template)
    
    db_template.deploy_count += 1
    db.commit()
    
    # Create instance from template
    from .instances import deploy_instance
    
    instance_data = InstanceCreate(
        name=instance_name or f"{template['name']}-{current_user.id}",
        gpu_type=template["gpu_required"],
        template_id=template_id,
        docker_image=template["docker_image"],
        environment_vars=template.get("environment_vars", {}),
        use_spot=True,
        auto_pause_enabled=True
    )
    
    # Deploy the instance
    return await deploy_instance(
        instance_data=instance_data,
        background_tasks=None,
        current_user=current_user,
        db=db
    )

@router.post("/import-huggingface")
async def import_huggingface_model(
    model_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Import a model from HuggingFace and create a template"""
    
    # Parse model requirements
    # For MVP, we'll use simple heuristics
    if "llama" in model_id.lower() or "mistral" in model_id.lower():
        gpu_required = "A10G"
        docker_image = "huggingface/text-generation-inference:latest"
        category = "llm"
    elif "stable-diffusion" in model_id.lower():
        gpu_required = "A10G"
        docker_image = "runpod/stable-diffusion:web-ui"
        category = "image-gen"
    else:
        gpu_required = "T4"
        docker_image = "pytorch/pytorch:latest"
        category = "ml-training"
    
    template = {
        "id": f"hf-{model_id.replace('/', '-')}",
        "name": f"HuggingFace: {model_id}",
        "description": f"Auto-imported from HuggingFace: {model_id}",
        "category": category,
        "docker_image": docker_image,
        "gpu_required": gpu_required,
        "min_memory_gb": 16,
        "exposed_ports": [8080],
        "environment_vars": {
            "MODEL_ID": model_id
        },
        "estimated_cost_per_hour": 1.99 if gpu_required == "A10G" else 0.99
    }
    
    return {
        "template": template,
        "message": "Template created from HuggingFace model",
        "deploy_url": f"/api/templates/{template['id']}/deploy"
    }

@router.get("/categories")
async def get_template_categories(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get available template categories"""
    return [
        {"id": "llm", "name": "Language Models", "icon": "🤖"},
        {"id": "image-gen", "name": "Image Generation", "icon": "🎨"},
        {"id": "jupyter", "name": "Jupyter Notebooks", "icon": "📓"},
        {"id": "ml-training", "name": "ML Training", "icon": "🧠"}
    ]