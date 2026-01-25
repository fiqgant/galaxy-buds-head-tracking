"""Quaternion class for head orientation."""

import struct
from dataclasses import dataclass
from typing import Optional
import numpy as np

from .protocol import SpatialAudioData


@dataclass
class Quaternion:
    """
    Unit Quaternion representing 3D orientation.
    Structure: w (scalar) + xi + yj + zk (vector).
    """
    x: float
    y: float
    z: float
    w: float
    
    def to_euler(self) -> tuple:
        """Convert quaternion to Euler angles (roll, pitch, yaw) in degrees."""
        sinr_cosp = 2 * (self.w * self.x + self.y * self.z)
        cosr_cosp = 1 - 2 * (self.x * self.x + self.y * self.y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)
        
        sinp = 2 * (self.w * self.y - self.z * self.x)
        pitch = np.arcsin(np.clip(sinp, -1, 1))
        
        siny_cosp = 2 * (self.w * self.z + self.x * self.y)
        cosy_cosp = 1 - 2 * (self.y * self.y + self.z * self.z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)
        
        return (np.degrees(roll), np.degrees(pitch), np.degrees(yaw))
    
    def to_rotation_matrix(self) -> np.ndarray:
        """
        Converts quaternion to 3x3 rotation matrix.
        Used for coordinate frame transformation.
        """
        w, x, y, z = self.w, self.x, self.y, self.z
        return np.array([
            [1 - 2*y*y - 2*z*z, 2*x*y - 2*z*w, 2*x*z + 2*y*w],
            [2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
            [2*x*z - 2*y*w, 2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y]
        ])


def parse_grv_data(payload: bytes) -> Optional[Quaternion]:
    """
    Decodes 16-byte payload into Quaternion.
    Format: 4x float32 (Little Endian).
    """
    if len(payload) < 9 or payload[0] != SpatialAudioData.BUD_GRV:
        return None
    
    data = payload[1:]
    values = []
    for i in range(4):
        short_val = struct.unpack('<h', data[i*2:i*2+2])[0]
        values.append(short_val / 10000.0)
    
    return Quaternion(x=values[0], y=values[1], z=values[2], w=values[3])
