import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import sys

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

screen_width, screen_height = pyautogui.size()

def move_cursor(index_finger_tip):
    x, y = index_finger_tip.x, index_finger_tip.y
    new_x = int(x * screen_width)
    new_y = int(y * screen_height)
    pyautogui.moveTo(new_x, new_y, duration=0.1)

def list_cameras():
    index = 0
    available_cameras = []
    # Try a wider range of indices (0-10)
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Camera found at index: {index}")
                available_cameras.append(index)
            cap.release()
    
    if not available_cameras:
        print("No cameras detected automatically.")
    return available_cameras

# Get available cameras
available_cameras = list_cameras()

# Allow manual camera selection
print("\nAvailable camera indices:", available_cameras)
camera_index = input("Enter camera index to use (or press Enter to use default 0): ")

try:
    if camera_index.strip():
        current_camera = int(camera_index)
    else:
        current_camera = 0 if available_cameras else 0
    
    print(f"Using camera index: {current_camera}")
    cap = cv2.VideoCapture(current_camera)
    
    if not cap.isOpened():
        print(f"Failed to open camera at index {current_camera}")
        sys.exit(1)
        
except ValueError:
    print("Invalid camera index. Using default (0).")
    current_camera = 0
    cap = cv2.VideoCapture(current_camera)

with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to get frame from camera {current_camera}. Trying again...")
            # Try to reopen the camera
            cap.release()
            cap = cv2.VideoCapture(current_camera)
            continue

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                index_finger_tip = hand_landmarks.landmark[8]
                move_cursor(index_finger_tip)
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Display current camera index on the frame
        cv2.putText(frame, f"Camera: {current_camera}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('Hand Tracking', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            # Ask for a new camera index when 'c' is pressed
            new_index = input("Enter new camera index: ")
            try:
                new_camera = int(new_index)
                print(f"Switching to camera {new_camera}")
                cap.release()
                cap = cv2.VideoCapture(new_camera)
                if cap.isOpened():
                    current_camera = new_camera
                else:
                    print(f"Failed to open camera at index {new_camera}")
                    cap = cv2.VideoCapture(current_camera)  # Revert to previous camera
            except ValueError:
                print("Invalid camera index")

cap.release()
cv2.destroyAllWindows()
