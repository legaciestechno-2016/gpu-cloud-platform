"""
Modal GPU Manager - True serverless GPU with auto-pause
"""
import modal
import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# Modal configuration
stub = modal.Stub("gpu-cloud-platform")

# GPU configurations matching your pricing
GPU_CONFIGS = {
    "T4": modal.gpu.T4(),
    "A10G": modal.gpu.A10G(),
    "A100": modal.gpu.A100(),
    "L4": modal.gpu.L4(),
    "H100": modal.gpu.H100(),
}

class ModalGPUManager:
    """Manages GPU instances on Modal with true auto-pause"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MODAL_API_KEY")
        if self.api_key:
            os.environ["MODAL_TOKEN_ID"] = self.api_key.split(":")[0]
            os.environ["MODAL_TOKEN_SECRET"] = self.api_key.split(":")[1] if ":" in self.api_key else ""
        
        self.active_functions = {}
        
    async def create_gpu_function(
        self,
        name: str,
        gpu_type: str,
        docker_image: str = None,
        memory: int = 32768,  # 32GB default
        cpu: float = 8.0,
        startup_script: str = None
    ) -> Dict[str, Any]:
        """Create a Modal function with GPU that auto-pauses when idle"""
        
        if gpu_type not in GPU_CONFIGS:
            raise ValueError(f"Invalid GPU type: {gpu_type}. Choose from {list(GPU_CONFIGS.keys())}")
        
        # Create Modal image with dependencies
        if docker_image:
            image = modal.Image.from_dockerfile(docker_image)
        else:
            # Default GPU-ready image
            image = (
                modal.Image.debian_slim()
                .pip_install([
                    "torch",
                    "transformers",
                    "diffusers",
                    "accelerate",
                    "jupyterlab",
                    "fastapi",
                    "uvicorn"
                ])
                .run_commands("apt-get update && apt-get install -y git wget")
            )
        
        # Define the GPU function with auto-scaling
        @stub.function(
            name=name,
            image=image,
            gpu=GPU_CONFIGS[gpu_type],
            memory=memory,
            cpu=cpu,
            concurrency_limit=1,
            container_idle_timeout=120,  # Auto-pause after 2 minutes idle
            timeout=3600,  # 1 hour max runtime
        )
        async def gpu_instance(command: str = None):
            """GPU instance that runs commands or starts services"""
            import subprocess
            import socket
            
            # Get instance metadata
            hostname = socket.gethostname()
            
            # Run startup script if provided
            if command:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return {
                    "hostname": hostname,
                    "output": result.stdout,
                    "error": result.stderr,
                    "return_code": result.returncode
                }
            
            # Default: Start Jupyter Lab
            subprocess.Popen([
                "jupyter", "lab",
                "--ip=0.0.0.0",
                "--port=8888",
                "--no-browser",
                "--allow-root",
                "--NotebookApp.token=''",
                "--NotebookApp.password=''"
            ])
            
            return {
                "hostname": hostname,
                "jupyter_url": f"https://{hostname}.modal.run:8888",
                "status": "running"
            }
        
        # Deploy the function
        with stub.run():
            # Get function handle
            function_handle = gpu_instance
            
            # Store in active functions
            self.active_functions[name] = {
                "function": function_handle,
                "gpu_type": gpu_type,
                "created_at": datetime.utcnow(),
                "status": "running"
            }
            
            # Get the function URL
            function_url = f"https://{name}--{self.get_workspace()}.modal.run"
            
            return {
                "id": name,
                "name": name,
                "gpu_type": gpu_type,
                "status": "running",
                "url": function_url,
                "jupyter_url": f"{function_url}:8888",
                "api_endpoint": f"{function_url}/api",
                "created_at": datetime.utcnow().isoformat(),
                "auto_pause_enabled": True,
                "idle_timeout": 120
            }
    
    async def invoke_function(self, name: str, command: str = None) -> Dict[str, Any]:
        """Invoke a Modal function (auto-resumes if paused)"""
        
        if name not in self.active_functions:
            raise ValueError(f"Function {name} not found")
        
        function = self.active_functions[name]["function"]
        
        # Modal automatically resumes paused functions
        result = await function.remote.aio(command=command)
        
        return result
    
    async def stop_function(self, name: str) -> bool:
        """Stop a Modal function (it will auto-pause)"""
        
        if name not in self.active_functions:
            return False
        
        # Modal functions auto-pause, we just mark as stopped
        self.active_functions[name]["status"] = "paused"
        
        return True
    
    async def delete_function(self, name: str) -> bool:
        """Delete a Modal function"""
        
        if name not in self.active_functions:
            return False
        
        # Remove from tracking
        del self.active_functions[name]
        
        # Modal functions are ephemeral, they clean up automatically
        return True
    
    async def get_function_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a Modal function"""
        
        if name not in self.active_functions:
            return None
        
        function_info = self.active_functions[name]
        
        # Check if function is idle (Modal tracks this)
        # In production, use Modal API to get actual status
        
        return {
            "name": name,
            "gpu_type": function_info["gpu_type"],
            "status": function_info["status"],
            "created_at": function_info["created_at"],
            "is_idle": function_info["status"] == "paused"
        }
    
    def get_gpu_pricing(self, gpu_type: str) -> float:
        """Get Modal GPU pricing per hour"""
        
        # Modal pricing (approximate)
        pricing = {
            "T4": 0.59,      # $0.59/hour
            "L4": 0.89,      # $0.89/hour  
            "A10G": 1.10,    # $1.10/hour
            "A100": 3.09,    # $3.09/hour (40GB)
            "H100": 8.50     # $8.50/hour
        }
        
        return pricing.get(gpu_type, 0)
    
    def calculate_cost_savings(self, gpu_type: str, idle_hours: int) -> float:
        """Calculate savings from auto-pause"""
        
        hourly_cost = self.get_gpu_pricing(gpu_type)
        saved = hourly_cost * idle_hours
        
        return saved
    
    def get_workspace(self) -> str:
        """Get Modal workspace name"""
        return os.getenv("MODAL_WORKSPACE", "sathyat")
    
    async def create_template_deployment(self, template: str) -> Dict[str, Any]:
        """Deploy a pre-configured template"""
        
        templates = {
            "llama3-chat": {
                "gpu_type": "A10G",
                "image": "modal.Image.debian_slim().pip_install(['transformers', 'torch', 'fastapi'])",
                "startup": "python -m transformers.models.llama.modeling_llama"
            },
            "stable-diffusion": {
                "gpu_type": "A10G",
                "image": "modal.Image.from_registry('runpod/stable-diffusion:web-ui')",
                "startup": "python app.py"
            },
            "jupyter-lab": {
                "gpu_type": "T4",
                "image": "modal.Image.debian_slim().pip_install(['jupyterlab', 'torch', 'numpy'])",
                "startup": "jupyter lab --ip=0.0.0.0"
            }
        }
        
        if template not in templates:
            raise ValueError(f"Template {template} not found")
        
        config = templates[template]
        
        return await self.create_gpu_function(
            name=f"{template}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            gpu_type=config["gpu_type"],
            startup_script=config.get("startup")
        )


# Modal function for running GPU workloads
@stub.function(
    gpu=modal.gpu.A10G(),
    image=modal.Image.debian_slim().pip_install(["torch", "transformers"]),
    concurrency_limit=10,
    container_idle_timeout=120,  # Auto-pause after 2 minutes
)
def run_gpu_workload(task: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run any GPU workload with auto-pause"""
    
    import torch
    import time
    
    start_time = time.time()
    
    if task == "inference":
        # Run model inference
        from transformers import pipeline
        
        model = pipeline(params.get("model", "gpt2"))
        result = model(params.get("input", "Hello world"))
        
        return {
            "task": task,
            "result": result,
            "gpu_used": torch.cuda.get_device_name(0),
            "execution_time": time.time() - start_time
        }
    
    elif task == "training":
        # Run training job
        # Your training code here
        pass
    
    return {"status": "completed", "task": task}


# Scheduled function for batch jobs
@stub.function(
    schedule=modal.Period(hours=1),  # Run every hour
    gpu=modal.gpu.T4(),
)
def scheduled_batch_job():
    """Scheduled GPU job that runs periodically"""
    
    import torch
    
    # Your batch processing code
    print(f"Running batch job on {torch.cuda.get_device_name(0)}")
    
    # Process data
    # ...
    
    # Job automatically pauses when done
    return {"status": "completed"}