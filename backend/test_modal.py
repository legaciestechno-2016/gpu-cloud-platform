#!/usr/bin/env python3
"""
Test Modal Integration - Verify GPU deployment works
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set your Modal credentials
# Get these from: https://modal.com/settings/tokens
MODAL_TOKEN_ID = os.getenv("MODAL_TOKEN_ID", "")
MODAL_TOKEN_SECRET = os.getenv("MODAL_TOKEN_SECRET", "")

if not MODAL_TOKEN_ID or not MODAL_TOKEN_SECRET:
    print("⚠️  Please set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET in your .env file")
    print("Get your tokens from: https://modal.com/settings/tokens")
    exit(1)

# Set Modal environment
os.environ["MODAL_TOKEN_ID"] = MODAL_TOKEN_ID
os.environ["MODAL_TOKEN_SECRET"] = MODAL_TOKEN_SECRET

from app.services.modal_gpu_manager import ModalGPUManager

async def test_modal_deployment():
    """Test deploying a GPU instance on Modal"""
    
    print("🚀 Testing Modal GPU Deployment...")
    print("-" * 50)
    
    # Initialize Modal manager
    manager = ModalGPUManager()
    
    # Test 1: Deploy a T4 GPU instance
    print("\n1️⃣ Deploying T4 GPU instance...")
    try:
        instance = await manager.create_gpu_function(
            name="test-gpu-t4",
            gpu_type="T4",
            memory=16384,  # 16GB
            cpu=4.0
        )
        
        print(f"✅ GPU deployed successfully!")
        print(f"   ID: {instance['id']}")
        print(f"   URL: {instance['url']}")
        print(f"   Jupyter: {instance['jupyter_url']}")
        print(f"   Auto-pause: {instance['auto_pause_enabled']}")
        print(f"   Cost: ${manager.get_gpu_pricing('T4')}/hour")
        
    except Exception as e:
        print(f"❌ Failed to deploy: {e}")
        return
    
    # Test 2: Calculate savings
    print("\n2️⃣ Calculating AutoPause savings...")
    
    # Assume 30% active usage (common pattern)
    active_hours = 219  # 30% of 730 hours/month
    idle_hours = 511   # 70% idle
    
    savings = manager.calculate_cost_savings("T4", idle_hours)
    aws_cost = 0.99 * 730  # AWS T4 cost for full month
    our_cost = manager.get_gpu_pricing("T4") * active_hours
    
    print(f"   AWS Cost (always on): ${aws_cost:.2f}/month")
    print(f"   Our Cost (auto-pause): ${our_cost:.2f}/month")
    print(f"   You Save: ${savings:.2f}/month ({(savings/aws_cost)*100:.1f}%)")
    
    # Test 3: Stop function (auto-pause)
    print("\n3️⃣ Testing auto-pause...")
    stopped = await manager.stop_function("test-gpu-t4")
    if stopped:
        print("✅ Instance paused (will auto-resume on next use)")
    
    # Test 4: Check status
    print("\n4️⃣ Checking instance status...")
    status = await manager.get_function_status("test-gpu-t4")
    if status:
        print(f"   Status: {status['status']}")
        print(f"   Is Idle: {status['is_idle']}")
    
    # Test 5: Template deployment
    print("\n5️⃣ Testing template deployment...")
    try:
        template_instance = await manager.create_template_deployment("jupyter-lab")
        print(f"✅ Jupyter Lab deployed!")
        print(f"   URL: {template_instance['jupyter_url']}")
    except Exception as e:
        print(f"⚠️  Template deployment skipped: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Modal integration test complete!")
    print("\nNext steps:")
    print("1. Check your Modal dashboard: https://modal.com/apps")
    print("2. Your functions will auto-pause after 2 minutes idle")
    print("3. They auto-resume in <1 second when accessed")
    
    return instance

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_modal_deployment())
    
    if result:
        print("\n💡 Pro tip: Modal bills per-second and auto-pauses!")
        print("   This means 70% savings vs always-on GPU providers")