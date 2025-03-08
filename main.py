from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId

# Create the FastAPI app
app = FastAPI()

# Add the CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins to make requests
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# MongoDB connection setup (using pymongo)
client = MongoClient("mongodb://localhost:27017")
db = client["CameraDb"]
users_collection = db["users"]


# Pydantic model to validate incoming data
class User(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    class Config:
        schema_extra = {
            "example": {
                "username": "testuser",
                "email": "test@example.com",
                "password": "your_password",
                "confirm_password": "your_password",
            }
        }


# Register a new user
@app.post("/register/")
async def register_user(user: User):
    # Check if passwords match
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Check if email already exists
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already in use")

    # Hash password before saving
    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())

    # Create new user
    new_user = {
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
    }

    # Insert new user into the database
    result = users_collection.insert_one(new_user)

    # Return response
    return {"message": "User created successfully", "user_id": str(result.inserted_id)}
