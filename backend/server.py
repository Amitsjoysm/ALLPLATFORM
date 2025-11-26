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
    Channel, APIToken, UserPreferences, UserPreferencesCreate, UserPreferencesResponse,
    RapidAPIKey, RapidAPIKeyCreate, RapidAPIKeyResponse
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_user_dependency, require_role, generate_api_token, hash_api_token,
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
@limiter.limit("10/hour")
async def register(request: Request, user_data: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
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
    
    # Create default user preferences
    prefs = UserPreferences(user_id=user.id)
    prefs_doc = prefs.model_dump()
    prefs_doc['created_at'] = prefs_doc['created_at'].isoformat()
    prefs_doc['updated_at'] = prefs_doc['updated_at'].isoformat()
    prefs_doc['enabled_channels'] = [ch.value for ch in prefs.enabled_channels]
    prefs_doc['scan_frequency'] = prefs_doc['scan_frequency'].value
    prefs_doc['notification_channels'] = [nc.value for nc in prefs.notification_channels]
    prefs_doc['enabled_opportunity_types'] = [ot.value for ot in prefs.enabled_opportunity_types]
    await db.user_preferences.insert_one(prefs_doc)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    user_response = UserResponse(**user.model_dump())
    return Token(access_token=access_token, user=user_response)


@api_router.post("/auth/login", response_model=Token)
@limiter.limit("20/hour")
async def login(request: Request, credentials: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
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
async def get_me(current_user: User = Depends(get_current_user_dependency)):
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



# ============= USER PREFERENCES MANAGEMENT =============

@api_router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Get current user's preferences"""
    from models import UserPreferences, UserPreferencesResponse
    
    prefs = await db.user_preferences.find_one({"user_id": current_user.id}, {"_id": 0})
    
    if not prefs:
        # Create default preferences
        default_prefs = UserPreferences(user_id=current_user.id)
        doc = default_prefs.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.user_preferences.insert_one(doc)
        return UserPreferencesResponse(**default_prefs.model_dump())
    
    return UserPreferencesResponse(**prefs)


@api_router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences: UserPreferencesCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Update current user's preferences"""
    from models import UserPreferences, UserPreferencesCreate, UserPreferencesResponse
    
    # Get existing preferences or create new
    existing = await db.user_preferences.find_one({"user_id": current_user.id}, {"_id": 0})
    
    if not existing:
        # Create new with provided data
        new_prefs = UserPreferences(user_id=current_user.id)
        existing = new_prefs.model_dump()
    
    # Update with provided fields
    update_data = preferences.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    for key, value in update_data.items():
        existing[key] = value
    
    # Save to database
    existing['updated_at'] = existing['updated_at'].isoformat()
    if 'created_at' in existing and isinstance(existing['created_at'], datetime):
        existing['created_at'] = existing['created_at'].isoformat()
    
    await db.user_preferences.update_one(
        {"user_id": current_user.id},
        {"$set": existing},
        upsert=True
    )
    
    logger.info(f"Preferences updated for user {current_user.email}")
    
    # Return updated preferences
    result = await db.user_preferences.find_one({"user_id": current_user.id}, {"_id": 0})
    return UserPreferencesResponse(**result)


@api_router.post("/preferences/reset")
async def reset_user_preferences(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Reset user preferences to defaults"""
    from models import UserPreferences
    
    default_prefs = UserPreferences(user_id=current_user.id)
    doc = default_prefs.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.user_preferences.update_one(
        {"user_id": current_user.id},
        {"$set": doc},
        upsert=True
    )
    
    logger.info(f"Preferences reset to defaults for user {current_user.email}")
    return {"message": "Preferences reset to defaults"}


# ============= SMART KEYWORD DISCOVERY =============

@api_router.post("/extract-keywords")
@limiter.limit("10/hour")
async def extract_keywords_from_url(
    request: Request,
    url_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Extract keywords from URL using AI"""
    try:
        url = url_data.get('url', '').strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Initialize extractor
        from services import URLKeywordExtractor
        extractor = URLKeywordExtractor()
        
        # Extract keywords
        result = await extractor.extract_keywords(url)
        
        logger.info(f"Extracted {len(result['extracted_keywords'])} keywords from {url} for user {current_user.email}")
        
        return {
            "success": True,
            "url": result['url'],
            "keywords": result['extracted_keywords'],
            "industry": result['industry'],
            "niche": result['niche'],
            "business_type": result['business_type'],
            "target_audience": result['target_audience'],
            "problems_solving": result['problems_solving']
        }
    
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/analyze-seo")
@limiter.limit("5/hour")
async def analyze_seo(
    request: Request,
    url_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Comprehensive SEO analysis with recommendations"""
    try:
        url = url_data.get('url', '').strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Initialize extractor
        from services import URLKeywordExtractor
        extractor = URLKeywordExtractor()
        
        # Analyze SEO
        result = await extractor.analyze_seo(url)
        
        logger.info(f"SEO analysis completed for {url}, score: {result['seo_score']}, user: {current_user.email}")
        
        return {
            "success": True,
            "url": result['url'],
            "seo_score": result['seo_score'],
            "issues": result['issues'],
            "warnings": result['warnings'],
            "good_practices": result['good_practices'],
            "content_gaps": result['content_gaps'],
            "keyword_opportunities": result['keyword_opportunities'],
            "content_suggestions": result['content_suggestions'],
            "technical_recommendations": result['technical_recommendations'],
            "traffic_strategies": result['traffic_strategies'],
            "metadata": result['metadata']
        }
    
    except Exception as e:
        logger.error(f"Error analyzing SEO: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/save-extracted-keywords")
async def save_extracted_keywords(
    keyword_data: dict,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(get_current_user())
):
    """Save extracted keywords to user preferences"""
    try:
        keywords = keyword_data.get('keywords', [])
        url = keyword_data.get('url', '')
        metadata = keyword_data.get('metadata', {})
        
        if not keywords:
            raise HTTPException(status_code=400, detail="No keywords provided")
        
        # Get existing preferences
        prefs = await db.user_preferences.find_one({"user_id": current_user.id}, {"_id": 0})
        
        if not prefs:
            # Create default if not exists
            from models import UserPreferences
            prefs = UserPreferences(user_id=current_user.id).model_dump()
        
        # Add new keywords to extracted_keywords
        existing_extracted = set(prefs.get('extracted_keywords', []))
        existing_extracted.update(keywords)
        
        # Also merge with target_keywords
        existing_target = set(prefs.get('target_keywords', []))
        existing_target.update(keywords)
        
        # Track analyzed URL
        analyzed_urls = prefs.get('analyzed_urls', [])
        analyzed_urls.append({
            'url': url,
            'analyzed_at': datetime.now(timezone.utc).isoformat(),
            'keywords_count': len(keywords),
            'metadata': metadata
        })
        
        # Update preferences
        await db.user_preferences.update_one(
            {"user_id": current_user.id},
            {
                "$set": {
                    "extracted_keywords": list(existing_extracted),
                    "target_keywords": list(existing_target),
                    "analyzed_urls": analyzed_urls,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        logger.info(f"Saved {len(keywords)} extracted keywords for user {current_user.email}")
        
        return {
            "success": True,
            "message": f"Added {len(keywords)} keywords to your preferences",
            "total_keywords": len(existing_target)
        }
    
    except Exception as e:
        logger.error(f"Error saving keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ============= RAPIDAPI KEY MANAGEMENT =============

@api_router.post("/admin/rapidapi-keys", response_model=RapidAPIKeyResponse)
@limiter.limit("10/hour")
async def create_rapidapi_key(
    request: Request,
    key_data: RapidAPIKeyCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    """Create a new RapidAPI key for LinkedIn scraping"""
    # Check if key already exists
    existing = await db.rapidapi_keys.find_one({"api_key": key_data.api_key})
    if existing:
        raise HTTPException(status_code=400, detail="This API key already exists")
    
    # Create new key
    api_key = RapidAPIKey(
        name=key_data.name,
        api_key=key_data.api_key,
        notes=key_data.notes,
        created_by=current_user.id
    )
    
    doc = api_key.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('last_used'):
        doc['last_used'] = doc['last_used'].isoformat()
    
    await db.rapidapi_keys.insert_one(doc)
    logger.info(f"RapidAPI key '{key_data.name}' created by {current_user.email}")
    
    return RapidAPIKeyResponse(**api_key.model_dump())


@api_router.get("/admin/rapidapi-keys", response_model=List[RapidAPIKeyResponse])
async def get_rapidapi_keys(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    """Get all RapidAPI keys"""
    keys = await db.rapidapi_keys.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for key in keys:
        if isinstance(key.get('created_at'), str):
            key['created_at'] = datetime.fromisoformat(key['created_at'])
        if key.get('last_used') and isinstance(key['last_used'], str):
            key['last_used'] = datetime.fromisoformat(key['last_used'])
    
    return [RapidAPIKeyResponse(**key) for key in keys]


@api_router.put("/admin/rapidapi-keys/{key_id}/toggle")
async def toggle_rapidapi_key(
    key_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    """Enable or disable a RapidAPI key"""
    key = await db.rapidapi_keys.find_one({"id": key_id}, {"_id": 0})
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    new_status = not key.get("is_active", True)
    
    result = await db.rapidapi_keys.update_one(
        {"id": key_id},
        {"$set": {"is_active": new_status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    status_text = "enabled" if new_status else "disabled"
    logger.info(f"RapidAPI key {key_id} {status_text} by {current_user.email}")
    
    return {"status": "success", "message": f"API key {status_text}", "is_active": new_status}


@api_router.delete("/admin/rapidapi-keys/{key_id}")
async def delete_rapidapi_key(
    key_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    """Delete a RapidAPI key"""
    result = await db.rapidapi_keys.delete_one({"id": key_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    logger.info(f"RapidAPI key {key_id} deleted by {current_user.email}")
    
    return {"status": "success", "message": "API key deleted"}


@api_router.get("/admin/rapidapi-keys/stats")
async def get_rapidapi_keys_stats(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN]))
):
    """Get statistics about RapidAPI key usage"""
    total_keys = await db.rapidapi_keys.count_documents({})
    active_keys = await db.rapidapi_keys.count_documents({"is_active": True})
    
    # Get total usage
    pipeline = [
        {"$group": {"_id": None, "total_usage": {"$sum": "$usage_count"}}}
    ]
    usage_result = await db.rapidapi_keys.aggregate(pipeline).to_list(1)
    total_usage = usage_result[0]["total_usage"] if usage_result else 0
    
    return {
        "total_keys": total_keys,
        "active_keys": active_keys,
        "inactive_keys": total_keys - active_keys,
        "total_usage": total_usage
    }


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
