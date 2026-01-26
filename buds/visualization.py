"""Visualization - Academic Style with Webcam (Responsive Portrait)."""

import sys
import time
import numpy as np

from .connection import GalaxyBudsConnection
from .quaternion import Quaternion

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


def print_quaternion(quat: Quaternion):
    euler = quat.to_euler()
    sys.stdout.write(f"\r\033[KRoll={euler[0]:+6.1f}° Pitch={euler[1]:+6.1f}° Yaw={euler[2]:+6.1f}°")
    sys.stdout.flush()


def run_terminal_mode(conn: GalaxyBudsConnection):
    conn.on_quaternion = print_quaternion
    print("\nStreaming... Ctrl+C to stop.\n")
    last_ka = time.time()
    try:
        while conn.connected:
            conn.run_loop(0.05)
            if time.time() - last_ka >= 2.0:
                conn.send_keep_alive()
                last_ka = time.time()
    except KeyboardInterrupt:
        print("\n")


def create_circle(radius, n=80):
    t = np.linspace(0, 2*np.pi, n)
    return np.vstack([radius*np.cos(t), radius*np.sin(t), np.zeros(n)])


def run_visualization(conn: GalaxyBudsConnection):
    """
    Renders 3D gimbal visualization with webcam overlay.
    Uses matplotlib for plotting and OpenCV for video feed.
    """
    try:

        from mpl_toolkits.mplot3d import Axes3D
        import matplotlib.pyplot as plt
    except ImportError:
        return run_terminal_mode(conn)
    
    print("\nStarting visualization...\n")
    
    # Camera initialization
    cap = None
    width, height = 640, 480
    if HAS_OPENCV:

        cap = cv2.VideoCapture(1)
        if cap.isOpened():
            # Get actual webcam resolution
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if width == 0 or height == 0:
                width, height = 640, 480
        else:
            cap = None
    
    # Calculate aspect ratio
    aspect_ratio = width / height
    
    plt.style.use('dark_background')
    
    # Figure size 6x9 inches
    fig_w, fig_h = 6, 9
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor='#121212')
    
    # Title
    fig.text(0.5, 0.97, 'Quaternion Orientation Tracking', ha='center', 
             fontsize=13, color='#cccccc', fontweight='normal', style='italic')
    
    # 3D plot (main area)
    ax3d = fig.add_axes([0.05, 0.35, 0.9, 0.58], projection='3d', facecolor='#121212')
    ax3d.set_xlim([-1.4, 1.4])
    ax3d.set_ylim([-1.4, 1.4])
    ax3d.set_zlim([-1.4, 1.4])
    ax3d.set_xlabel('X', fontsize=9, color='#666666', labelpad=-8)
    ax3d.set_ylabel('Y', fontsize=9, color='#666666', labelpad=-8)
    ax3d.set_zlabel('Z', fontsize=9, color='#666666', labelpad=-8)
    ax3d.tick_params(colors='#444444', labelsize=7)
    ax3d.xaxis.pane.fill = False
    ax3d.yaxis.pane.fill = False
    ax3d.zaxis.pane.fill = False
    ax3d.xaxis.pane.set_edgecolor('#333333')
    ax3d.yaxis.pane.set_edgecolor('#333333')
    ax3d.zaxis.pane.set_edgecolor('#333333')
    ax3d.grid(True, alpha=0.15, color='#555555', linestyle='-', linewidth=0.5)
    
    # Data panel (bottom left)
    data_text = fig.text(0.08, 0.28, '', fontsize=10, color='#aaaaaa', 
                         fontfamily='monospace', verticalalignment='top',
                         linespacing=1.8)
    
    # Webcam placement logic to prefer aspect ratio
    # We want webcam width to be about 35% of figure width = 2.1 inches
    # Height will be determined by aspect ratio
    cam_w_inch = 2.0
    cam_h_inch = cam_w_inch / aspect_ratio
    
    # Convert to figure coordinates (0-1)
    cam_w_rel = cam_w_inch / fig_w
    cam_h_rel = cam_h_inch / fig_h
    
    # Position: Bottom right with margins
    cam_x = 0.95 - cam_w_rel
    cam_y = 0.03
    
    ax_cam = fig.add_axes([cam_x, cam_y, cam_w_rel, cam_h_rel])
    ax_cam.axis('off')
    
    # Placeholder
    cam_placeholder = np.zeros((height, width, 3), dtype=np.uint8)
    cam_placeholder[:] = [25, 25, 25]
    cam_img = ax_cam.imshow(cam_placeholder)
    
    # Gimbal rings
    ring_out = create_circle(1.15)
    ring_mid = create_circle(0.85)
    ring_in = create_circle(0.55)
    rot_x = np.array([[1,0,0],[0,0,-1],[0,1,0]])
    rot_y = np.array([[0,0,1],[0,1,0],[-1,0,0]])
    
    drawn = []
    last_ka = time.time()
    
    def update():
        nonlocal drawn, last_ka
        
        conn.run_loop(0.01)
        
        if time.time() - last_ka >= 2.0:
            conn.send_keep_alive()
            last_ka = time.time()
        
        # Webcam update
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                cam_img.set_data(frame)
        
        quat = conn.latest_quaternion
        if quat is None:
            return
        
        for obj in drawn:
            try: obj.remove()
            except: pass
        drawn.clear()
        
        rot = quat.to_rotation_matrix()
        euler = quat.to_euler()
        
        # Update data
        data_text.set_text(
            f'Euler Angles\n'
            f'  φ (Roll):   {euler[0]:+8.2f}°\n'
            f'  θ (Pitch):  {euler[1]:+8.2f}°\n'
            f'  ψ (Yaw):    {euler[2]:+8.2f}°\n\n'
            f'Quaternion q\n'
            f'  w: {quat.w:+.4f}\n'
            f'  x: {quat.x:+.4f}\n'
            f'  y: {quat.y:+.4f}\n'
            f'  z: {quat.z:+.4f}'
        )
        
        # Draw gimbal
        yr = np.radians(euler[2])
        yaw_m = np.array([[np.cos(yr),-np.sin(yr),0],[np.sin(yr),np.cos(yr),0],[0,0,1]])
        
        pr = np.radians(euler[1])
        pitch_m = np.array([[np.cos(pr),0,np.sin(pr)],[0,1,0],[-np.sin(pr),0,np.cos(pr)]])
        
        # Outer (yaw) - muted red
        r = yaw_m @ ring_out
        drawn.append(ax3d.plot(r[0], r[1], r[2], '#cc6666', lw=1.2, alpha=0.85)[0])
        
        # Middle (pitch) - muted cyan
        r = yaw_m @ pitch_m @ (rot_x @ ring_mid)
        drawn.append(ax3d.plot(r[0], r[1], r[2], '#66aaaa', lw=1.2, alpha=0.85)[0])
        
        # Inner (roll) - muted yellow
        r = rot @ (rot_y @ ring_in)
        drawn.append(ax3d.plot(r[0], r[1], r[2], '#aaaa66', lw=1.2, alpha=0.85)[0])
        
        # Coordinate frame
        colors = ['#aa4444', '#44aa44', '#4444aa']
        dirs = [[0.45,0,0], [0,0.7,0], [0,0,0.45]]
        for d, c in zip(dirs, colors):
            v = rot @ np.array(d)
            drawn.append(ax3d.quiver(0,0,0, v[0],v[1],v[2], color=c, arrow_length_ratio=0.12, lw=1))
        
        # Center
        drawn.append(ax3d.scatter([0],[0],[0], c='#888888', s=15))
        
        fig.canvas.draw_idle()
    
    def on_close(e):
        if cap: cap.release()
    
    fig.canvas.mpl_connect('close_event', on_close)
    
    timer = fig.canvas.new_timer(interval=45)
    timer.add_callback(update)
    timer.start()
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()
    if cap: cap.release()
