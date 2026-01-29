"""Webcam visualization with head tracking overlay."""

import cv2
import numpy as np
import time
import math

from .connection import GalaxyBudsConnection
from .quaternion import Quaternion


def draw_orientation_indicator(frame, quat: Quaternion, x, y, size=150):
    """Draw 3D orientation indicator on frame."""
    if quat is None:
        return
    
    euler = quat.to_euler()
    roll, pitch, yaw = euler
    
    # Colors
    color_ring = (100, 100, 100)
    color_yaw = (100, 100, 255)    # Red
    color_pitch = (255, 200, 100)  # Cyan
    color_roll = (100, 255, 200)   # Green
    color_arrow = (0, 255, 255)    # Yellow
    
    # Draw base circle
    cv2.circle(frame, (x, y), size, color_ring, 2)
    cv2.circle(frame, (x, y), size - 30, color_ring, 1)
    cv2.circle(frame, (x, y), size - 60, color_ring, 1)
    
    # Draw yaw indicator (horizontal rotation)
    yaw_rad = math.radians(yaw)
    yaw_x = int(x + size * 0.9 * math.sin(yaw_rad))
    yaw_y = int(y - size * 0.9 * math.cos(yaw_rad))
    cv2.line(frame, (x, y), (yaw_x, yaw_y), color_yaw, 3)
    cv2.circle(frame, (yaw_x, yaw_y), 8, color_yaw, -1)
    
    # Draw pitch indicator (arc)
    pitch_angle = int(pitch)
    if pitch_angle != 0:
        start_angle = -90 - pitch_angle
        end_angle = -90
        cv2.ellipse(frame, (x, y), (size - 40, size - 40), 
                   0, min(start_angle, end_angle), max(start_angle, end_angle), 
                   color_pitch, 3)
    
    # Draw roll indicator (tilted line)
    roll_rad = math.radians(roll)
    roll_len = size - 50
    roll_x1 = int(x - roll_len * math.cos(roll_rad))
    roll_y1 = int(y + roll_len * math.sin(roll_rad))
    roll_x2 = int(x + roll_len * math.cos(roll_rad))
    roll_y2 = int(y - roll_len * math.sin(roll_rad))
    cv2.line(frame, (roll_x1, roll_y1), (roll_x2, roll_y2), color_roll, 2)
    
    # Center dot
    cv2.circle(frame, (x, y), 5, (255, 255, 255), -1)


def draw_data_panel(frame, quat: Quaternion, x, y):
    """Draw data panel on frame."""
    if quat is None:
        return
    
    euler = quat.to_euler()
    
    # Semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + 280, y + 180), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Border
    cv2.rectangle(frame, (x, y), (x + 280, y + 180), (80, 80, 80), 1)
    
    # Title
    cv2.putText(frame, "ORIENTATION DATA", (x + 15, y + 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    # Euler angles
    cv2.putText(frame, f"Roll:  {euler[0]:+7.2f} deg", (x + 15, y + 55), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 200), 1)
    cv2.putText(frame, f"Pitch: {euler[1]:+7.2f} deg", (x + 15, y + 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 100), 1)
    cv2.putText(frame, f"Yaw:   {euler[2]:+7.2f} deg", (x + 15, y + 105), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 1)
    
    # Quaternion
    cv2.putText(frame, "Quaternion:", (x + 15, y + 135), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    cv2.putText(frame, f"[{quat.w:+.3f}, {quat.x:+.3f}, {quat.y:+.3f}, {quat.z:+.3f}]", 
                (x + 15, y + 160), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)


def draw_3d_axes(frame, quat: Quaternion, x, y, size=100):
    """Draw 3D coordinate axes based on orientation."""
    if quat is None:
        return
    
    rot = quat.to_rotation_matrix()
    
    # Project 3D axes to 2D
    axes = [
        (np.array([1, 0, 0]), (0, 0, 255), "X"),   # X - Red
        (np.array([0, 1, 0]), (0, 255, 0), "Y"),   # Y - Green  
        (np.array([0, 0, 1]), (255, 0, 0), "Z"),   # Z - Blue
    ]
    
    for axis, color, label in axes:
        # Rotate axis
        rotated = rot @ axis
        
        # Simple perspective projection
        scale = 1.0 / (1.0 + rotated[1] * 0.3)  # Y is depth
        px = int(x + rotated[0] * size * scale)
        py = int(y - rotated[2] * size * scale)  # Flip Z for screen coords
        
        # Draw axis line
        cv2.line(frame, (x, y), (px, py), color, 2)
        
        # Draw axis label
        cv2.putText(frame, label, (px + 5, py + 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    # Origin
    cv2.circle(frame, (x, y), 4, (255, 255, 255), -1)


def run_webcam_visualization(conn: GalaxyBudsConnection):
    """Run webcam visualization with head tracking overlay."""
    print("\nStarting webcam visualization...")
    print("Press 'Q' to quit\n")
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    # Set resolution to 1920x1080
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    # Get actual resolution
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Webcam resolution: {width}x{height}")
    
    last_keep_alive = time.time()
    fps_time = time.time()
    fps_count = 0
    fps = 0
    
    cv2.namedWindow("Head Tracking", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Head Tracking", 1920, 1080)
    
    try:
        while True:
            # Process Bluetooth
            conn.run_loop(0.005)
            
            # Keep alive
            now = time.time()
            if now - last_keep_alive >= 2.0:
                conn.send_keep_alive()
                last_keep_alive = now
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                break
            
            # Flip horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Get quaternion
            quat = conn.latest_quaternion
            
            # Draw overlays
            if quat:
                # Orientation indicator (top right)
                draw_orientation_indicator(frame, quat, width - 180, 180, 140)
                
                # 3D axes (bottom right)
                draw_3d_axes(frame, quat, width - 180, height - 150, 100)
                
                # Data panel (top left)
                draw_data_panel(frame, quat, 20, 20)
            else:
                cv2.putText(frame, "Waiting for sensor data...", (20, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            
            # FPS counter
            fps_count += 1
            if now - fps_time >= 1.0:
                fps = fps_count
                fps_count = 0
                fps_time = now
            
            cv2.putText(frame, f"FPS: {fps}", (width - 100, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            # Title
            cv2.putText(frame, "Galaxy Buds Head Tracking", (20, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
            
            # Display
            cv2.imshow("Head Tracking", frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        pass
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Webcam closed")
