"""Data logging module for saving sensor data to CSV."""

import time
import csv
import sys
from datetime import datetime
from pathlib import Path

from .connection import GalaxyBudsConnection
from .quaternion import Quaternion

def run_logging_mode(conn: GalaxyBudsConnection):
    """
    Logs sensor data to a CSV file.
    Format: Timestamp, Roll, Pitch, Yaw, qW, qX, qY, qZ
    """
    # Create filename with timestamp
    filename = f"head_tracking_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Headers
    headers = [
        "timestamp", 
        "roll_deg", "pitch_deg", "yaw_deg",
        "quat_w", "quat_x", "quat_y", "quat_z"
    ]
    
    print("\n" + "=" * 40)
    print("DATA LOGGING MODE")
    print("=" * 40)
    print(f"File: {filename}")
    print("Recording... Press Ctrl+C to stop.\n")
    
    start_time = time.time()
    last_ka = time.time()
    count = 0
    
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            while conn.connected:
                # Process events
                conn.run_loop(0.005)
                
                # Keep Alive (every 2s)
                now = time.time()
                if now - last_ka >= 2.0:
                    conn.send_keep_alive()
                    last_ka = now
                
                # Write data if available
                quat = conn.latest_quaternion
                if quat:
                    euler = quat.to_euler() # returns (r, p, y) in degrees
                    
                    # Relative timestamp
                    t = now - start_time
                    
                    writer.writerow([
                        f"{t:.4f}",
                        f"{euler[0]:.2f}", f"{euler[1]:.2f}", f"{euler[2]:.2f}",
                        f"{quat.w:.4f}", f"{quat.x:.4f}", f"{quat.y:.4f}", f"{quat.z:.4f}"
                    ])
                    
                    count += 1
                    
                    # Console feedback every 50 samples
                    if count % 50 == 0:
                        sys.stdout.write(f"\rCaptured {count} samples... (Last: R={euler[0]:.1f} P={euler[1]:.1f} Y={euler[2]:.1f})")
                        sys.stdout.flush()
                        
                else:
                    time.sleep(0.005)
                    
    except KeyboardInterrupt:
        print(f"\n\nLogging stopped. Saved {count} samples to {filename}")
    except Exception as e:
        print(f"\nError: {e}")
