from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import datetime
from ..utils.database import get_db
from ..utils.auth import get_current_active_user
from ..models.user import User
from ..models.instance import Instance, UsageRecord
from ..schemas.instance import (
    InstanceCreate,
    InstanceResponse,
    InstanceMetrics,
    InstanceAction
)
from ..main import azure_manager, autopause_engine
import uuid

router = APIRouter()

@router.get("/", response_model=List[InstanceResponse])
async def list_instances(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """List all instances for current user"""
    instances = db.query(Instance).filter(Instance.user_id == current_user.id).all()
    return instances

@router.post("/deploy", response_model=InstanceResponse)
async def deploy_instance(
    instance_data: InstanceCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Deploy a new GPU instance in <60 seconds"""
    
    # Check user credits
    estimated_cost = azure_manager.GPU_SPECS[instance_data.gpu_type]["cost_per_hour"]
    if current_user.credits_remaining < estimated_cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits. Please add credits to continue."
        )
    
    # Create instance in Azure
    try:
        azure_instance = await azure_manager.create_instance(
            gpu_type=instance_data.gpu_type,
            user_id=current_user.id,
            name=instance_data.name,
            use_spot=instance_data.use_spot,
            docker_image=instance_data.docker_image
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy instance: {str(e)}"
        )
    
    # Save to database
    db_instance = Instance(
        id=azure_instance["id"],
        user_id=current_user.id,
        name=azure_instance["name"],
        gpu_type=instance_data.gpu_type,
        status="running",
        azure_resource_id=azure_instance["azure_resource_id"],
        public_ip=azure_instance["public_ip"],
        ssh_port=azure_instance["ssh_port"],
        jupyter_url=azure_instance["jupyter_url"],
        api_endpoint=azure_instance["api_endpoint"],
        cost_per_hour=estimated_cost,
        is_spot_instance=instance_data.use_spot,
        auto_pause_enabled=instance_data.auto_pause_enabled,
        template_id=instance_data.template_id,
        environment_vars=instance_data.environment_vars,
        started_at=datetime.utcnow()
    )
    
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    
    # Register with AutoPause
    if instance_data.auto_pause_enabled:
        await autopause_engine.register_instance(db_instance.id, current_user.id)
    
    # Start usage tracking
    usage_record = UsageRecord(
        user_id=current_user.id,
        instance_id=db_instance.id,
        start_time=datetime.utcnow()
    )
    db.add(usage_record)
    db.commit()
    
    return db_instance

@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get instance details"""
    instance = db.query(Instance).filter(
        Instance.id == instance_id,
        Instance.user_id == current_user.id
    ).first()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    return instance

@router.get("/{instance_id}/metrics", response_model=InstanceMetrics)
async def get_instance_metrics(
    instance_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get real-time metrics for an instance"""
    instance = db.query(Instance).filter(
        Instance.id == instance_id,
        Instance.user_id == current_user.id
    ).first()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # Get metrics from Azure
    metrics = await azure_manager.get_instance_metrics(instance.name)
    
    # Add GPU specs
    gpu_spec = azure_manager.GPU_SPECS[instance.gpu_type]
    metrics.update({
        "gpu_memory_total_gb": gpu_spec["gpu_memory_gb"],
        "memory_total_gb": gpu_spec["memory_gb"]
    })
    
    return InstanceMetrics(**metrics)

@router.post("/{instance_id}/action")
async def perform_instance_action(
    instance_id: str,
    action: InstanceAction,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Perform an action on an instance (stop, resume, delete)"""
    instance = db.query(Instance).filter(
        Instance.id == instance_id,
        Instance.user_id == current_user.id
    ).first()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    if action.action == "stop":
        success = await azure_manager.stop_instance(instance.name)
        if success:
            instance.status = "stopped"
            instance.stopped_at = datetime.utcnow()
            
            # End current usage record
            usage_record = db.query(UsageRecord).filter(
                UsageRecord.instance_id == instance_id,
                UsageRecord.end_time.is_(None)
            ).first()
            if usage_record:
                usage_record.end_time = datetime.utcnow()
                usage_record.duration_seconds = (
                    usage_record.end_time - usage_record.start_time
                ).total_seconds()
                usage_record.cost = (
                    usage_record.duration_seconds / 3600
                ) * instance.cost_per_hour
                
                # Update user credits
                current_user.credits_remaining -= usage_record.cost
                instance.total_cost += usage_record.cost
            
            db.commit()
            return {"message": "Instance stopped successfully"}
    
    elif action.action == "resume":
        if instance.status == "paused":
            # Resume from AutoPause
            success = await autopause_engine.resume_instance(instance_id)
        else:
            # Start stopped instance
            success = await azure_manager.start_instance(instance.name)
        
        if success:
            instance.status = "running"
            instance.started_at = datetime.utcnow()
            
            # Start new usage record
            usage_record = UsageRecord(
                user_id=current_user.id,
                instance_id=instance.id,
                start_time=datetime.utcnow()
            )
            db.add(usage_record)
            db.commit()
            
            return {"message": "Instance resumed successfully"}
    
    elif action.action == "pause":
        # Manual pause
        success = await autopause_engine.force_pause(instance_id)
        if success:
            instance.status = "paused"
            instance.paused_at = datetime.utcnow()
            db.commit()
            return {"message": "Instance paused successfully"}
    
    elif action.action == "delete":
        # Delete from Azure
        success = await azure_manager.delete_instance(
            instance.name,
            {"vm": instance.azure_resource_id}
        )
        
        if success:
            # Unregister from AutoPause
            await autopause_engine.unregister_instance(instance_id)
            
            # End usage record
            usage_record = db.query(UsageRecord).filter(
                UsageRecord.instance_id == instance_id,
                UsageRecord.end_time.is_(None)
            ).first()
            if usage_record:
                usage_record.end_time = datetime.utcnow()
                usage_record.duration_seconds = (
                    usage_record.end_time - usage_record.start_time
                ).total_seconds()
                usage_record.cost = (
                    usage_record.duration_seconds / 3600
                ) * instance.cost_per_hour
                current_user.credits_remaining -= usage_record.cost
            
            # Delete from database
            db.delete(instance)
            db.commit()
            
            return {"message": "Instance deleted successfully"}
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: {action.action}"
        )
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to perform action: {action.action}"
    )

@router.get("/{instance_id}/savings")
async def get_instance_savings(
    instance_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get AutoPause savings for an instance"""
    instance = db.query(Instance).filter(
        Instance.id == instance_id,
        Instance.user_id == current_user.id
    ).first()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    savings = autopause_engine.get_instance_savings(instance_id)
    
    return {
        "instance_id": instance_id,
        "total_savings": f"${savings['total_savings']:.2f}",
        "total_paused_hours": f"{savings['total_paused_hours']:.1f}",
        "pause_count": savings["pause_count"],
        "current_status": savings["current_status"],
        "savings_percentage": (
            (savings["total_savings"] / max(instance.total_cost, 0.01)) * 100
            if instance.total_cost > 0 else 0
        )
    }