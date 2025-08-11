"""Frame extraction functionality refactored from stream_keyframes.py."""

import asyncio
import io
import math
import os
import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from PIL import Image

from .video_utils import sanitize_video_folder_name


def run_ffprobe_duration(url_or_path: str) -> Optional[float]:
    """Return duration in seconds (float) using ffprobe. None if unknown/fails."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1",
        url_or_path
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        s = out.decode("utf-8", errors="ignore").strip()
        if s:
            return float(s)
    except Exception:
        return None
    return None


def sample_candidate_timestamps(duration: Optional[float], target_frames: int, multiplier: float, max_candidates: int) -> List[float]:
    """Uniformly sample candidate timestamps across the video. Avoid very start/end edges."""
    n_cand = int(min(max_candidates, max(target_frames * multiplier, target_frames)))
    if duration is None or duration <= 0:
        # without duration, sample pseudo-timestamps (we'll try seek anyway)
        return [i for i in range(n_cand)]
    # Avoid first/last 1% to skip black/intro/outro frames
    start = 0.01 * duration
    end = 0.99 * duration
    if n_cand <= 1:
        return [0.5 * duration]
    step = (end - start) / (n_cand - 1)
    return [start + i * step for i in range(n_cand)]


def ffmpeg_grab_frame_at(url_or_path: str, t: float, jpeg_quality: int = 2, headers: Optional[List[str]] = None) -> Optional[bytes]:
    """Return a single JPEG frame as bytes by seeking to t seconds on the input URL/path."""
    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",
        "-nostdin",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_at_eof", "1",
        "-rw_timeout", "60000000",  # 60s in microseconds
        "-ss", f"{max(0.0, t):.3f}",
    ]
    if headers:
        for h in headers:
            cmd += ["-headers", h]
    cmd += [
        "-http_seekable", "1",
        "-i", url_or_path,
        "-frames:v", "1",
        "-f", "image2pipe",
        "-q:v", str(jpeg_quality),
        "pipe:1",
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return out
    except subprocess.CalledProcessError:
        return None


def image_laplacian_var(img: Image.Image) -> float:
    """Return variance of Laplacian as a sharpness measure."""
    # convert to grayscale float32
    g = np.asarray(img.convert("L"), dtype=np.float32)
    # simple Laplacian kernel
    kernel = np.array([[0, 1, 0],
                       [1, -4, 1],
                       [0, 1, 0]], dtype=np.float32)
    # convolution
    from scipy.signal import convolve2d
    lap = convolve2d(g, kernel, mode="same", boundary="symm")
    return float(lap.var())


def image_gradient_magnitude(img: Image.Image) -> float:
    """Calculate gradient magnitude for additional sharpness measurement."""
    from scipy.signal import convolve2d
    g = np.asarray(img.convert("L"), dtype=np.float32)
    
    # Sobel kernels
    sobel_x = np.array([[-1, 0, 1],
                        [-2, 0, 2],
                        [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[-1, -2, -1],
                        [0, 0, 0],
                        [1, 2, 1]], dtype=np.float32)
    
    grad_x = convolve2d(g, sobel_x, mode="same", boundary="symm")
    grad_y = convolve2d(g, sobel_y, mode="same", boundary="symm")
    
    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    return float(magnitude.mean())


def compute_composite_quality_score(img: Image.Image) -> float:
    """
    Compute a composite quality score combining sharpness metrics.
    Higher score = better quality.
    """
    try:
        laplacian_var = image_laplacian_var(img)
        gradient_mag = image_gradient_magnitude(img)
        
        # Normalize and combine (weights can be tuned)
        # Laplacian variance typically ranges 0-10000+, gradient magnitude 0-50+
        normalized_laplacian = min(laplacian_var / 1000.0, 10.0)  # Cap at 10
        normalized_gradient = min(gradient_mag / 10.0, 5.0)       # Cap at 5
        
        # Weighted combination favoring gradient magnitude for blur detection
        composite_score = 0.4 * normalized_laplacian + 0.6 * normalized_gradient
        return composite_score
    except Exception:
        return 0.0


def image_brightness(img: Image.Image) -> float:
    """Mean luminance in [0,1]."""
    g = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    return float(g.mean())


def phash(img: Image.Image, hash_size: int = 8, highfreq_factor: int = 4) -> np.ndarray:
    """Perceptual hash (pHash). Based on DCT of a resized image."""
    import scipy.fft
    # size for DCT
    size = hash_size * highfreq_factor
    img = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = np.asarray(img, dtype=np.float32)
    dct = scipy.fft.dct(scipy.fft.dct(pixels, axis=0, norm='ortho'), axis=1, norm='ortho')
    # take top-left block (low frequencies)
    dctlow = dct[:hash_size, :hash_size]
    med = np.median(dctlow[1:, 1:])  # exclude DC
    ph = dctlow > med
    return ph.flatten()


def hamming(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))


@dataclass
class FrameCandidate:
    t: float
    jpeg: bytes
    sharpness: float  # Legacy Laplacian variance
    quality_score: float  # New composite quality score
    brightness: float
    hash: np.ndarray


def select_diverse_topk(cands: List[FrameCandidate], k: int, min_hamm: int, bright_min: float, bright_max: float, min_quality_threshold: float = 0.3) -> List[FrameCandidate]:
    """
    Advanced frame selection that prioritizes quality and diversity.
    
    IMPORTANT: k is the MAXIMUM allowed frames, not a target.
    The function will return FEWER frames if:
    - Insufficient quality frames available
    - Video is too static (similar frames)
    - Not enough diverse frames found
    
    Args:
        cands: List of candidate frames
        k: MAXIMUM number of frames to select (may return fewer)
        min_hamm: Minimum Hamming distance for diversity
        bright_min/bright_max: Brightness range filter
        min_quality_threshold: Minimum quality score to accept a frame
    
    Returns:
        List of selected diverse, high-quality frames (≤ k frames)
    """
    if not cands:
        return []
    
    # First pass: filter by brightness and minimum quality
    quality_filtered = [c for c in cands if bright_min <= c.brightness <= bright_max and c.quality_score >= min_quality_threshold]
    
    # If no frames meet quality threshold, be more lenient but still maintain standards
    if not quality_filtered:
        # Relax quality threshold by 50% but keep brightness constraints
        relaxed_threshold = min_quality_threshold * 0.5
        quality_filtered = [c for c in cands if bright_min <= c.brightness <= bright_max and c.quality_score >= relaxed_threshold]
        
        # If still no frames, take brightness-filtered frames only
        if not quality_filtered:
            quality_filtered = [c for c in cands if bright_min <= c.brightness <= bright_max]
            
            # Last resort: take any frames but limit to 1-2 for very poor quality videos
            if not quality_filtered:
                quality_filtered = cands[:min(2, len(cands), k)]
    
    # Sort by composite quality score (best first)
    quality_filtered.sort(key=lambda c: c.quality_score, reverse=True)
    
    # Static video detection: check if video has minimal variation
    if len(quality_filtered) >= 3:
        # Sample top frames to check for static content
        sample_size = min(8, len(quality_filtered))
        top_frames = quality_filtered[:sample_size]
        
        total_distance = 0
        pairs = 0
        for i in range(len(top_frames)):
            for j in range(i + 1, len(top_frames)):
                total_distance += hamming(top_frames[i].hash, top_frames[j].hash)
                pairs += 1
        
        avg_distance = total_distance / pairs if pairs > 0 else 0
        
        # If average similarity is very high (low Hamming distance), it's likely static
        static_threshold = min_hamm * 0.4  # 40% of minimum diversity requirement
        
        if avg_distance < static_threshold:
            # Static video detected - return only the single best frame
            return quality_filtered[:1]
    
    # Dynamic selection with strict quality and diversity requirements
    chosen: List[FrameCandidate] = []
    
    # Always include the best quality frame
    if quality_filtered:
        chosen.append(quality_filtered[0])
    
    # Select additional frames with diversity constraints
    for candidate in quality_filtered[1:]:
        if len(chosen) >= k:
            break
            
        # Check if this frame is sufficiently different from all chosen frames
        is_diverse = True
        min_distance_to_chosen = float('inf')
        
        for chosen_frame in chosen:
            distance = hamming(candidate.hash, chosen_frame.hash)
            min_distance_to_chosen = min(min_distance_to_chosen, distance)
            
            if distance < min_hamm:
                is_diverse = False
                break
        
        if is_diverse:
            chosen.append(candidate)
    
    # Conservative approach: if we have very few diverse frames relative to maximum,
    # it might indicate a repetitive/static video - be more restrictive
    diversity_ratio = len(chosen) / k if k > 0 else 0
    
    if diversity_ratio < 0.3 and len(chosen) > 2:
        # If we found very few diverse frames relative to maximum allowed,
        # keep only the best ones to avoid near-duplicates
        chosen = chosen[:max(1, len(chosen) // 2)]
    
    return chosen


def compute_max_frames_by_schedule(duration: Optional[float], user_max: Optional[int]) -> int:
    """
    Non-linear maximum frame count schedule optimized for your requirements:
    30s -> max 5, 60s -> max 10, 120s -> max 15, 300s -> max 20, 600s -> max 30
    
    These are MAXIMUM allowed frames - the system will extract fewer if:
    - Not enough diverse frames found (too similar)
    - Quality threshold not met (too blurry/dark)
    - Static video detected (minimal variation)
    
    Uses logarithmic scaling for better frame distribution on longer videos.
    """
    if user_max is not None:
        return int(user_max)
    if duration is None:
        return 15  # fallback
    
    d = duration
    
    # Handle very short videos
    if d <= 10:
        return 3
    elif d <= 30:
        # 10-30s: 3 -> 5 frames
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
        # beyond 10min: logarithmic scaling, capped at 50
        # This gives diminishing returns for very long videos
        extra_time = d - 600
        extra_frames = int(10 * math.log10(1 + extra_time / 600))
        return int(min(50, 30 + extra_frames))


async def extract_frames_from_video(
    video_url: str,
    output_dir: str,
    video_filename: str,
    target_frames: Optional[int] = None,
    cand_mult: float = 4.0,
    cand_max: int = 200,
    min_hamm: int = 12,
    bright_min: float = 0.08,
    bright_max: float = 0.98,
    jpeg_quality: int = 2,
    headers: Optional[List[str]] = None,
    prefix: str = "frame"
) -> List[str]:
    """
    Extract frames from a video URL and save them to disk.
    Returns list of saved frame file paths.
    """
    # Check if ffmpeg/ffprobe are available
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg/ffprobe not found in PATH")
    
    # Create a subfolder for this video's frames
    video_stem = sanitize_video_folder_name(Path(video_filename).stem)
    frames_dir = Path(output_dir) / f"video_{video_stem}_frames"
    frames_dir.mkdir(exist_ok=True)
    
    # Get video duration
    duration = run_ffprobe_duration(video_url)
    
    # Determine maximum allowed frame count
    max_frames = compute_max_frames_by_schedule(duration, target_frames)
    
    # Sample candidate timestamps (use more candidates than max to have better selection)
    cand_ts = sample_candidate_timestamps(
        duration, 
        target_frames=max_frames, 
        multiplier=cand_mult, 
        max_candidates=cand_max
    )
    
    # Extract candidate frames
    candidates: List[FrameCandidate] = []
    for t in cand_ts:
        jpeg = ffmpeg_grab_frame_at(video_url, t, jpeg_quality=jpeg_quality, headers=headers)
        if not jpeg:
            continue
        try:
            img = Image.open(io.BytesIO(jpeg))
            img.load()
        except Exception:
            continue
        try:
            sharp = image_laplacian_var(img)  # Keep for backward compatibility
            quality_score = compute_composite_quality_score(img)  # New quality metric
            bright = image_brightness(img)
            ph = phash(img)
            candidates.append(FrameCandidate(
                t=float(t), 
                jpeg=jpeg, 
                sharpness=sharp, 
                quality_score=quality_score,
                brightness=bright, 
                hash=ph
            ))
        except Exception:
            continue
    
    # Select diverse frames (up to max_frames, but may be fewer if quality/diversity insufficient)
    selected = select_diverse_topk(
        candidates, 
        k=max_frames, 
        min_hamm=min_hamm, 
        bright_min=bright_min, 
        bright_max=bright_max
    )
    
    # Save frames and collect paths
    saved_paths = []
    for i, c in enumerate(selected, 1):
        ts_ms = int(round(c.t * 1000))
        frame_filename = f"{prefix}_{i:03d}_t{ts_ms}ms.jpg"
        frame_path = frames_dir / frame_filename
        
        with open(frame_path, "wb") as f:
            f.write(c.jpeg)
        saved_paths.append(str(frame_path))
    
    return saved_paths
