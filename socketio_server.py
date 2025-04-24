import socketio
import threading
import time
from flask import Flask
import requests

# Create a new Flask app and SocketIO server
app = Flask(__name__)
sio = socketio.Server()

# Attach the SocketIO server to the Flask app
app.wsgi_app = sio.WSGIApp(app.wsgi_app)

# A global variable to track the access status
access_status = "Access Pending"


# Define an event when the client connects
@sio.event
def connect(sid, environ):
    print(f"Client connected: {sid}")
    # Send the current status to the client when they connect
    sio.send(sid, access_status)


# Define an event to update the status
@sio.event
def update_status(sid, status):
    global access_status
    access_status = status
    print(f"Updated status: {access_status}")
    # Notify all connected clients with the new status
    sio.send(sid, access_status)


# Define the face recognition loop (simulated here)
def run_face_recognition():
    global access_status
    while True:
        # Simulate face recognition
        access_status = "No match found, access pending"

        print(access_status)
        # Notify all connected clients about the status change
        for sid in sio.connected:
            sio.send(sid, access_status)
        time.sleep(5)


# Run face recognition in a separate thread
thread = threading.Thread(target=run_face_recognition)
thread.start()

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
