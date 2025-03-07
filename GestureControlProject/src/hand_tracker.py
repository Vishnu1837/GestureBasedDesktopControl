import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import sys
import tkinter as tk
from tkinter import messagebox
import win32gui
import time
from threading import Thread
import queue

class CameraStream:
    def __init__(self):
        self.stream = None
        self.stopped = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.available_cameras = self.list_cameras()
        
    def list_cameras(self):
        """List all available cameras"""
        available = []
        for i in range(10):  # Check first 10 indexes
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Use DirectShow
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
        return available
    
    def start(self, camera_index=0):
        """Start camera stream"""
        if not self.available_cameras:
            raise Exception("No cameras found!")
            
        if camera_index not in self.available_cameras:
            camera_index = self.available_cameras[0]
            
        self.stream = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not self.stream.isOpened():
            raise Exception(f"Failed to open camera {camera_index}")
            
        self.stopped = False
        Thread(target=self._update, args=()).start()
        return self
        
    def _update(self):
        """Update frames in background thread"""
        while True:
            if self.stopped:
                return
            
            if not self.frame_queue.full():
                ret, frame = self.stream.read()
                if ret:
                    self.frame_queue.put(frame)
                    
    def read(self):
        """Read frame from queue"""
        return self.frame_queue.get() if not self.frame_queue.empty() else None
        
    def stop(self):
        """Stop camera stream"""
        self.stopped = True
        if self.stream:
            self.stream.release()
        while not self.frame_queue.empty():
            self.frame_queue.get()

class HandTrackerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hand Gesture Control")
        
        # Set window size and position it in center
        window_width = 400
        window_height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.configure(bg='black')
        
        self.tracking = False  # Add tracking state
        
        # Add custom button style
        self.button_style = {
            'font': ("Arial", 14, "bold"),
            'width': 15,
            'height': 2,
            'relief': tk.RAISED,
            'cursor': "hand2",
            'borderwidth': 3,  # Add border width
            'padx': 20,
            'pady': 10
        }
        
        self.camera = CameraStream()  # Initialize camera handler
        
        # Create and pack widgets
        self.create_widgets()
        
    def create_widgets(self):
        # Title Label with bigger font and padding
        title_label = tk.Label(
            self.root,
            text="Hand Gesture Control System",
            font=("Arial", 24, "bold"),  # Increased font size
            bg='black',
            fg='#00FF00'  # Bright green color for title
        )
        title_label.pack(pady=40)
        
        # Description with enhanced visibility
        desc_label = tk.Label(
            self.root,
            text="Use hand gestures to control your computer\n\n" +
                 "Right hand: Move cursor with index finger\n" +
                 "Right hand: Thumbs up for context actions\n" +
                 "Left hand: Make a fist to click",
            font=("Arial", 12),  # Increased font size
            bg='black',
            fg='#FFFFFF',  # Bright white color
            justify=tk.LEFT
        )
        desc_label.pack(pady=30)
        
        # Button Frame with padding
        button_frame = tk.Frame(self.root, bg='black', pady=20)
        button_frame.pack(expand=True)
        
        # Start Button with enhanced style
        self.start_button = tk.Button(
            button_frame,
            text="Start Tracking",
            command=self.start_tracking,
            bg='#00CC00',  # Slightly darker green for better contrast
            fg='white',    # White text for better visibility
            activebackground='#00FF00',  # Bright green when hovered
            activeforeground='black',
            **self.button_style
        )
        self.start_button.pack(side=tk.LEFT, padx=20)
        
        # Stop Button with enhanced style
        self.stop_button = tk.Button(
            button_frame,
            text="Stop Tracking",
            command=self.stop_tracking,
            bg='#CC0000',  # Slightly darker red for better contrast
            fg='white',
            activebackground='#FF0000',  # Bright red when hovered
            activeforeground='white',
            state=tk.DISABLED,
            **self.button_style
        )
        self.stop_button.pack(side=tk.LEFT, padx=20)

        # Add hover effects
        self.add_button_hover_effects()

    def add_button_hover_effects(self):
        """Add hover effects to buttons"""
        def on_enter_start(e):
            if self.start_button['state'] != 'disabled':
                self.start_button['bg'] = '#00FF00'
                
        def on_leave_start(e):
            if self.start_button['state'] != 'disabled':
                self.start_button['bg'] = '#00CC00'

        def on_enter_stop(e):
            if self.stop_button['state'] != 'disabled':
                self.stop_button['bg'] = '#FF0000'
                
        def on_leave_stop(e):
            if self.stop_button['state'] != 'disabled':
                self.stop_button['bg'] = '#CC0000'

        self.start_button.bind("<Enter>", on_enter_start)
        self.start_button.bind("<Leave>", on_leave_start)
        self.stop_button.bind("<Enter>", on_enter_stop)
        self.stop_button.bind("<Leave>", on_leave_stop)

    def start_tracking(self):
        self.tracking = True
        self.start_button.config(
            state=tk.DISABLED,
            bg='#004400'  # Darker green when disabled
        )
        self.stop_button.config(
            state=tk.NORMAL,
            bg='#CC0000'
        )
        self.root.withdraw()
        self.run_hand_tracker()
        
    def stop_tracking(self):
        self.tracking = False
        self.camera.stop()  # Stop camera when tracking stops
        self.start_button.config(
            state=tk.NORMAL,
            bg='#00CC00'
        )
        self.stop_button.config(
            state=tk.DISABLED,
            bg='#440000'
        )
        self.root.deiconify()

    def get_active_window_title(self):
        """Get the title of the currently active window"""
        window = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(window)

    def is_thumbs_up(self, hand_landmarks):
        """Detect if hand is making a thumbs up gesture"""
        thumb_tip = hand_landmarks.landmark[4]
        thumb_base = hand_landmarks.landmark[2]
        
        # Check if thumb is extended upward and other fingers are folded
        return (thumb_tip.y < thumb_base.y and 
                all(hand_landmarks.landmark[i].y > hand_landmarks.landmark[i-2].y 
                    for i in [8, 12, 16, 20]))

    def handle_thumbs_up_action(self):
        """Handle thumbs up gesture based on active window"""
        active_window = self.get_active_window_title().lower()
        
        if "youtube" in active_window:
            pyautogui.press('l')  # Like the video
        elif "notepad" in active_window:
            pyautogui.hotkey('ctrl', 's')  # Save the file
        elif "chrome" in active_window or "firefox" in active_window:
            pyautogui.hotkey('ctrl', 'd')  # Bookmark page
        elif "explorer" in active_window:
            pyautogui.hotkey('ctrl', 'c')  # Copy selected file
        time.sleep(1)  # Prevent multiple actions

    def run_hand_tracker(self):
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        screen_width, screen_height = pyautogui.size()

        try:
            # Start camera stream
            self.camera.start()
        except Exception as e:
            messagebox.showerror("Camera Error", str(e))
            self.stop_tracking()
            return

        with mp_hands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            max_num_hands=2  # Allow detection of both hands
        ) as hands:
            while self.tracking:
                frame = self.camera.read()
                if frame is None:
                    continue

                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb_frame)

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        handedness = results.multi_handedness[
                            results.multi_hand_landmarks.index(hand_landmarks)
                        ].classification[0].label
                        
                        index_finger_tip = hand_landmarks.landmark[8]
                        
                        if handedness == 'Right':
                            # Move cursor with right hand
                            x = int(index_finger_tip.x * screen_width)
                            y = int(index_finger_tip.y * screen_height)
                            pyautogui.moveTo(x, y, duration=0.1)
                            
                            # Check for thumbs up gesture with right hand
                            if self.is_thumbs_up(hand_landmarks):
                                self.handle_thumbs_up_action()
                            
                        if handedness == 'Left':
                            # Check for fist gesture
                            if self.is_fist(hand_landmarks):
                                pyautogui.click()
                                print("Click triggered!")
                                
                        mp_drawing.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Add status text and camera info to frame
                cv2.putText(frame, "Press 'Q' to return to menu", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Camera: {self.camera.available_cameras}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow('Hand Tracking', frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.tracking = False
                    break

        self.camera.stop()
        cv2.destroyAllWindows()
        self.stop_tracking()
        
    def is_fist(self, hand_landmarks):
        thumb = hand_landmarks.landmark[4]
        index_finger = hand_landmarks.landmark[8]
        middle_finger = hand_landmarks.landmark[12]
        ring_finger = hand_landmarks.landmark[16]
        pinky_finger = hand_landmarks.landmark[20]

        return (thumb.y > hand_landmarks.landmark[3].y and
                index_finger.y > hand_landmarks.landmark[6].y and
                middle_finger.y > hand_landmarks.landmark[10].y and
                ring_finger.y > hand_landmarks.landmark[14].y and
                pinky_finger.y > hand_landmarks.landmark[18].y)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = HandTrackerUI()
    app.run() 