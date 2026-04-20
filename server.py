from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from models import (
    User, UserCreate, UserLogin, UserResponse, UserRole, AuthResponse,
    Product, ProductCreate,
    ReviewRequest, ReviewRequestCreate, ReviewRequestAssign, ReviewRequestStatus,
    VideoReview, VideoReviewCreate,
    WalletTransaction, WalletTransactionCreate, TransactionType,
    Order, OrderCreate
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'trivio_db')]

# Security
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id == None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_role(user: dict, allowed_roles: List[UserRole]):
    if user.get("role") not in [role.value for role in allowed_roles]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


# ============= AUTH ROUTES =============

@api_router.post("/auth/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
        role=user_data.role
    )
    
    user_dict = user.dict()
    await db.users.insert_one(user_dict)
    
    # Create token
    token = create_access_token({"user_id": user.id, "email": user.email})
    
    # Return response using AuthResponse model
    user_response = UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        wallet_balance=user.wallet_balance,
        is_verified_creator=user.is_verified_creator,
        creator_rating=user.creator_rating
    )
    
    return AuthResponse(token=token, user=user_response)


@api_router.post("/auth/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"user_id": user["id"], "email": user["email"]})
    
    # Return response using AuthResponse model
    user_response = UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        wallet_balance=user.get("wallet_balance", 0.0),
        is_verified_creator=user.get("is_verified_creator", False),
        creator_rating=user.get("creator_rating")
    )
    
    return AuthResponse(token=token, user=user_response)


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)


# ============= PRODUCT ROUTES =============

@api_router.get("/products", response_model=List[Product])
async def get_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    query = {}
    
    if category:
        query["category"] = category
    if min_price != None or max_price != None:
        query["price"] = {}
        if min_price != None:
            query["price"]["$gte"] = min_price
        if max_price != None:
            query["price"]["$lte"] = max_price
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"brand": {"$regex": search, "$options": "i"}}
        ]
    
    products = await db.products.find(query).to_list(1000)
    return [Product(**product) for product in products]


@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)


@api_router.post("/products", response_model=Product)
async def create_product(
    product_data: ProductCreate,
    current_user: dict = Depends(get_current_user)
):
    await require_role(current_user, [UserRole.ADMIN])
    
    product = Product(**product_data.dict())
    await db.products.insert_one(product.dict())
    return product


@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    product_data: ProductCreate,
    current_user: dict = Depends(get_current_user)
):
    await require_role(current_user, [UserRole.ADMIN])
    
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": product_data.dict()}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = await db.products.find_one({"id": product_id})
    return Product(**product)


@api_router.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    await require_role(current_user, [UserRole.ADMIN])
    
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted successfully"}


# ============= REVIEW REQUEST ROUTES (OV2RS Core) =============

@api_router.post("/review-requests", response_model=ReviewRequest)
async def create_review_request(
    request_data: ReviewRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    # Get product details
    product = await db.products.find_one({"id": request_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if user already has a pending request for this product
    existing_request = await db.review_requests.find_one({
        "product_id": request_data.product_id,
        "requester_id": current_user["id"],
        "status": {"$in": [ReviewRequestStatus.PENDING.value, ReviewRequestStatus.ASSIGNED.value]}
    })
    
    if existing_request:
        raise HTTPException(status_code=400, detail="You already have a pending request for this product")
    
    # Create request
    review_request = ReviewRequest(
        product_id=request_data.product_id,
        product_name=product["name"],
        requester_id=current_user["id"],
        requester_name=current_user["name"]
    )
    
    await db.review_requests.insert_one(review_request.dict())
    
    return review_request


@api_router.get("/review-requests", response_model=List[ReviewRequest])
async def get_review_requests(
    status: Optional[ReviewRequestStatus] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    # If customer, show only their requests
    if current_user["role"] == UserRole.CUSTOMER.value:
        query["requester_id"] = current_user["id"]
    # If creator, show pending or their assigned requests
    elif current_user["role"] == UserRole.CREATOR.value:
        query["$or"] = [
            {"status": ReviewRequestStatus.PENDING.value},
            {"assigned_creator_id": current_user["id"]}
        ]
    
    if status:
        query["status"] = status.value
    
    requests = await db.review_requests.find(query).sort("created_at", -1).to_list(1000)
    return [ReviewRequest(**req) for req in requests]


@api_router.post("/creator/accept-task", response_model=ReviewRequest)
async def accept_review_task(
    assign_data: ReviewRequestAssign,
    current_user: dict = Depends(get_current_user)
):
    await require_role(current_user, [UserRole.CREATOR, UserRole.ADMIN])
    
    # Get request
    request = await db.review_requests.find_one({"id": assign_data.request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Review request not found")
    
    if request["status"] != ReviewRequestStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Request is not available")
    
    # Assign to creator
    assigned_at = datetime.utcnow()
    deadline = assigned_at + timedelta(hours=24)
    
    await db.review_requests.update_one(
        {"id": assign_data.request_id},
        {
            "$set": {
                "assigned_creator_id": current_user["id"],
                "assigned_creator_name": current_user["name"],
                "status": ReviewRequestStatus.ASSIGNED.value,
                "assigned_at": assigned_at,
                "deadline": deadline
            }
        }
    )
    
    updated_request = await db.review_requests.find_one({"id": assign_data.request_id})
    return ReviewRequest(**updated_request)


@api_router.get("/creator/tasks", response_model=List[ReviewRequest])
async def get_creator_tasks(current_user: dict = Depends(get_current_user)):
    await require_role(current_user, [UserRole.CREATOR, UserRole.ADMIN])
    
    # Get assigned tasks
    tasks = await db.review_requests.find({
        "assigned_creator_id": current_user["id"],
        "status": {"$in": [ReviewRequestStatus.ASSIGNED.value, ReviewRequestStatus.COMPLETED.value]}
    }).sort("deadline", 1).to_list(1000)
    
    return [ReviewRequest(**task) for task in tasks]


# ============= VIDEO REVIEW ROUTES =============

@api_router.post("/creator/upload-review", response_model=VideoReview)
async def upload_video_review(
    review_data: VideoReviewCreate,
    current_user: dict = Depends(get_current_user)
):
    await require_role(current_user, [UserRole.CREATOR, UserRole.ADMIN])
    
    # Get review request
    request = await db.review_requests.find_one({"id": review_data.review_request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Review request not found")
    
    if request["assigned_creator_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized for this request")
    
    if request["status"] != ReviewRequestStatus.ASSIGNED.value:
        raise HTTPException(status_code=400, detail="Request is not in assigned state")
    
    # Check if within deadline
    is_on_time = datetime.utcnow() <= request["deadline"]
    
    # Create video review
    video_review = VideoReview(
        product_id=request["product_id"],
        creator_id=current_user["id"],
        creator_name=current_user["name"],
        video_url=review_data.video_url,
        thumbnail_url=review_data.thumbnail_url,
        duration=review_data.duration,
        review_request_id=review_data.review_request_id
    )
    
    await db.video_reviews.insert_one(video_review.dict())
    
    # Update request status
    await db.review_requests.update_one(
        {"id": review_data.review_request_id},
        {
            "$set": {
                "status": ReviewRequestStatus.COMPLETED.value,
                "completed_at": datetime.utcnow()
            }
        }
    )
    
    # Update product video review count
    await db.products.update_one(
        {"id": request["product_id"]},
        {"$inc": {"video_reviews_count": 1}}
    )
    
    # Add reward or penalty
    if is_on_time:
        # Add reward
        reward_amount = request.get("reward_amount", 10.0)
        await add_wallet_transaction(
            current_user["id"],
            reward_amount,
            TransactionType.REWARD,
            f"Video review reward for {request['product_name']}",
            request["id"]
        )
    else:
        # Penalty: reduce rating (optional)
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"creator_rating": -0.1}}
        )
    
    return video_review


@api_router.get("/products/{product_id}/video-reviews", response_model=List[VideoReview])
async def get_product_video_reviews(product_id: str):
    reviews = await db.video_reviews.find({"product_id": product_id}).sort("created_at", -1).to_list(1000)
    return [VideoReview(**review) for review in reviews]


# ============= WALLET ROUTES =============

async def add_wallet_transaction(
    user_id: str,
    amount: float,
    transaction_type: TransactionType,
    description: str,
    reference_id: Optional[str] = None
):
    # Get current balance
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_balance = user.get("wallet_balance", 0.0)
    new_balance = current_balance + amount
    
    # Update user balance
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"wallet_balance": new_balance}}
    )
    
    # Create transaction record
    transaction = WalletTransaction(
        user_id=user_id,
        amount=amount,
        type=transaction_type,
        description=description,
        balance_after=new_balance,
        reference_id=reference_id
    )
    
    await db.wallet_transactions.insert_one(transaction.dict())
    return transaction


@api_router.get("/wallet/balance")
async def get_wallet_balance(current_user: dict = Depends(get_current_user)):
    return {"balance": current_user.get("wallet_balance", 0.0)}


@api_router.get("/wallet/transactions", response_model=List[WalletTransaction])
async def get_wallet_transactions(current_user: dict = Depends(get_current_user)):
    transactions = await db.wallet_transactions.find(
        {"user_id": current_user["id"]}
    ).sort("created_at", -1).to_list(1000)
    
    return [WalletTransaction(**txn) for txn in transactions]


# ============= ORDER ROUTES =============

@api_router.post("/orders", response_model=Order)
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user)
):
    # Validate wallet credits
    if order_data.wallet_credits_used > 0:
        if current_user.get("wallet_balance", 0.0) < order_data.wallet_credits_used:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        
        # Deduct from wallet
        await add_wallet_transaction(
            current_user["id"],
            -order_data.wallet_credits_used,
            TransactionType.PURCHASE,
            f"Used for order purchase",
            None
        )
    
    # Create order
    order = Order(
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_email=current_user["email"],
        **order_data.dict()
    )
    
    await db.orders.insert_one(order.dict())
    
    return order


@api_router.get("/orders", response_model=List[Order])
async def get_orders(current_user: dict = Depends(get_current_user)):
    orders = await db.orders.find({"user_id": current_user["id"]}).sort("created_at", -1).to_list(1000)
    return [Order(**order) for order in orders]


# ============= ADMIN ROUTES =============

@api_router.get("/admin/review-requests", response_model=List[ReviewRequest])
async def admin_get_all_review_requests(current_user: dict = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN])
    
    requests = await db.review_requests.find({}).sort("created_at", -1).to_list(1000)
    return [ReviewRequest(**req) for req in requests]


@api_router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN])
    
    total_requests = await db.review_requests.count_documents({})
    completed_requests = await db.review_requests.count_documents({"status": ReviewRequestStatus.COMPLETED.value})
    pending_requests = await db.review_requests.count_documents({"status": ReviewRequestStatus.PENDING.value})
    total_video_reviews = await db.video_reviews.count_documents({})
    
    completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "total_requests": total_requests,
        "completed_requests": completed_requests,
        "pending_requests": pending_requests,
        "total_video_reviews": total_video_reviews,
        "completion_rate": round(completion_rate, 2)
    }


# ============= HEALTH CHECK =============

@api_router.get("/")
async def root():
    return {"message": "Trivio API with OV2RS - Real Reviews. Real Trust."}


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
