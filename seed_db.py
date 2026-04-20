import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


async def seed_database():
    print("🌱 Seeding database...")
    
    # Clear existing data
    await db.users.delete_many({})
    await db.products.delete_many({})
    await db.review_requests.delete_many({})
    await db.video_reviews.delete_many({})
    await db.wallet_transactions.delete_many({})
    await db.orders.delete_many({})
    
    print("✓ Cleared existing data")
    
    # Create sample users
    users = [
        {
            "id": "user-1",
            "name": "John Customer",
            "email": "customer@trivio.com",
            "password": pwd_context.hash("password123"),
            "role": "customer",
            "wallet_balance": 50.0,
            "is_verified_creator": False
        },
        {
            "id": "creator-1",
            "name": "Alice Creator",
            "email": "creator@trivio.com",
            "password": pwd_context.hash("password123"),
            "role": "creator",
            "wallet_balance": 100.0,
            "is_verified_creator": True,
            "creator_rating": 4.8
        },
        {
            "id": "creator-2",
            "name": "Bob Reviewer",
            "email": "reviewer@trivio.com",
            "password": pwd_context.hash("password123"),
            "role": "creator",
            "wallet_balance": 75.0,
            "is_verified_creator": True,
            "creator_rating": 4.5
        },
        {
            "id": "admin-1",
            "name": "Admin User",
            "email": "admin@trivio.com",
            "password": pwd_context.hash("admin123"),
            "role": "admin",
            "wallet_balance": 0.0,
            "is_verified_creator": False
        }
    ]
    
    await db.users.insert_many(users)
    print(f"✓ Created {len(users)} users")
    
    # Create sample products
    products = [
        {
            "id": "1",
            "name": "Premium Wireless Headphones",
            "price": 299.99,
            "original_price": 399.99,
            "category": "Electronics",
            "brand": "AudioTech",
            "rating": 4.5,
            "reviews_count": 1284,
            "video_reviews_count": 2,
            "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&q=80",
            "images": [
                "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&q=80",
                "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=500&q=80",
                "https://images.unsplash.com/photo-1487215078519-e21cc028cb29?w=500&q=80"
            ],
            "description": "Experience premium sound quality with our wireless headphones featuring active noise cancellation, 30-hour battery life, and premium comfort padding.",
            "features": [
                "Active Noise Cancellation",
                "30-hour battery life",
                "Bluetooth 5.0",
                "Premium comfort padding",
                "Foldable design"
            ],
            "in_stock": True,
            "stock": 45
        },
        {
            "id": "2",
            "name": "Ultra Running Shoes",
            "price": 149.99,
            "original_price": 199.99,
            "category": "Footwear",
            "brand": "SportElite",
            "rating": 4.8,
            "reviews_count": 2341,
            "video_reviews_count": 3,
            "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&q=80",
            "images": [
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&q=80",
                "https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?w=500&q=80",
                "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=500&q=80"
            ],
            "description": "Lightweight running shoes engineered for maximum performance. Features responsive cushioning and breathable mesh upper.",
            "features": [
                "Responsive cushioning",
                "Breathable mesh upper",
                "Lightweight design",
                "Durable rubber outsole",
                "Reflective details"
            ],
            "in_stock": True,
            "stock": 78
        },
        {
            "id": "3",
            "name": "Smart Watch Pro",
            "price": 399.99,
            "original_price": 499.99,
            "category": "Electronics",
            "brand": "TechWear",
            "rating": 4.6,
            "reviews_count": 892,
            "video_reviews_count": 1,
            "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&q=80",
            "images": [
                "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&q=80",
                "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=500&q=80",
                "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=500&q=80"
            ],
            "description": "Stay connected and track your fitness with our advanced smartwatch featuring heart rate monitoring, GPS, and smartphone notifications.",
            "features": [
                "Heart rate monitoring",
                "Built-in GPS",
                "Smartphone notifications",
                "Water resistant",
                "7-day battery life"
            ],
            "in_stock": True,
            "stock": 34
        },
        {
            "id": "4",
            "name": "Classic Leather Backpack",
            "price": 129.99,
            "original_price": 179.99,
            "category": "Bags",
            "brand": "UrbanStyle",
            "rating": 4.4,
            "reviews_count": 567,
            "video_reviews_count": 0,
            "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&q=80",
            "images": [
                "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&q=80",
                "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?w=500&q=80",
                "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=500&q=80"
            ],
            "description": "Premium leather backpack with multiple compartments, laptop sleeve, and elegant design perfect for work or travel.",
            "features": [
                "Genuine leather",
                "Laptop compartment (15 inch)",
                "Multiple pockets",
                "Adjustable straps",
                "Water-resistant"
            ],
            "in_stock": True,
            "stock": 23
        }
    ]
    
    await db.products.insert_many(products)
    print(f"✓ Created {len(products)} products")
    
    # Create sample video reviews
    video_reviews = [
        {
            "id": "review-1",
            "product_id": "1",
            "creator_id": "creator-1",
            "creator_name": "Alice Creator",
            "video_url": "https://storage.cloudinary.com/mock/headphones-review.mp4",
            "thumbnail_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300&q=80",
            "duration": 75,
            "is_verified": True,
            "review_request_id": "req-1",
            "likes": 124,
            "views": 1523
        },
        {
            "id": "review-2",
            "product_id": "2",
            "creator_id": "creator-2",
            "creator_name": "Bob Reviewer",
            "video_url": "https://storage.cloudinary.com/mock/shoes-review.mp4",
            "thumbnail_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300&q=80",
            "duration": 68,
            "is_verified": True,
            "review_request_id": "req-2",
            "likes": 89,
            "views": 892
        }
    ]
    
    await db.video_reviews.insert_many(video_reviews)
    print(f"✓ Created {len(video_reviews)} video reviews")
    
    print("\n✅ Database seeded successfully!")
    print("\n📝 Test Accounts:")
    print("   Customer: customer@trivio.com / password123")
    print("   Creator: creator@trivio.com / password123")
    print("   Admin: admin@trivio.com / admin123")


if __name__ == "__main__":
    asyncio.run(seed_database())
    client.close()
