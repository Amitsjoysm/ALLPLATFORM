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
    signal_content: Optional[str] = None
    signal_link: Optional[str] = None
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



class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    NONE = "none"


class ScanFrequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    TWICE_DAILY = "twice_daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class UserPreferences(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    
    # Channel Selection - which platforms to scan
    enabled_channels: List[ChannelType] = Field(
        default_factory=lambda: [
            ChannelType.REDDIT,
            ChannelType.HACKER_NEWS,
            ChannelType.PRODUCT_HUNT,
            ChannelType.GOOGLE_TRENDS
        ]
    )
    
    # Topic/Keyword Preferences
    target_keywords: List[str] = Field(default_factory=list)  # e.g., ["email verification", "b2b leads"]
    industry: str = ""  # e.g., "SaaS", "B2B Marketing"
    niche: str = ""  # e.g., "Email tools", "Lead generation"
    exclude_keywords: List[str] = Field(default_factory=list)  # Keywords to avoid
    
    # Smart Keyword Discovery (URL-based extraction)
    extracted_keywords: List[str] = Field(default_factory=list)  # Keywords extracted from URLs
    analyzed_urls: List[Dict[str, Any]] = Field(default_factory=list)  # History of analyzed URLs with metadata
    
    # Scan Frequency Control
    scan_frequency: ScanFrequency = ScanFrequency.HOURLY
    custom_cron: Optional[str] = None  # For custom frequency (e.g., "0 */3 * * *")
    
    # Notification Preferences
    notification_channels: List[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.NONE]
    )
    notification_email: Optional[str] = None
    notification_slack_webhook: Optional[str] = None
    notification_whatsapp_number: Optional[str] = None
    notify_on_high_score_only: bool = True  # Only notify for high-priority opportunities
    min_score_for_notification: float = 70.0
    
    # Opportunity Filters
    min_opportunity_score: float = 50.0  # Minimum score threshold
    enabled_opportunity_types: List[OpportunityType] = Field(
        default_factory=lambda: [
            OpportunityType.QUESTION,
            OpportunityType.TRENDING_KEYWORD,
            OpportunityType.COMPETITOR_MENTION,
            OpportunityType.COMPLAINT,
            OpportunityType.FORUM_DISCUSSION
        ]
    )
    max_opportunities_per_day: int = 50  # Limit daily recommendations
    
    # Advanced Settings
    auto_generate_content: bool = True  # Auto-generate content templates
    include_competitor_analysis: bool = True
    competitor_domains: List[str] = Field(default_factory=list)  # e.g., ["apollo.io", "hunter.io"]
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserPreferencesCreate(BaseModel):
    enabled_channels: Optional[List[ChannelType]] = None
    target_keywords: Optional[List[str]] = None
    industry: Optional[str] = None
    niche: Optional[str] = None
    exclude_keywords: Optional[List[str]] = None
    scan_frequency: Optional[ScanFrequency] = None
    custom_cron: Optional[str] = None
    notification_channels: Optional[List[NotificationChannel]] = None
    notification_email: Optional[str] = None
    notification_slack_webhook: Optional[str] = None
    notification_whatsapp_number: Optional[str] = None
    notify_on_high_score_only: Optional[bool] = None
    min_score_for_notification: Optional[float] = None
    min_opportunity_score: Optional[float] = None
    enabled_opportunity_types: Optional[List[OpportunityType]] = None
    max_opportunities_per_day: Optional[int] = None
    auto_generate_content: Optional[bool] = None
    include_competitor_analysis: Optional[bool] = None
    competitor_domains: Optional[List[str]] = None


class UserPreferencesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    user_id: str
    enabled_channels: List[ChannelType]
    target_keywords: List[str]
    industry: str
    niche: str
    exclude_keywords: List[str]
    scan_frequency: ScanFrequency
    custom_cron: Optional[str]
    notification_channels: List[NotificationChannel]
    notification_email: Optional[str]
    notification_slack_webhook: Optional[str]
    notification_whatsapp_number: Optional[str]
    notify_on_high_score_only: bool
    min_score_for_notification: float
    min_opportunity_score: float
    enabled_opportunity_types: List[OpportunityType]
    max_opportunities_per_day: int
    auto_generate_content: bool
    include_competitor_analysis: bool
    competitor_domains: List[str]
    created_at: datetime
    updated_at: datetime
