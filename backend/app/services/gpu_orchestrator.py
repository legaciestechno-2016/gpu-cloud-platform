"""
GPU Orchestrator - Routes to appropriate provider based on deployment type
"""
from typing import Dict, Any, Optional
from enum import Enum
import os
from .modal_gpu_manager import ModalGPUManager
from .azure_manager import AzureGPUManager
from ..utils.config import settings
import logging

logger = logging.getLogger(__name__)

class DeploymentType(Enum):
    SAAS = "saas"           # Our infrastructure (Modal + DO)
    BYOC = "byoc"           # Customer's cloud (AWS/Azure/GCP)
    ON_PREMISE = "on_premise"  # Customer's data center
    HYBRID = "hybrid"       # Mix of above

class GPUProvider(Enum):
    MODAL = "modal"
    AZURE = "azure"
    AWS = "aws"
    RUNPOD = "runpod"
    ON_PREMISE = "on_premise"

class GPUOrchestrator:
    """
    Universal orchestrator that works with any infrastructure
    This is the magic that makes your platform infrastructure-agnostic
    """
    
    def __init__(self):
        self.deployment_type = self._detect_deployment_type()
        self.providers = self._initialize_providers()
        
    def _detect_deployment_type(self) -> DeploymentType:
        """Detect deployment type from environment"""
        deployment = os.getenv("DEPLOYMENT_TYPE", "saas")
        return DeploymentType(deployment)
    
    def _initialize_providers(self) -> Dict[GPUProvider, Any]:
        """Initialize available providers based on deployment"""
        providers = {}
        
        # Always initialize Modal for SaaS
        if self.deployment_type == DeploymentType.SAAS:
            modal_key = os.getenv("MODAL_API_KEY")
            if modal_key:
                providers[GPUProvider.MODAL] = ModalGPUManager(modal_key)
                logger.info("Modal provider initialized")
        
        # Initialize Azure if configured (BYOC or Enterprise)
        if settings.AZURE_SUBSCRIPTION_ID:
            providers[GPUProvider.AZURE] = AzureGPUManager()
            logger.info("Azure provider initialized")
        
        # Add more providers as needed
        # providers[GPUProvider.AWS] = AWSManager()
        # providers[GPUProvider.RUNPOD] = RunPodManager()
        
        return providers
    
    async def deploy_gpu(
        self,
        name: str,
        gpu_type: str,
        user_id: int,
        template: Optional[str] = None,
        provider: Optional[GPUProvider] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Deploy GPU instance using appropriate provider
        """
        
        # Select provider based on deployment type
        if not provider:
            provider = self._select_best_provider(gpu_type, user_id)
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not available")
        
        manager = self.providers[provider]
        
        # Deploy based on provider type
        if provider == GPUProvider.MODAL:
            # Use Modal for serverless with auto-pause
            if template:
                instance = await manager.create_template_deployment(template)
            else:
                instance = await manager.create_gpu_function(
                    name=name,
                    gpu_type=gpu_type,
                    **kwargs
                )
            
            # Add provider metadata
            instance["provider"] = "modal"
            instance["deployment_type"] = self.deployment_type.value
            instance["auto_pause"] = True
            instance["cost_per_hour"] = manager.get_gpu_pricing(gpu_type)
            
        elif provider == GPUProvider.AZURE:
            # Use Azure for dedicated instances
            instance = await manager.create_instance(
                gpu_type=gpu_type,
                user_id=user_id,
                name=name,
                **kwargs
            )
            instance["provider"] = "azure"
            instance["deployment_type"] = self.deployment_type.value
        
        else:
            raise NotImplementedError(f"Provider {provider} not implemented")
        
        return instance
    
    def _select_best_provider(self, gpu_type: str, user_id: int) -> GPUProvider:
        """
        Intelligent provider selection based on multiple factors
        """
        
        # For SaaS deployment, prefer Modal for auto-pause
        if self.deployment_type == DeploymentType.SAAS:
            if GPUProvider.MODAL in self.providers:
                return GPUProvider.MODAL
        
        # For BYOC, use customer's cloud
        elif self.deployment_type == DeploymentType.BYOC:
            if GPUProvider.AZURE in self.providers:
                return GPUProvider.AZURE
            elif GPUProvider.AWS in self.providers:
                return GPUProvider.AWS
        
        # Default fallback
        if self.providers:
            return list(self.providers.keys())[0]
        
        raise ValueError("No GPU providers available")
    
    async def stop_instance(self, instance_id: str, provider: str) -> bool:
        """Stop/pause GPU instance"""
        
        provider_enum = GPUProvider(provider)
        if provider_enum not in self.providers:
            return False
        
        manager = self.providers[provider_enum]
        
        if provider_enum == GPUProvider.MODAL:
            return await manager.stop_function(instance_id)
        elif provider_enum == GPUProvider.AZURE:
            return await manager.stop_instance(instance_id)
        
        return False
    
    async def resume_instance(self, instance_id: str, provider: str) -> bool:
        """Resume paused GPU instance"""
        
        provider_enum = GPUProvider(provider)
        if provider_enum not in self.providers:
            return False
        
        manager = self.providers[provider_enum]
        
        if provider_enum == GPUProvider.MODAL:
            # Modal auto-resumes on next invocation
            return True
        elif provider_enum == GPUProvider.AZURE:
            return await manager.start_instance(instance_id)
        
        return False
    
    async def delete_instance(self, instance_id: str, provider: str) -> bool:
        """Delete GPU instance"""
        
        provider_enum = GPUProvider(provider)
        if provider_enum not in self.providers:
            return False
        
        manager = self.providers[provider_enum]
        
        if provider_enum == GPUProvider.MODAL:
            return await manager.delete_function(instance_id)
        elif provider_enum == GPUProvider.AZURE:
            return await manager.delete_instance(instance_id, {})
        
        return False
    
    async def get_instance_metrics(self, instance_id: str, provider: str) -> Dict[str, Any]:
        """Get instance metrics from provider"""
        
        provider_enum = GPUProvider(provider)
        if provider_enum not in self.providers:
            return {}
        
        manager = self.providers[provider_enum]
        
        if provider_enum == GPUProvider.MODAL:
            status = await manager.get_function_status(instance_id)
            return {
                "gpu_utilization": 0 if status.get("is_idle") else 85,  # Estimate
                "status": status.get("status", "unknown"),
                "provider": "modal"
            }
        elif provider_enum == GPUProvider.AZURE:
            return await manager.get_instance_metrics(instance_id)
        
        return {}
    
    def get_supported_gpus(self) -> Dict[str, Dict[str, float]]:
        """Get all supported GPU types and pricing across providers"""
        
        gpus = {}
        
        if GPUProvider.MODAL in self.providers:
            modal_manager = self.providers[GPUProvider.MODAL]
            for gpu_type in ["T4", "L4", "A10G", "A100", "H100"]:
                gpus[gpu_type] = {
                    "modal": modal_manager.get_gpu_pricing(gpu_type),
                    "available": True
                }
        
        if GPUProvider.AZURE in self.providers:
            azure_manager = self.providers[GPUProvider.AZURE]
            for gpu_type, spec in azure_manager.GPU_SPECS.items():
                if gpu_type not in gpus:
                    gpus[gpu_type] = {}
                gpus[gpu_type]["azure"] = spec["cost_per_hour"]
        
        return gpus
    
    def calculate_savings_potential(
        self,
        gpu_type: str,
        usage_hours_per_month: int,
        idle_percentage: float = 0.7
    ) -> Dict[str, float]:
        """Calculate potential savings with auto-pause"""
        
        gpus = self.get_supported_gpus()
        
        if gpu_type not in gpus:
            return {}
        
        # Get best price (usually Modal with auto-pause)
        modal_price = gpus[gpu_type].get("modal", 0)
        aws_price = gpus[gpu_type].get("azure", modal_price * 3)  # AWS is ~3x more
        
        # Calculate costs
        always_on_cost = aws_price * 730  # Full month
        active_hours = usage_hours_per_month
        our_cost = modal_price * active_hours  # Only pay for active time
        
        savings = always_on_cost - our_cost
        savings_percent = (savings / always_on_cost) * 100 if always_on_cost > 0 else 0
        
        return {
            "aws_monthly_cost": always_on_cost,
            "our_monthly_cost": our_cost,
            "monthly_savings": savings,
            "savings_percentage": savings_percent
        }