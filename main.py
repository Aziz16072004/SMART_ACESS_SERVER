import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
import bcrypt

# Create the FastAPI app
app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# MongoDB connection setup
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mouhamedazizchaabani:mouhamedazizchaabani@cluster0.o9yxb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
)

client = MongoClient(MONGO_URI)
db = client["CameraDb"]
users_collection = db["users"]


# Pydantic models
class SignUp(BaseModel):
    username: str
    email: EmailStr
    password: str


class SignIn(BaseModel):
    email: EmailStr
    password: str


# SignUp route
@app.post("/register/")
async def signup_user(user: SignUp):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())

    user_data = {
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
    }
    users_collection.insert_one(user_data)

    return {"message": "User registered successfully"}


# SignIn route
@app.post("/test/")
async def test():
    return {
        "message": "Login successful",
    }


@app.post("/signin/")
async def signin_user(user: SignIn):
    existing_user = users_collection.find_one({"email": user.email})

    if not existing_user:
        raise HTTPException(status_code=400, detail="Email not found")

    if not bcrypt.checkpw(user.password.encode("utf-8"), existing_user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    return {
        "message": "Login successful",
        "user_id": str(existing_user["_id"]),
        "username": existing_user.get("username", "Guest"),
    }


# Run FastAPI on Render-compatible port
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
