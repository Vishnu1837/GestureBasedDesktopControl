import cv2
import mediapipe as mp
import pyautogui
import math
import win32gui
import time
import numpy as np
from threading import Thread
import queue
import os

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# Add this class for threaded webcam reading
class WebcamVideoStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.stopped = False
        self.queue = queue.Queue(maxsize=2)
        
    def start(self):
        Thread(target=self._update, args=()).start()
        return self
        
    def _update(self):
        while True:
            if self.stopped:
                return
            if not self.queue.full():
                ret, frame = self.stream.read()
                if ret:
                    self.queue.put(frame)
                    
    def read(self):
        return self.queue.get()
        
    def stop(self):
        self.stopped = True

# Replace the webcam initialization with:
cap = WebcamVideoStream(src=0).start()
screen_width, screen_height = pyautogui.size()
pyautogui.FAILSAFE = False

# Smoothing factor for cursor movement
smoothing = 0.5
prev_x, prev_y = 0, 0

def get_active_window_title():
    """Get the title of the currently active window"""
    window = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(window)

def calculate_distance(point1, point2):
    """Calculate distance between two points"""
    return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)

def is_fist(hand_landmarks):
    """Detect if hand is making a fist gesture"""
    fingers_folded = True
    finger_tips = [8, 12, 16, 20]  # Index, Middle, Ring, Pinky tip points
    finger_bases = [5, 9, 13, 17]  # Corresponding base points
    
    for tip, base in zip(finger_tips, finger_bases):
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[base].y:
            fingers_folded = False
            break
    return fingers_folded

def is_thumbs_up(hand_landmarks):
    """Detect if hand is making a thumbs up gesture"""
    thumb_tip = hand_landmarks.landmark[4]
    thumb_base = hand_landmarks.landmark[2]
    index_tip = hand_landmarks.landmark[8]
    
    # Check if thumb is extended upward and other fingers are folded
    return (thumb_tip.y < thumb_base.y and 
            all(hand_landmarks.landmark[i].y > hand_landmarks.landmark[i-2].y 
                for i in [8, 12, 16, 20]))

def handle_thumbs_up_action():
    """Handle thumbs up gesture based on active window"""
    active_window = get_active_window_title().lower()
    
    if "youtube" in active_window:
        # Simulate pressing 'l' key which is the shortcut for liking a YouTube video
        pyautogui.press('l')
        print("YouTube video liked!")
    elif "notepad" in active_window:
        # Use Ctrl+Shift+S for "Save As" dialog
        pyautogui.hotkey('ctrl', 'shift', 's')
        time.sleep(0.5)  # Wait for dialog to appear
        
        # Type the Documents path
        documents_path = os.path.expanduser("~/Documents")
        pyautogui.write(documents_path)
        pyautogui.press('enter')
        
        print("Save As dialog opened in Documents folder")
    else:
        # Check if YouTube window exists in background
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if "youtube" in title:
                    windows.append(hwnd)
            return True
        
        youtube_windows = []
        win32gui.EnumWindows(callback, youtube_windows)
        
        if youtube_windows:
            # Store current window to return to it later
            current_window = win32gui.GetForegroundWindow()
            
            # Switch to YouTube window
            win32gui.SetForegroundWindow(youtube_windows[0])
            time.sleep(0.5)  # Wait for window to become active
            
            # Like the video
            pyautogui.press('l')
            print("YouTube video liked (background window)!")
            
            # Switch back to original window
            win32gui.SetForegroundWindow(current_window)
            
    time.sleep(1)  # Prevent multiple actions

try:
    while True:
        img = cap.read()
        if img is None:
            continue
            
        # Flip the image horizontally
        img = cv2.flip(img, 1)
        
        # Convert to RGB
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Process hand landmarks with performance flag
        results = hands.process(rgb_img)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Only draw landmarks if needed (comment out if not needed)
                # mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Get index finger tip coordinates
                index_finger = hand_landmarks.landmark[8]
                x = int(index_finger.x * screen_width)
                y = int(index_finger.y * screen_height)
                
                # Apply smoothing
                x = int(prev_x + (x - prev_x) * smoothing)
                y = int(prev_y + (y - prev_y) * smoothing)
                prev_x, prev_y = x, y
                
                # Move cursor
                pyautogui.moveTo(x, y)
                
                # Check for fist gesture (click)
                if is_fist(hand_landmarks):
                    pyautogui.click()
                    time.sleep(0.5)  # Prevent multiple clicks
                
                # Check for thumbs up gesture
                if is_thumbs_up(hand_landmarks):
                    handle_thumbs_up_action()
        
        # Display the image
        cv2.imshow("Gesture Control", img)
        
        # Break loop with 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.stop()
    cv2.destroyAllWindows() 