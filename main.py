import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
import bcrypt
from dotenv import load_dotenv

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

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
print(MONGO_URI)


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
        "message": "test sucess",
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


# @app.post("/upload")
# async def upload_image(image: UploadFile = File(...)):
#    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}"
#    file_path = os.path.join(UPLOAD_DIR, filename)
#    with open(file_path, "wb") as buffer:
#        buffer.write(await image.read())
#    return JSONResponse(content={"message": "Image saved!", "filename": filename})
# Run FastAPI on Render-compatible port
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
