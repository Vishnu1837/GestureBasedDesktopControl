import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import sys

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

screen_width, screen_height = pyautogui.size()

# Store previous fingertip depth (z-coordinate)
prev_z = None
click_threshold = 0.02  # Adjust this threshold based on testing

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

def is_fist(hand_landmarks):
    # Check if the left hand is making a fist
    thumb = hand_landmarks.landmark[4]  # Thumb tip
    index_finger = hand_landmarks.landmark[8]  # Index finger tip
    middle_finger = hand_landmarks.landmark[12]  # Middle finger tip
    ring_finger = hand_landmarks.landmark[16]  # Ring finger tip
    pinky_finger = hand_landmarks.landmark[20]  # Pinky finger tip

    # Debugging output to check positions
    print(f"Thumb Y: {thumb.y}, Index Y: {index_finger.y}, Middle Y: {middle_finger.y}, Ring Y: {ring_finger.y}, Pinky Y: {pinky_finger.y}")
    print(f"Base Thumb Y: {hand_landmarks.landmark[3].y}, Base Index Y: {hand_landmarks.landmark[6].y}, Base Middle Y: {hand_landmarks.landmark[10].y}, Base Ring Y: {hand_landmarks.landmark[14].y}, Base Pinky Y: {hand_landmarks.landmark[18].y}")

    # Check if all fingertips are above the base of the fingers
    if (thumb.y > hand_landmarks.landmark[3].y and
        index_finger.y > hand_landmarks.landmark[6].y and
        middle_finger.y > hand_landmarks.landmark[10].y and
        ring_finger.y > hand_landmarks.landmark[14].y and
        pinky_finger.y > hand_landmarks.landmark[18].y):
        print("Fist detected!")  # Debugging output
        return True
    return False

with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to get frame from camera {current_camera}. Trying again...")
            cap.release()
            cap = cv2.VideoCapture(current_camera)
            continue

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Determine if the hand is left or right
                handedness = results.multi_handedness[results.multi_hand_landmarks.index(hand_landmarks)].classification[0].label
                index_finger_tip = hand_landmarks.landmark[8]
                z = index_finger_tip.z  # Depth value

                if handedness == 'Right':
                    # Move cursor with right index finger
                    move_cursor(index_finger_tip)

                if handedness == 'Left':
                    # Check if left hand is making a fist
                    if is_fist(hand_landmarks):
                        # Trigger click if fist is detected
                        if prev_z is not None and (prev_z - z) > click_threshold:
                            pyautogui.click()  # Simulate a click
                            print("Click triggered!")

                prev_z = z  # Update previous Z value
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Display current camera index on the frame
        cv2.putText(frame, f"Camera: {current_camera}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('Hand Tracking', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
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
