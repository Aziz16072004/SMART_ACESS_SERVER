import cv2
import numpy as np
import face_recognition
import os
import requests
from dotenv import load_dotenv


encodings = []
names = []
load_dotenv()
database_path = "faces/"
FCM_TOKEN = os.getenv("FCM_TOKEN")
API_URL = os.getenv("API_URL")

# Load face encodings from the database
print("Loading face database...")
for person_name in os.listdir(database_path):
    person_folder = os.path.join(database_path, person_name)
    if os.path.isdir(person_folder):
        for file in os.listdir(person_folder):
            if file.endswith(".jpg") or file.endswith(".png"):
                image_path = os.path.join(person_folder, file)
                print(
                    f"Loading image: {image_path}"
                )  # Debugging line to check image path
                image = face_recognition.load_image_file(image_path)
                face_encs = face_recognition.face_encodings(image)

                if face_encs:
                    encodings.append(face_encs[0])
                    names.append(person_name)
                else:
                    print(
                        f"No faces found in {image_path}"
                    )  # Debugging line for missing faces

print(f"Loaded {len(encodings)} encodings from the database.")

# Check if the encodings are populated
if len(encodings) == 0:
    print("No encodings were loaded. Please check the 'faces/' folder.")
    exit()

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(
        face_locations, face_encodings
    ):

        # Increase tolerance for matching
        matches = face_recognition.compare_faces(
            encodings, face_encoding, tolerance=0.7
        )
        name = "Visitor - Access Pending"
        # If there's a match, get the name of the person
        if True in matches:
            matched_names = [names[i] for i, match in enumerate(matches) if match]
            name = max(set(matched_names), key=matched_names.count)
            print(f"Recognized {name}!")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/send_notification/",
                    json={
                        "fcm_token": FCM_TOKEN,
                        "title": "No user Match",
                        "body": "unregistred people",
                    },
                )
                print("Notification response:", response.text)
                time.sleep(8)
            except Exception as e:
                print("Error sending notification:", e)

        # Draw bounding box and label
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(
            frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )

    cv2.imshow("Face Recognition", frame)

    # Exit on pressing 'ESC' key
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
