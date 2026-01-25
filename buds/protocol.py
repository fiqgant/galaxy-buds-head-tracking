"""Protocol constants and enums for Galaxy Buds SPP communication."""

from enum import IntEnum


class MsgIds(IntEnum):
    """SPP message IDs."""
    SET_SPATIAL_AUDIO = 124
    SPATIAL_AUDIO_DATA = 194
    SPATIAL_AUDIO_CONTROL = 195


class SpatialAudioControl(IntEnum):
    """Control commands for spatial audio."""
    ATTACH = 0
    DETACH = 1
    ATTACH_SUCCESS = 2
    DETACH_SUCCESS = 3
    KEEP_ALIVE = 4


class SpatialAudioData(IntEnum):
    """Spatial audio data event types."""
    BUD_GRV = 32
    WEAR_ON = 33
    WEAR_OFF = 34


class MsgConstants(IntEnum):
    """Message framing constants."""
    SOM = 0xFD  # Start of Message
    EOM = 0xDD  # End of Message
