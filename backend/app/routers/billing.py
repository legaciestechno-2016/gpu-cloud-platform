from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any
from datetime import datetime, timedelta
import stripe
from ..utils.database import get_db
from ..utils.auth import get_current_active_user
from ..utils.config import settings
from ..models.user import User
from ..models.instance import UsageRecord
from ..main import autopause_engine

router = APIRouter()

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Pricing tiers
PRICING_TIERS = {
    "starter": {
        "name": "Starter",
        "price": 299,
        "credits": 400,
        "features": [
            "400 GPU credits/month",
            "AutoPause included",
            "All GPU types",
            "Email support"
        ]
    },
    "business": {
        "name": "Business",
        "price": 999,
        "credits": 1500,
        "features": [
            "1500 GPU credits/month",
            "AutoPause included",
            "Priority support",
            "Custom templates",
            "Team collaboration"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": "custom",
        "credits": "unlimited",
        "features": [
            "Unlimited credits",
            "AutoPause included",
            "24/7 phone support",
            "Custom SLA",
            "Private cloud option",
            "Volume discounts"
        ]
    }
}

@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current usage and billing information"""
    
    # Get current month usage
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    usage_records = db.query(UsageRecord).filter(
        UsageRecord.user_id == current_user.id,
        UsageRecord.created_at >= start_of_month
    ).all()
    
    total_cost = sum(record.cost for record in usage_records)
    total_hours = sum(record.duration_seconds / 3600 for record in usage_records)
    
    # Get AutoPause savings
    total_savings = autopause_engine.get_user_total_savings(current_user.id)
    
    return {
        "current_month": {
            "total_cost": f"${total_cost:.2f}",
            "total_hours": f"{total_hours:.1f}",
            "total_savings": f"${total_savings:.2f}",
            "savings_percentage": (total_savings / max(total_cost, 0.01)) * 100 if total_cost > 0 else 0
        },
        "credits_remaining": f"${current_user.credits_remaining:.2f}",
        "subscription_tier": current_user.subscription_tier,
        "next_billing_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }

@router.get("/usage/detailed")
async def get_detailed_usage(
    start_date: datetime = None,
    end_date: datetime = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed usage records"""
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    usage_records = db.query(UsageRecord).filter(
        UsageRecord.user_id == current_user.id,
        UsageRecord.created_at >= start_date,
        UsageRecord.created_at <= end_date
    ).all()
    
    # Group by day
    daily_usage = {}
    for record in usage_records:
        day = record.created_at.date().isoformat()
        if day not in daily_usage:
            daily_usage[day] = {
                "cost": 0,
                "hours": 0,
                "instances": 0
            }
        daily_usage[day]["cost"] += record.cost
        daily_usage[day]["hours"] += record.duration_seconds / 3600
        daily_usage[day]["instances"] += 1
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "daily_usage": daily_usage,
        "total_cost": sum(d["cost"] for d in daily_usage.values()),
        "total_hours": sum(d["hours"] for d in daily_usage.values())
    }

@router.post("/add-credits")
async def add_credits(
    amount: float,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Add credits to user account"""
    
    if amount < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum credit purchase is $10"
        )
    
    try:
        # Create Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Stripe uses cents
            currency="usd",
            customer=current_user.stripe_customer_id,
            metadata={
                "user_id": str(current_user.id),
                "type": "credits"
            }
        )
        
        return {
            "client_secret": intent.client_secret,
            "amount": amount
        }
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/subscribe/{tier}")
async def subscribe_to_tier(
    tier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Subscribe to a pricing tier"""
    
    if tier not in PRICING_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pricing tier"
        )
    
    if tier == "enterprise":
        return {
            "message": "Please contact sales for Enterprise pricing",
            "contact": "sales@gpucloud.ai"
        }
    
    tier_info = PRICING_TIERS[tier]
    
    try:
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={"user_id": str(current_user.id)}
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        
        # Create subscription
        subscription = stripe.Subscription.create(
            customer=current_user.stripe_customer_id,
            items=[{
                "price": f"price_{tier}"  # You need to create these in Stripe
            }],
            metadata={
                "user_id": str(current_user.id),
                "tier": tier
            }
        )
        
        # Update user subscription
        current_user.subscription_tier = tier
        current_user.credits_remaining += tier_info["credits"]
        db.commit()
        
        return {
            "subscription_id": subscription.id,
            "tier": tier,
            "credits_added": tier_info["credits"],
            "next_billing_date": datetime.fromtimestamp(subscription.current_period_end).isoformat()
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Cancel current subscription"""
    
    if current_user.subscription_tier == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel"
        )
    
    # Cancel in Stripe (implementation needed)
    # ...
    
    current_user.subscription_tier = "free"
    db.commit()
    
    return {"message": "Subscription cancelled successfully"}

@router.get("/invoices")
async def get_invoices(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user invoices"""
    
    if not current_user.stripe_customer_id:
        return {"invoices": []}
    
    try:
        invoices = stripe.Invoice.list(
            customer=current_user.stripe_customer_id,
            limit=10
        )
        
        return {
            "invoices": [
                {
                    "id": inv.id,
                    "date": datetime.fromtimestamp(inv.created).isoformat(),
                    "amount": f"${inv.amount_paid / 100:.2f}",
                    "status": inv.status,
                    "pdf_url": inv.invoice_pdf
                }
                for inv in invoices.data
            ]
        }
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """Handle Stripe webhooks"""
    
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        user_id = payment_intent["metadata"]["user_id"]
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            # Add credits
            amount = payment_intent["amount"] / 100
            user.credits_remaining += amount
            db.commit()
    
    elif event["type"] == "invoice.payment_succeeded":
        # Handle subscription payment
        pass
    
    return {"status": "success"}

@router.get("/pricing")
async def get_pricing_tiers() -> Any:
    """Get available pricing tiers"""
    return PRICING_TIERS