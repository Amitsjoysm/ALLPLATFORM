from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from contextlib import asynccontextmanager
import os
import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from database import connect_to_mongo, close_mongo_connection, get_database
from config import settings
from models import (
    User, UserCreate, UserLogin, UserResponse, Token, UserRole, PlanType,
    OpportunityResponse, OpportunityStatus, RecommendationResponse,
    Channel, APIToken
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_role, generate_api_token, hash_api_token,
    get_current_user_flexible
)
from middleware import (
    limiter, SecurityHeadersMiddleware, RequestLoggingMiddleware,
    RequestValidationMiddleware
)
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    
    # Create default superadmin if not exists
    db = get_database()
    admin = await db.users.find_one({"email": "admin@traffic.engine"})
    if not admin:
        admin_user = User(
            email="admin@traffic.engine",
            password_hash=get_password_hash("admin123"),
            role=UserRole.SUPERADMIN,
            plan=PlanType.PRO
        )
        doc = admin_user.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.users.insert_one(doc)
        logger.info("Default superadmin created: admin@traffic.engine / admin123")
    
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Traffic Opportunity Engine",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)
api_router = APIRouter(prefix="/api")

# Add rate limiter state
app.state.limiter = limiter

# Rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )


# Dependency to get database
async def get_db():
    return get_database()


# ============= AUTH ENDPOINTS =============

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password)
    )
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['role'] = doc['role'].value
    doc['plan'] = doc['plan'].value
    
    await db.users.insert_one(doc)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    user_response = UserResponse(**user.model_dump())
    return Token(access_token=access_token, user=user_response)


@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user_doc or not verify_password(credentials.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**user_doc)
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    access_token = create_access_token(data={"sub": user.id})
    user_response = UserResponse(**user.model_dump())
    
    return Token(access_token=access_token, user=user_response)


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(db: AsyncIOMotorDatabase = Depends(get_db), current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.model_dump())


# ============= OPPORTUNITIES ENDPOINTS =============

@api_router.get("/opportunities", response_model=List[OpportunityResponse])
async def get_opportunities(
    score_min: Optional[float] = Query(None, ge=0, le=100),
    status: Optional[OpportunityStatus] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = {}
    
    if score_min is not None:
        query["score"] = {"$gte": score_min}
    
    if status:
        query["status"] = status.value
    
    opportunities = await db.opportunities.find(query, {"_id": 0}).sort("score", -1).limit(limit).to_list(limit)
    
    # Convert ISO strings back to datetime
    for opp in opportunities:
        if isinstance(opp.get('created_at'), str):
            opp['created_at'] = datetime.fromisoformat(opp['created_at'])
    
    # Fetch signal data
    result = []
    for opp in opportunities:
        signal = await db.raw_signals.find_one({"id": opp.get("raw_signal_id")}, {"_id": 0})
        opp_response = OpportunityResponse(**opp)
        if signal:
            opp_response.signal_content = signal.get("content", "")[:200]
            opp_response.signal_link = signal.get("link")
        result.append(opp_response)
    
    return result


@api_router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    opp = await db.opportunities.find_one({"id": opportunity_id}, {"_id": 0})
    
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    if isinstance(opp.get('created_at'), str):
        opp['created_at'] = datetime.fromisoformat(opp['created_at'])
    
    signal = await db.raw_signals.find_one({"id": opp.get("raw_signal_id")}, {"_id": 0})
    opp_response = OpportunityResponse(**opp)
    if signal:
        opp_response.signal_content = signal.get("content", "")
        opp_response.signal_link = signal.get("link")
    
    return opp_response


# ============= RECOMMENDATIONS ENDPOINTS =============

@api_router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_user_recommendations(
    status_filter: Optional[str] = Query(None, regex="^(pending|completed|ignored)$"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = {"user_id": current_user.id}
    
    if status_filter:
        query["status"] = status_filter
    
    recommendations = await db.recommendations.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Convert ISO strings and fetch opportunities
    result = []
    for rec in recommendations:
        if isinstance(rec.get('created_at'), str):
            rec['created_at'] = datetime.fromisoformat(rec['created_at'])
        if rec.get('completed_at') and isinstance(rec['completed_at'], str):
            rec['completed_at'] = datetime.fromisoformat(rec['completed_at'])
        
        rec_response = RecommendationResponse(**rec)
        
        # Fetch opportunity details
        opp = await db.opportunities.find_one({"id": rec["opportunity_id"]}, {"_id": 0})
        if opp:
            if isinstance(opp.get('created_at'), str):
                opp['created_at'] = datetime.fromisoformat(opp['created_at'])
            rec_response.opportunity = OpportunityResponse(**opp)
        
        result.append(rec_response)
    
    return result


@api_router.post("/recommendations/{recommendation_id}/complete")
async def complete_recommendation(
    recommendation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rec = await db.recommendations.find_one({"id": recommendation_id, "user_id": current_user.id}, {"_id": 0})
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Update recommendation
    await db.recommendations.update_one(
        {"id": recommendation_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Log action
    await db.user_actions_log.insert_one({
        "user_id": current_user.id,
        "recommendation_id": recommendation_id,
        "action_type": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"status": "success", "message": "Recommendation marked as completed"}


@api_router.post("/recommendations/{recommendation_id}/ignore")
async def ignore_recommendation(
    recommendation_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rec = await db.recommendations.find_one({"id": recommendation_id, "user_id": current_user.id}, {"_id": 0})
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    await db.recommendations.update_one(
        {"id": recommendation_id},
        {"$set": {"status": "ignored"}}
    )
    
    return {"status": "success", "message": "Recommendation ignored"}


# ============= ADMIN ENDPOINTS =============

@api_router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return [UserResponse(**user) for user in users]


@api_router.put("/admin/users/{user_id}/plan")
async def update_user_plan(
    user_id: str,
    plan: PlanType,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERADMIN]))
):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"plan": plan.value}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"status": "success", "message": f"User plan updated to {plan.value}"}


@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: UserRole,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERADMIN]))
):
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": role.value}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"status": "success", "message": f"User role updated to {role.value}"}


@api_router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERADMIN]))
):
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"status": "success", "message": "User deleted"}


@api_router.get("/admin/stats")
async def get_admin_stats(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    total_users = await db.users.count_documents({})
    total_opportunities = await db.opportunities.count_documents({})
    total_recommendations = await db.recommendations.count_documents({})
    pending_recommendations = await db.recommendations.count_documents({"status": "pending"})
    completed_recommendations = await db.recommendations.count_documents({"status": "completed"})
    
    # High-value opportunities (score > 70)
    high_value_opps = await db.opportunities.count_documents({"score": {"$gte": 70}})
    
    return {
        "total_users": total_users,
        "total_opportunities": total_opportunities,
        "total_recommendations": total_recommendations,
        "pending_recommendations": pending_recommendations,
        "completed_recommendations": completed_recommendations,
        "high_value_opportunities": high_value_opps
    }


# ============= CHANNELS MANAGEMENT =============

@api_router.get("/admin/channels", response_model=List[Channel])
async def get_channels(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    channels = await db.channels.find({}, {"_id": 0}).to_list(100)
    
    for channel in channels:
        if isinstance(channel.get('created_at'), str):
            channel['created_at'] = datetime.fromisoformat(channel['created_at'])
    
    return [Channel(**ch) for ch in channels]


@api_router.put("/admin/channels/{channel_id}/toggle")
async def toggle_channel(
    channel_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERADMIN]))
):
    channel = await db.channels.find_one({"id": channel_id})
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    new_status = not channel.get("is_active", True)
    
    await db.channels.update_one(
        {"id": channel_id},
        {"$set": {"is_active": new_status}}
    )
    
    return {"status": "success", "message": f"Channel {'activated' if new_status else 'deactivated'}"}


# ============= TRIGGER MANUAL SCAN =============

@api_router.post("/admin/trigger-scan")
async def trigger_manual_scan(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERADMIN]))
):
    from celery_tasks import run_hourly_scan
    
    # Trigger scan asynchronously
    task = run_hourly_scan.delay()
    
    return {
        "status": "success",
        "message": "Scan triggered",
        "task_id": task.id
    }


# ============= API TOKEN MANAGEMENT =============

@api_router.post("/tokens/generate")
@limiter.limit("5/hour")
async def generate_user_api_token(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Generate a new API token for the current user"""
    # Generate token
    token = generate_api_token()
    token_hash = hash_api_token(token)
    
    # Store in database
    api_token = APIToken(
        user_id=current_user.id,
        token_hash=token_hash,
        permissions=["read", "write"]
    )
    
    doc = api_token.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.api_tokens.insert_one(doc)
    
    logger.info(f"API token generated for user {current_user.email}")
    
    # Return the plain token (only time it's visible)
    return {
        "token": token,
        "token_id": api_token.id,
        "message": "Save this token securely. It won't be shown again."
    }


@api_router.get("/tokens")
async def list_user_tokens(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """List all API tokens for current user (hashed)"""
    cursor = db.api_tokens.find(
        {"user_id": current_user.id},
        {"_id": 0, "token_hash": 0}
    ).sort("created_at", -1)
    
    tokens = await cursor.to_list(length=100)
    return tokens


@api_router.delete("/tokens/{token_id}")
async def revoke_api_token(
    token_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Revoke an API token"""
    result = await db.api_tokens.update_one(
        {"id": token_id, "user_id": current_user.id},
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Token not found")
    
    logger.info(f"API token {token_id} revoked for user {current_user.email}")
    return {"message": "Token revoked successfully"}


# ============= HEALTH CHECK =============

@api_router.get("/health")
async def health_check(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Enhanced health check with dependency status"""
    health_status = {
        "status": "healthy",
        "service": "Traffic Opportunity Engine",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check MongoDB
    try:
        await db.command("ping")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis (for Celery)
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


# Include router
app.include_router(api_router)

# Add middleware (order matters - first added is outermost)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestValidationMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)
