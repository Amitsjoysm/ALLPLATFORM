from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"


class OpportunityStatus(str, Enum):
    PENDING = "pending"
    RECOMMENDED = "recommended"
    COMPLETED = "completed"
    IGNORED = "ignored"


class OpportunityType(str, Enum):
    QUESTION = "question"
    TRENDING_KEYWORD = "trending_keyword"
    COMPETITOR_MENTION = "competitor_mention"
    COMPLAINT = "complaint"
    FORUM_DISCUSSION = "forum_discussion"
    CONTENT_GAP = "content_gap"


class ChannelType(str, Enum):
    REDDIT = "reddit"
    QUORA = "quora"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    PRODUCT_HUNT = "product_hunt"
    HACKER_NEWS = "hacker_news"
    GOOGLE_TRENDS = "google_trends"
    YOUTUBE = "youtube"
    COMPETITOR = "competitor"
    FORUM = "forum"


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: str
    role: UserRole = UserRole.USER
    plan: PlanType = PlanType.FREE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    email: EmailStr
    role: UserRole
    plan: PlanType
    created_at: datetime
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class Channel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: ChannelType
    config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RawSignal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    content: str
    link: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)
    processed: bool = False


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_signal_id: str
    channel_id: str
    score: float
    type: OpportunityType
    difficulty: int  # 1-5
    relevance: int  # 1-10
    traffic_potential: int  # 1-10
    competition: int  # 1-5
    user_intent: int  # 1-10
    suggested_action: str
    content_template: Optional[str] = None
    status: OpportunityStatus = OpportunityStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    channel_id: str
    score: float
    type: OpportunityType
    difficulty: int
    suggested_action: str
    content_template: Optional[str]
    status: OpportunityStatus
    created_at: datetime
    signal_content: Optional[str] = None
    signal_link: Optional[str] = None


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    opportunity_id: str
    action_text: str
    content_template: Optional[str] = None
    status: str = "pending"  # pending, completed, ignored
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    user_id: str
    opportunity_id: str
    action_text: str
    content_template: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    opportunity: Optional[OpportunityResponse] = None


class UserActionLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    recommendation_id: str
    action_type: str  # completed, ignored
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class APIToken(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    token_hash: str  # Hashed token for security
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    last_used: Optional[datetime] = None


class AgentContext(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
