import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from ..utils.config import settings
from .azure_manager import AzureGPUManager

logger = logging.getLogger(__name__)

class AutoPauseEngine:
    """
    AutoPause Engine - The secret sauce that saves 70% on GPU costs
    Monitors GPU utilization and automatically pauses idle instances
    """
    
    def __init__(self, azure_manager: AzureGPUManager):
        self.azure_manager = azure_manager
        self.monitoring_tasks = {}
        self.instance_metrics = {}
        self.pause_candidates = {}
        
        # Configuration
        self.check_interval = settings.AUTOPAUSE_CHECK_INTERVAL  # seconds
        self.idle_threshold = settings.AUTOPAUSE_IDLE_THRESHOLD  # seconds
        self.gpu_usage_threshold = settings.AUTOPAUSE_GPU_USAGE_THRESHOLD  # percent
        
        self.is_running = False
    
    async def start(self):
        """Start the AutoPause monitoring engine"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("AutoPause Engine started - Saving money automatically!")
        
        # Start the main monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop the AutoPause engine"""
        self.is_running = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        logger.info("AutoPause Engine stopped")
    
    async def register_instance(self, instance_id: str, user_id: int):
        """Register an instance for AutoPause monitoring"""
        if instance_id not in self.monitoring_tasks:
            self.instance_metrics[instance_id] = {
                "user_id": user_id,
                "last_active": datetime.utcnow(),
                "idle_time": 0,
                "total_paused_time": 0,
                "total_savings": 0.0,
                "pause_count": 0,
                "gpu_history": []
            }
            logger.info(f"Instance {instance_id} registered for AutoPause monitoring")
    
    async def unregister_instance(self, instance_id: str):
        """Remove an instance from AutoPause monitoring"""
        if instance_id in self.monitoring_tasks:
            self.monitoring_tasks[instance_id].cancel()
            del self.monitoring_tasks[instance_id]
        
        if instance_id in self.instance_metrics:
            del self.instance_metrics[instance_id]
        
        if instance_id in self.pause_candidates:
            del self.pause_candidates[instance_id]
    
    async def _monitoring_loop(self):
        """Main monitoring loop that checks all instances"""
        while self.is_running:
            try:
                # Get all active instances to monitor
                for instance_id, metrics in self.instance_metrics.items():
                    asyncio.create_task(self._check_instance(instance_id))
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in AutoPause monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_instance(self, instance_id: str):
        """Check a single instance for AutoPause conditions"""
        try:
            # Get current instance status
            instance_status = await self.azure_manager.get_instance_status(instance_id)
            
            if not instance_status:
                return
            
            # Only check running instances
            if instance_status["status"] != "running":
                return
            
            # Get current GPU metrics
            metrics = await self.azure_manager.get_instance_metrics(instance_id)
            gpu_utilization = metrics.get("gpu_utilization", 0)
            
            # Update metrics history
            if instance_id in self.instance_metrics:
                history = self.instance_metrics[instance_id]["gpu_history"]
                history.append({
                    "timestamp": datetime.utcnow(),
                    "gpu_utilization": gpu_utilization
                })
                
                # Keep only last 10 minutes of history
                cutoff_time = datetime.utcnow() - timedelta(minutes=10)
                history = [h for h in history if h["timestamp"] > cutoff_time]
                self.instance_metrics[instance_id]["gpu_history"] = history
                
                # Check if instance is idle
                if gpu_utilization < self.gpu_usage_threshold:
                    # Mark as pause candidate
                    if instance_id not in self.pause_candidates:
                        self.pause_candidates[instance_id] = datetime.utcnow()
                        logger.info(f"Instance {instance_id} marked as pause candidate (GPU: {gpu_utilization:.1f}%)")
                    
                    # Check if idle for long enough
                    idle_duration = (datetime.utcnow() - self.pause_candidates[instance_id]).total_seconds()
                    
                    if idle_duration >= self.idle_threshold:
                        await self._pause_instance(instance_id, instance_status)
                
                else:
                    # Instance is active, remove from candidates
                    if instance_id in self.pause_candidates:
                        del self.pause_candidates[instance_id]
                    
                    self.instance_metrics[instance_id]["last_active"] = datetime.utcnow()
                    self.instance_metrics[instance_id]["idle_time"] = 0
        
        except Exception as e:
            logger.error(f"Error checking instance {instance_id}: {e}")
    
    async def _pause_instance(self, instance_id: str, instance_status: Dict):
        """Pause an idle instance to save money"""
        try:
            logger.info(f"AutoPausing instance {instance_id} to save costs...")
            
            # Record pause start time
            pause_start = datetime.utcnow()
            
            # Pause the instance
            success = await self.azure_manager.pause_instance(instance_id)
            
            if success:
                # Update metrics
                if instance_id in self.instance_metrics:
                    self.instance_metrics[instance_id]["pause_count"] += 1
                    self.instance_metrics[instance_id]["last_paused"] = pause_start
                
                # Remove from pause candidates
                if instance_id in self.pause_candidates:
                    del self.pause_candidates[instance_id]
                
                # Calculate and log savings
                hourly_cost = instance_status["specs"]["cost_per_hour"]
                logger.info(f"Instance {instance_id} paused! Saving ${hourly_cost:.2f}/hour")
                
                # Send notification (would integrate with notification service)
                await self._notify_pause(instance_id, hourly_cost)
            
            else:
                logger.error(f"Failed to pause instance {instance_id}")
        
        except Exception as e:
            logger.error(f"Error pausing instance {instance_id}: {e}")
    
    async def resume_instance(self, instance_id: str) -> bool:
        """Resume a paused instance when user returns"""
        try:
            logger.info(f"Resuming instance {instance_id}...")
            
            # Resume the instance
            success = await self.azure_manager.resume_instance(instance_id)
            
            if success and instance_id in self.instance_metrics:
                # Calculate pause duration and savings
                if "last_paused" in self.instance_metrics[instance_id]:
                    pause_duration = (datetime.utcnow() - self.instance_metrics[instance_id]["last_paused"]).total_seconds()
                    
                    # Get instance details for cost calculation
                    instance_status = await self.azure_manager.get_instance_status(instance_id)
                    if instance_status:
                        hourly_cost = instance_status["specs"]["cost_per_hour"]
                        savings = (pause_duration / 3600) * hourly_cost
                        
                        self.instance_metrics[instance_id]["total_paused_time"] += pause_duration
                        self.instance_metrics[instance_id]["total_savings"] += savings
                        
                        logger.info(f"Instance {instance_id} resumed! Saved ${savings:.2f} during pause")
                
                # Reset idle tracking
                self.instance_metrics[instance_id]["last_active"] = datetime.utcnow()
                self.instance_metrics[instance_id]["idle_time"] = 0
                
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error resuming instance {instance_id}: {e}")
            return False
    
    def get_instance_savings(self, instance_id: str) -> Dict:
        """Get AutoPause savings for an instance"""
        if instance_id not in self.instance_metrics:
            return {
                "total_savings": 0.0,
                "total_paused_hours": 0.0,
                "pause_count": 0
            }
        
        metrics = self.instance_metrics[instance_id]
        return {
            "total_savings": metrics["total_savings"],
            "total_paused_hours": metrics["total_paused_time"] / 3600,
            "pause_count": metrics["pause_count"],
            "last_active": metrics.get("last_active"),
            "current_status": "paused" if instance_id in self.pause_candidates else "active"
        }
    
    def get_user_total_savings(self, user_id: int) -> float:
        """Get total AutoPause savings for a user"""
        total = 0.0
        for instance_id, metrics in self.instance_metrics.items():
            if metrics["user_id"] == user_id:
                total += metrics["total_savings"]
        return total
    
    async def force_pause(self, instance_id: str) -> bool:
        """Manually pause an instance (user-triggered)"""
        try:
            instance_status = await self.azure_manager.get_instance_status(instance_id)
            if instance_status and instance_status["status"] == "running":
                await self._pause_instance(instance_id, instance_status)
                return True
            return False
        except Exception as e:
            logger.error(f"Error force pausing instance {instance_id}: {e}")
            return False
    
    async def _notify_pause(self, instance_id: str, savings_per_hour: float):
        """Send notification about instance pause (placeholder)"""
        # In production, this would send email/webhook/notification
        logger.info(f"Notification: Instance {instance_id} paused, saving ${savings_per_hour:.2f}/hour")
    
    def get_analytics(self) -> Dict:
        """Get AutoPause analytics for dashboard"""
        total_instances = len(self.instance_metrics)
        paused_instances = len([i for i in self.instance_metrics if i in self.pause_candidates])
        total_savings = sum(m["total_savings"] for m in self.instance_metrics.values())
        total_pause_time = sum(m["total_paused_time"] for m in self.instance_metrics.values())
        
        return {
            "total_instances_monitored": total_instances,
            "currently_paused": paused_instances,
            "total_savings_all_time": total_savings,
            "total_pause_hours": total_pause_time / 3600,
            "average_savings_per_instance": total_savings / max(total_instances, 1),
            "pause_efficiency": (paused_instances / max(total_instances, 1)) * 100 if total_instances > 0 else 0
        }