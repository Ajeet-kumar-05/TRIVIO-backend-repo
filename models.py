from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
from enum import Enum


# Enums
class UserRole(str, Enum):
    CUSTOMER = "customer"
    CREATOR = "creator"
    ADMIN = "admin"


class ReviewRequestStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TransactionType(str, Enum):
    REWARD = "reward"
    PURCHASE = "purchase"
    REFUND = "refund"
    PENALTY = "penalty"


# User Model (Extended)
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    password: str  # In production, this should be hashed
    role: UserRole = UserRole.CUSTOMER
    wallet_balance: float = 0.0
    creator_rating: Optional[float] = None
    is_verified_creator: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[UserRole] = UserRole.CUSTOMER


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    wallet_balance: float
    is_verified_creator: bool
    creator_rating: Optional[float] = None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# Product Model
class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    original_price: Optional[float] = None
    category: str
    brand: str
    description: str
    image: str
    images: List[str] = []
    features: List[str] = []
    stock: int
    in_stock: bool = True
    rating: float = 0.0
    reviews_count: int = 0
    video_reviews_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProductCreate(BaseModel):
    name: str
    price: float
    original_price: Optional[float] = None
    category: str
    brand: str
    description: str
    image: str
    images: Optional[List[str]] = []
    features: Optional[List[str]] = []
    stock: int


# Review Request Model
class ReviewRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: str  # Denormalized for easy display
    requester_id: str
    requester_name: str  # Denormalized
    assigned_creator_id: Optional[str] = None
    assigned_creator_name: Optional[str] = None
    status: ReviewRequestStatus = ReviewRequestStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_at: Optional[datetime] = None
    deadline: Optional[datetime] = None  # 24 hours from assignment
    completed_at: Optional[datetime] = None
    reward_amount: float = 10.0  # Default reward


class ReviewRequestCreate(BaseModel):
    product_id: str


class ReviewRequestAssign(BaseModel):
    request_id: str


# Video Review Model
class VideoReview(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    creator_id: str
    creator_name: str  # Denormalized
    creator_avatar: Optional[str] = None
    video_url: str  # Mock URL for now, will be Cloudinary URL later
    thumbnail_url: Optional[str] = None
    duration: int = 60  # seconds
    is_verified: bool = True
    review_request_id: str  # Link to the request
    likes: int = 0
    views: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoReviewCreate(BaseModel):
    review_request_id: str
    video_url: str  # Mock upload
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = 60


# Wallet Transaction Model
class WalletTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float
    type: TransactionType
    description: str
    balance_after: float
    reference_id: Optional[str] = None  # Links to review_request_id or order_id
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WalletTransactionCreate(BaseModel):
    user_id: str
    amount: float
    type: TransactionType
    description: str
    reference_id: Optional[str] = None


# Order Model (for cart checkout)
class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_name: str
    user_email: str
    items: List[dict]
    subtotal: float
    shipping: float
    tax: float
    wallet_credits_used: float = 0.0
    total: float
    status: str = "Processing"
    shipping_address: dict
    payment_method: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrderCreate(BaseModel):
    items: List[dict]
    subtotal: float
    shipping: float
    tax: float
    wallet_credits_used: float = 0.0
    total: float
    shipping_address: dict
    payment_method: str
