# Quick Start Guide

## 🚀 How to Run

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Install FFmpeg** (for video frame extraction)
3. **Run**: `python run.py`

## 🎯 Usage Modes

### AI Training Dataset (Recommended)
- Choose "Extract frames from videos" 
- Search for your topic (e.g., "nature", "street photography")
- Set number of albums (start with 5-10)
- Optionally filter files

### Photo Collection
- Choose "Download videos normally"
- Search or use URLs.txt file
- Set filtering preferences

## 🎬 Video Frame Extraction

When enabled, videos are processed to extract the best frames:
- Automatic quality analysis
- Smart frame selection for diversity
- Saves disk space (no large video files)
- Perfect for AI training datasets

## 📁 Output

Files are saved to `Downloads/Album Name (ID)/`
Video frames go to `video_name_frames/` subfolders

## ❓ Need Help?

- Check `session_log.txt` for errors
- Make sure FFmpeg is installed for video processing
- Use search terms like "nature", "photography", "art", etc.
- Start with small album counts (5-10) for testing
