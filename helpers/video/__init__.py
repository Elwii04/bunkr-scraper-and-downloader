"""Video processing utilities for the BunkrDownloader.

This module provides comprehensive video frame extraction capabilities with:
- In-memory processing for large RAM systems (64GB+)
- Smart frame selection based on quality and diversity
- Static video detection to avoid duplicate frames
- Optimized frame count scheduling for different video lengths
- Advanced blur and quality detection algorithms
"""

from .frame_extractor import extract_frames_from_video, FrameCandidate
from .memory_frame_extractor import (
    extract_frames_to_memory_stream,
    extract_frames_smart,
    save_memory_frames_to_disk,
    compute_smart_frame_count
)
from .video_utils import (
    is_video_file,
    get_video_stem,
    sanitize_video_folder_name,
    estimate_frame_count_by_duration
)

__all__ = [
    # Original frame extraction
    "extract_frames_from_video",
    "FrameCandidate",
    
    # New memory-based extraction
    "extract_frames_to_memory_stream",
    "extract_frames_smart", 
    "save_memory_frames_to_disk",
    "compute_smart_frame_count",
    
    # Utility functions
    "is_video_file",
    "get_video_stem", 
    "sanitize_video_folder_name",
    "estimate_frame_count_by_duration"
]
