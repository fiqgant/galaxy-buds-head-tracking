"""SPP Message encoder/decoder for Galaxy Buds protocol."""

import struct
from dataclasses import dataclass
from typing import Optional

from .protocol import MsgConstants
from .crc import crc16_ccitt


@dataclass
class SppMessage:
    """Represents a Galaxy Buds RFCOMM protocol message."""
    msg_id: int
    payload: bytes
    is_response: bool = False

    def encode(self) -> bytes:
        """Encode message to bytes for transmission."""
        size = 1 + len(self.payload) + 2
        header = size & 0x3FF
        if self.is_response:
            header |= 0x1000
        
        crc_data = bytes([self.msg_id]) + self.payload
        crc = crc16_ccitt(crc_data)
        
        packet = bytes([MsgConstants.SOM])
        packet += struct.pack('<H', header)
        packet += bytes([self.msg_id])
        packet += self.payload
        packet += struct.pack('<H', crc)
        packet += bytes([MsgConstants.EOM])
        
        return packet

    @staticmethod
    def decode(data: bytes) -> Optional['SppMessage']:
        """Decode bytes to SppMessage."""
        if len(data) < 6 or data[0] != MsgConstants.SOM:
            return None
        
        header = struct.unpack('<H', data[1:3])[0]
        is_response = bool(header & 0x1000)
        size = header & 0x3FF
        msg_id = data[3]
        
        payload_size = max(0, size - 3)
        payload = data[4:4 + payload_size]
        
        eom_pos = 4 + payload_size + 2
        if len(data) <= eom_pos or data[eom_pos] != MsgConstants.EOM:
            return None
        
        return SppMessage(msg_id=msg_id, payload=payload, is_response=is_response)
