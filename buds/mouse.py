"""Mouse control with Head Tracking + Hand Gestures."""

import time
import math
import cv2
import numpy as np

from .connection import GalaxyBudsConnection
from .quaternion import Quaternion

# MediaPipe for hand tracking
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError as e:
    print(f"DEBUG: Import MediaPipe failed: {e}")
    HAS_MEDIAPIPE = False
except Exception as e:
    print(f"DEBUG: Unexpected error importing MediaPipe: {e}")
    HAS_MEDIAPIPE = False

# Quartz for macOS mouse control
try:
    import Quartz
    from Quartz import (
        CGEventCreateMouseEvent, CGEventPost, 
        kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp,
        kCGEventRightMouseDown, kCGEventRightMouseUp, 
        kCGEventLeftMouseDragged,
        kCGMouseButtonLeft, kCGMouseButtonRight, kCGHIDEventTap,
        CGDisplayBounds, CGMainDisplayID
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


class GestureController:
    """Handle MediaPipe hand gestures."""
    def __init__(self):
        if HAS_MEDIAPIPE:
            try:
                # Basic standard import
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    max_num_hands=1,
                    min_detection_confidence=0.7,
                    min_tracking_confidence=0.7
                )
                self.mp_draw = mp.solutions.drawing_utils
                self.active = True
            except Exception as e:
                print(f"MediaPipe Error: {e}")
                self.active = False
        else:
            self.active = False
        
        # State
        self.is_dragging = False
        self.last_click_time = 0
        self.click_cooldown = 0.5
    
    def process(self, frame, mouse_x, mouse_y):
        """Process frame for gestures and trigger actions."""
        if not self.active or not HAS_QUARTZ:
            return frame, "No Hand Track"
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        status = "Open Hand"
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # Get landmark coordinates
                coords = []
                h, w, _ = frame.shape
                for lm in hand_landmarks.landmark:
                    coords.append((int(lm.x * w), int(lm.y * h)))
                
                # Finger tips
                thumb_tip = coords[4]
                index_tip = coords[8]
                middle_tip = coords[12]
                ring_tip = coords[16]
                pinky_tip = coords[20]
                
                # Finger MCP (knuckles) - for fist detection
                index_mcp = coords[5]
                middle_mcp = coords[9]
                ring_mcp = coords[13]
                pinky_mcp = coords[17]
                wrist = coords[0]
                
                # Calculate distances
                dist_thumb_index = math.hypot(thumb_tip[0]-index_tip[0], thumb_tip[1]-index_tip[1])
                dist_thumb_middle = math.hypot(thumb_tip[0]-middle_tip[0], thumb_tip[1]-middle_tip[1])
                
                # 1. FIST DETECTION (Drag Mode)
                # Check if all fingertips are close to wrist/palm
                is_fist = (
                    math.hypot(index_tip[0]-wrist[0], index_tip[1]-wrist[1]) < math.hypot(index_mcp[0]-wrist[0], index_mcp[1]-wrist[1]) and
                    math.hypot(middle_tip[0]-wrist[0], middle_tip[1]-wrist[1]) < math.hypot(middle_mcp[0]-wrist[0], middle_mcp[1]-wrist[1]) and
                    math.hypot(ring_tip[0]-wrist[0], ring_tip[1]-wrist[1]) < math.hypot(ring_mcp[0]-wrist[0], ring_mcp[1]-wrist[1]) and
                    math.hypot(pinky_tip[0]-wrist[0], pinky_tip[1]-wrist[1]) < math.hypot(pinky_mcp[0]-wrist[0], pinky_mcp[1]-wrist[1])
                )
                
                if is_fist:
                    status = "FIST (Drag)"
                    if not self.is_dragging:
                        self._mouse_event(kCGEventLeftMouseDown, mouse_x, mouse_y, kCGMouseButtonLeft)
                        self.is_dragging = True
                else:
                    if self.is_dragging:
                        self._mouse_event(kCGEventLeftMouseUp, mouse_x, mouse_y, kCGMouseButtonLeft)
                        self.is_dragging = False
                    
                    # 2. LEFT CLICK (Thumb + Index pinch)
                    if dist_thumb_index < 30:
                        status = "LEFT CLICK"
                        if time.time() - self.last_click_time > self.click_cooldown:
                            self._click(kCGEventLeftMouseDown, kCGEventLeftMouseUp, mouse_x, mouse_y, kCGMouseButtonLeft)
                            self.last_click_time = time.time()
                    
                    # 3. RIGHT CLICK (Thumb + Middle pinch)
                    elif dist_thumb_middle < 30:
                        status = "RIGHT CLICK"
                        if time.time() - self.last_click_time > self.click_cooldown:
                            self._click(kCGEventRightMouseDown, kCGEventRightMouseUp, mouse_x, mouse_y, kCGMouseButtonRight)
                            self.last_click_time = time.time()
        
        else:
            # Release drag if hand lost
            if self.is_dragging:
                self._mouse_event(kCGEventLeftMouseUp, mouse_x, mouse_y, kCGMouseButtonLeft)
                self.is_dragging = False

        return frame, status

    def _mouse_event(self, type, x, y, button):
        evt = CGEventCreateMouseEvent(None, type, (x, y), button)
        CGEventPost(kCGHIDEventTap, evt)

    def _click(self, down_type, up_type, x, y, button):
        self._mouse_event(down_type, x, y, button)
        time.sleep(0.05)
        self._mouse_event(up_type, x, y, button)


class HeadMouseController:
    def __init__(self, sensitivity=15.0):
        self.sensitivity = sensitivity
        self.center_yaw = 0.0
        self.center_pitch = 0.0
        self.calibrated = False
        self.current_x = 0
        self.current_y = 0
        
        if HAS_QUARTZ:
            display = CGMainDisplayID()
            bounds = CGDisplayBounds(display)
            self.screen_w = bounds.size.width
            self.screen_h = bounds.size.height
            self.cx = self.screen_w / 2
            self.cy = self.screen_h / 2
            self.current_x = self.cx
            self.current_y = self.cy
        else:
            self.screen_w = 1920
            self.screen_h = 1080
    
    def calibrate(self, quat):
        euler = quat.to_euler()
        self.center_yaw = euler[2]
        self.center_pitch = euler[1]
        self.calibrated = True
        print(f"Calibrated center.")
    
    def update(self, quat):
        if not self.calibrated or not HAS_QUARTZ:
            return self.current_x, self.current_y
            
        euler = quat.to_euler()
        dx = euler[2] - self.center_yaw
        dy = euler[1] - self.center_pitch
        
        x = self.cx + (dx * self.sensitivity)
        y = self.cy - (dy * self.sensitivity)
        
        # Clamp
        self.current_x = max(0, min(self.screen_w, x))
        self.current_y = max(0, min(self.screen_h, y))
        
        # Only move mouse; clicks handled by gesture controller
        evt = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (self.current_x, self.current_y), kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, evt)
        
        return self.current_x, self.current_y


def run_mouse_mode(conn: GalaxyBudsConnection):
    """Mouse control with Head Tracking + MediaPipe Hand Gestures."""
    if not HAS_QUARTZ:
        print("Error: Quartz not available.")
        return
    
    if not HAS_MEDIAPIPE:
        print("Error: MediaPipe not available. Install: pip install mediapipe")
        return
    
    head_ctrl = HeadMouseController(sensitivity=25.0)
    gesture_ctrl = GestureController()
    
    # Open webcam
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Webcam error")
        return
    
    print("\n" + "=" * 50)
    print("HEAD + HAND CONTROL")
    print("=" * 50)
    print("HEAD:")
    print("  • Look around -> Move Cursor")
    print("HAND GESTURES:")
    print("  • 👌 Pinch (Thumb+Index)  -> Click Left")
    print("  • 🖕 Pinch (Thumb+Middle) -> Click Right")
    print("  • ✊ Fist (Clench)        -> Drag (Hold Left)")
    print("\nPress ENTER to calibrate look direction...")
    
    # Wait for sensor
    last_ka = time.time()
    while conn.latest_quaternion is None:
        conn.run_loop(0.1)
        if time.time() - last_ka >= 2.0:
            conn.send_keep_alive()
            last_ka = time.time()
            
    input("Press ENTER when looking at screen center...")
    head_ctrl.calibrate(conn.latest_quaternion)
    print("Active! Press ESC to stop.")
    
    cv2.namedWindow("Gestures", cv2.WINDOW_AUTOSIZE)
    
    try:
        while True:
            conn.run_loop(0.01)
            
            # Keep alive
            if time.time() - last_ka >= 2.0:
                conn.send_keep_alive()
                last_ka = time.time()
            
            # 1. Update Head Mouse Position
            mx, my = 0, 0
            if conn.latest_quaternion:
                mx, my = head_ctrl.update(conn.latest_quaternion)
            
            # 2. Process Hand Gestures
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                
                # Process gestures
                frame, status = gesture_ctrl.process(frame, int(mx), int(my))
                
                # Resize for display (small)
                h, w = frame.shape[:2]
                target_w = 240
                target_h = int(target_w * (h / w))
                small = cv2.resize(frame, (target_w, target_h))
                
                # Overlay status
                color = (0, 255, 0)
                if "CLICK" in status: color = (0, 0, 255)
                elif "Drag" in status: color = (0, 255, 255)
                
                cv2.putText(small, status, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 3)
                cv2.putText(small, status, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                
                cv2.imshow("Gestures", small)
            
            if cv2.waitKey(1) & 0xFF == 27:
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
