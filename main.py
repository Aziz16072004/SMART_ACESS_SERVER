import os
import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from fastapi.staticfiles import StaticFiles
from bson import ObjectId
import requests
from pymongo import MongoClient
from fastapi.responses import JSONResponse
import bcrypt
from dotenv import load_dotenv
from datetime import datetime
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import json
import jwt
import shutil

# Create the FastAPI app
app = FastAPI()
upload_dir = "faces/"

if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)
app.mount("/faces", StaticFiles(directory="faces"), name="faces")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client["CameraDb"]
users_collection = db["users"]
pictures_collection = db["pictures"]
history_collection = db["history"]


# Pydantic models
class SignUp(BaseModel):
    username: str
    email: EmailStr
    password: str


class Picture(BaseModel):
    userId: str
    picture: str
    name: str
    accessLevel: str


class SignIn(BaseModel):
    email: EmailStr
    password: str


class History(BaseModel):
    userId: str
    registered: bool
    timestamp: datetime


class NotificationData(BaseModel):
    fcm_token: str
    title: str
    body: str


# Firebase Cloud Messaging credentials
PROJECT_ID = "smartaccess-3df78"
SERVICE_ACCOUNT_FILE = "smartaccess-3df78-firebase-adminsdk-fbsvc-94740c8ae5.json"


def get_access_token():
    # Load the service account file
    with open(SERVICE_ACCOUNT_FILE, "r") as file:
        service_account_info = json.load(file)

    # Create credentials with the correct scope for Firebase Cloud Messaging
    scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=scopes
    )

    # Refresh the credentials to get the access token
    credentials.refresh(Request())

    return credentials.token


@app.post("/send_notification/")
async def send_notification(notification: NotificationData):
    # Get the access token
    access_token = get_access_token()
    print(f"Access token: {access_token}")

    # FCM HTTP v1 API URL
    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"

    # Set up headers for the request
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Prepare the message payload
    message = {
        "message": {
            "token": notification.fcm_token,
            "notification": {
                "title": notification.title,
                "body": notification.body,
            },
        }
    }

    # Send the notification via HTTP POST request
    response = requests.post(url, json=message, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        return {"message": "Notification sent successfully"}
    else:
        return {"error": response.text}


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


upload_dir = "faces/"

# Ensure the base directory exists
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)


@app.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    userId: str = Form(...),
    name: str = Form(...),
    accessLevel: str = Form(...),
):
    try:
        # Create a subdirectory for the person if it doesn't exist
        person_dir = os.path.join(upload_dir, name)
        if not os.path.exists(person_dir):
            os.makedirs(person_dir)

        # Generate a unique filename
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}"
        file_path = os.path.join(person_dir, filename)

        # Save the file
        with open(file_path, "wb") as buffer:
            buffer.write(await image.read())

        # Create a new picture document to insert into MongoDB
        picture_data = {
            "userId": userId,
            "name": name,
            "picture": file_path,  # Store the file path or URL
            "accessLevel": accessLevel,
        }

        # Insert the picture data into the database
        pictures_collection.insert_one(picture_data)

        # Return a response with the picture data
        return JSONResponse(
            content={
                "message": "Image uploaded and saved!",
                "file_path": file_path,
                "userId": userId,
                "name": name,
                "accessLevel": accessLevel,
            }
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/pictures/{user_id}")
async def get_user_pictures(user_id: str):
    try:
        # Find all pictures for the given user ID
        pictures = list(pictures_collection.find({"userId": user_id}))

        # Convert ObjectId to string for each picture
        for picture in pictures:
            picture["_id"] = str(picture["_id"])

        return JSONResponse(
            content={
                "message": "Pictures retrieved successfully",
                "pictures": pictures,
            }
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.delete("/pictures/{picture_id}")
async def delete_picture(picture_id: str):
    try:
        # Find the picture from the database using its ObjectId
        picture = pictures_collection.find_one({"_id": ObjectId(picture_id)})

        if not picture:
            return JSONResponse(
                content={"error": "Picture not found"},
                status_code=404,
            )

        # Get the file URL from the picture document (this is where the image is stored)
        file_url = picture["picture"]  # e.g., "/static/uploads/filename"

        # Extract the filename and directory from the file_url
        path_parts = file_url.split("/")
        directory = os.path.join(upload_dir, *path_parts[1:-1])  # e.g., "faces/mohamed"
        filename = path_parts[-1]
        file_path = os.path.join(directory, filename)

        # Check if the file exists and delete it
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            return JSONResponse(
                content={"error": "File not found on the server"},
                status_code=404,
            )

        # Check if the directory is empty and remove it
        if not os.listdir(directory):  # Check if directory is empty
            shutil.rmtree(directory)  # Delete the empty directory

        # Delete the picture from MongoDB
        result = pictures_collection.delete_one({"_id": ObjectId(picture_id)})

        if result.deleted_count == 0:
            return JSONResponse(
                content={"error": "Failed to delete the picture from the database"},
                status_code=500,
            )

        return JSONResponse(
            content={
                "message": "Picture and directory deleted successfully, both from database and server"
            },
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/history/{user_id}")
async def get_user_history(user_id: str):
    try:
        # Find all history records for the given user ID
        history = list(history_collection.find({"userId": user_id}))

        # Convert ObjectId to string for each history entry
        for entry in history:
            entry["_id"] = str(entry["_id"])

        return JSONResponse(
            content={
                "message": "History retrieved successfully",
                "history": history,
            }
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/history/")
async def add_history(
    userId: str = Form(...),
    registered: bool = Form(...),
):
    try:
        # Create a new history entry with the given userId and registered status
        history_entry = History(
            userId=userId,
            registered=registered,
            timestamp=datetime.now(),
        )

        # Insert the history entry into the MongoDB collection
        history_dict = history_entry.dict()
        history_collection = db["history"]
        result = history_collection.insert_one(history_dict)

        # Return a response with the newly created history entry
        return JSONResponse(
            content={
                "message": "History entry added successfully!",
                "history": history_dict,
            },
            status_code=201,
        )

    except Exception as e:
        # If there's an error, return a response with the error message
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
