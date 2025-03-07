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
import win32clipboard

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

# Add variables to track states
save_dialog_active = False
last_gesture_time = 0
GESTURE_COOLDOWN = 1.0  # Reduced cooldown time for smoother response
last_skip_time = 0
SKIP_COOLDOWN = 0.8  # Specific cooldown for YouTube skip

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

def get_clipboard_text():
    """Get text from clipboard"""
    try:
        win32clipboard.OpenClipboard()
        try:
            text = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
            return text.decode('utf-8')
        except:
            return ""
        finally:
            win32clipboard.CloseClipboard()
    except:
        return ""

def handle_thumbs_up_action():
    """Handle thumbs up gesture based on active window"""
    global save_dialog_active, last_gesture_time, last_skip_time
    
    # Check cooldown to prevent accidental double gestures
    current_time = time.time()
    if current_time - last_gesture_time < GESTURE_COOLDOWN:
        return
    last_gesture_time = current_time
    
    active_window = get_active_window_title().lower()
    
    if "youtube" in active_window:
        # Check specific cooldown for YouTube skip
        if current_time - last_skip_time < SKIP_COOLDOWN:
            return
        last_skip_time = current_time
        
        # Just press 'l' to skip forward 10 seconds
        pyautogui.press('l')
        print("Skipped forward 10 seconds!")
        
    elif "notepad" in active_window or "save as" in active_window:
        if not save_dialog_active:
            # First thumbs up: Open save dialog and prepare filename
            print("First thumbs up detected - Opening save dialog...")
            
            # Select all text and copy
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)  # Increased wait for selection
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)  # Increased wait for clipboard
            
            # Get first line of text for filename
            content = get_clipboard_text()
            filename = content.split('\n')[0][:30] if content else "untitled"
            filename = ''.join(c for c in filename if c.isalnum() or c in (' ', '-', '_')) + '.txt'
            
            # Open save dialog
            pyautogui.hotkey('ctrl', 'shift', 's')
            time.sleep(1.5)  # Increased wait for dialog
            
            # Navigate to Documents
            documents_path = os.path.expanduser("~/Documents")
            pyautogui.write(documents_path)
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(1.0)  # Increased wait after navigation
            
            # Write filename
            pyautogui.write(filename)
            save_dialog_active = True
            print(f"Save As dialog opened - Suggested filename: {filename}")
            
        else:
            # Second thumbs up: Confirm save
            print("Second thumbs up detected - Saving file...")
            time.sleep(0.5)  # Increased wait before save
            
            # Make sure we're in the save dialog
            active = get_active_window_title().lower()
            if "save as" in active:
                # Press Alt+S as a more reliable way to save
                pyautogui.hotkey('alt', 's')
                time.sleep(0.3)
                
                # Also try Enter as a backup
                pyautogui.press('enter')
                time.sleep(0.3)
                
                save_dialog_active = False
                print("File saved successfully!")
            else:
                print("Save dialog not found. Please try again.")
                save_dialog_active = False
            
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
            # Check specific cooldown for YouTube skip
            if current_time - last_skip_time < SKIP_COOLDOWN:
                return
            last_skip_time = current_time
            
            current_window = win32gui.GetForegroundWindow()
            win32gui.SetForegroundWindow(youtube_windows[0])
            time.sleep(0.2)  # Reduced delay
            
            # Just press 'l' to skip
            pyautogui.press('l')
            print("Skipped forward 10 seconds (background window)!")
            
            time.sleep(0.2)  # Reduced delay
            win32gui.SetForegroundWindow(current_window)

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