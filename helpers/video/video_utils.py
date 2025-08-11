"""Video detection and utility functions."""

import re
from pathlib import Path
from typing import Optional

# Common video file extensions
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', 
    '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'
}

def is_video_file(filename: str) -> bool:
    """Check if a filename has a video extension."""
    if not filename:
        return False
    
    extension = Path(filename).suffix.lower()
    return extension in VIDEO_EXTENSIONS

def get_video_stem(filename: str) -> str:
    """Get the filename without extension for video files."""
    return Path(filename).stem

def sanitize_video_folder_name(name: str) -> str:
    """Sanitize a folder name for video frame output."""
    # Remove invalid characters for folder names
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Limit length
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    return sanitized

def estimate_frame_count_by_duration(duration: Optional[float], user_top: Optional[int] = None) -> int:
    """
    Estimate number of frames to extract based on video duration.
    Updated to match your requirements: 30s->5, 60s->10, 120s->15, 300s->20, 600s->30
    """
    if user_top is not None:
        return int(user_top)
    if duration is None:
        return 15  # Updated fallback
    
    d = duration
    
    # Handle very short videos
    if d <= 10:
        return max(1, int(d / 3))
    elif d <= 30:
        # 10-30s: scale to 5 frames at 30s
        return int(round(3 + (d - 10) / 20 * 2))
    elif d <= 60:
        # 30-60s: 5 -> 10 frames
        return int(round(5 + (d - 30) / 30 * 5))
    elif d <= 120:
        # 60-120s: 10 -> 15 frames
        return int(round(10 + (d - 60) / 60 * 5))
    elif d <= 300:
        # 120-300s: 15 -> 20 frames
        return int(round(15 + (d - 120) / 180 * 5))
    elif d <= 600:
        # 300-600s: 20 -> 30 frames
        return int(round(20 + (d - 300) / 300 * 10))
    else:
        # Beyond 10min: logarithmic scaling for diminishing returns
        import math
        extra_time = d - 600
        extra_frames = int(8 * math.log10(1 + extra_time / 300))
        return int(min(45, 30 + extra_frames))
