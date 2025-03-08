from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
import bcrypt

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


# Pydantic model for SignIn
class SignIn(BaseModel):
    email: EmailStr
    password: str


# SignIn user
@app.post("/signin/")
async def signin_user(user: SignIn):
    # Find the user by email
    existing_user = users_collection.find_one({"email": user.email})

    if not existing_user:
        raise HTTPException(status_code=400, detail="Email not found")

    # Compare the provided password with the hashed password stored in the database
    if not bcrypt.checkpw(user.password.encode("utf-8"), existing_user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    # Return success response including username
    return {
        "message": "Login successful",
        "user_id": str(existing_user["_id"]),
        "username": existing_user.get("username", "Guest")  # Fallback to "Guest" if missing
    }

