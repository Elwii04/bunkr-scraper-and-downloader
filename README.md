# Bunkr Album Downloader with AI Frame Extraction

> An intelligent Python downloader for Bunkr albums that can extract high-quality frames from videos for AI training datasets. Features interactive configuration and automated album discovery.

![Screenshot](https://github.com/Lysagxra/BunkrDownloader/blob/3bc786d91f2950fbc1df120b7ebbb6ff90e4e6fd/misc/DemoV2.gif)

## Features

- 🔍 **Automatic Album Discovery**: Search and find albums automatically
- 🎬 **Smart Video Processing**: Extract frames from videos for AI training instead of downloading large video files
- 📥 **Concurrent Downloads**: Download multiple files efficiently with progress tracking
- 🎯 **Interactive Configuration**: User-friendly setup without complex command-line arguments
- 📁 **Organized Storage**: Automatic directory structure and file organization
- 🛡️ **Robust Error Handling**: Retry mechanisms and offline server detection
- 📝 **Comprehensive Logging**: Track downloads and errors for troubleshooting

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install FFmpeg** (required for video frame extraction):
   - Windows: Download from https://ffmpeg.org/download.html
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

3. **Run the downloader**:
   ```bash
   python run.py
   ```
   or directly:
   ```bash
   python interactive_downloader.py
   ```

4. **Follow the prompts** to configure your download preferences

## Usage Modes

### Interactive Mode (Recommended)
The script will ask you simple questions:
- Do you want to download videos or extract frames?
- Search for specific content or browse defaults?
- How many albums to process?
- Any file filtering preferences?

### Traditional Batch Mode
Put album URLs in `URLs.txt` (one per line) and run:
```bash
python main.py
```

### Single Album Download
```bash
python downloader.py https://bunkr.cr/a/ALBUM_ID
```

## Video Frame Extraction

When frame extraction mode is enabled:
- Videos are automatically detected by file extension
- High-quality frames are extracted using intelligent selection:
  - Sharpness analysis (Laplacian variance)
  - Brightness filtering
  - Perceptual hashing for diversity
- Frames are saved as JPEGs in organized subfolders
- Original videos are NOT downloaded (saves massive disk space)

### Frame Selection Logic
- **≤30s videos**: 10 frames
- **30-60s videos**: 10-12 frames  
- **60-300s videos**: 12-20 frames
- **300-600s videos**: 20-30 frames
- **>600s videos**: 30-60 frames (capped)

## Dependencies

### Core Dependencies
- **Python 3.10+** - Required
- `requests` - HTTP requests and web scraping
- `beautifulsoup4` - HTML parsing
- `lxml` - Fast XML/HTML parsing
- `rich` - Beautiful progress bars and UI

### Video Frame Extraction
- `numpy` - Numerical computing for image analysis
- `Pillow` - Image processing and manipulation
- `scipy` - Scientific computing for advanced algorithms
- **FFmpeg/FFprobe** - Video processing (system dependency)

## Project Structure

```
BunkrDownloader/
├── run.py                     # 🚀 Simple launcher script
├── interactive_downloader.py  # 🎯 Main interactive downloader
├── downloader.py              # Single album downloader
├── main.py                    # Batch downloader (URLs.txt)
├── requirements.txt           # Python dependencies
├── Downloads/                 # Output directory (auto-created)
│   ├── Album Name (ID)/      # Individual albums
│   │   ├── image1.jpg        # Images and files
│   │   └── video_name_frames/ # Video frame folders
│   │       ├── frame_001.jpg
│   │       └── frame_002.jpg
├── helpers/                   # Core functionality
│   ├── video/                # 🎬 Video frame extraction
│   │   ├── frame_extractor.py
│   │   └── video_utils.py
│   ├── downloaders/          # 📥 Download management
│   ├── managers/             # 📊 Progress and logging
│   ├── crawlers/             # 🕷️ Page parsing
│   └── ... (other utilities)
├── URLs.txt                  # Batch input file (auto-created)
└── session_log.txt          # Error logging (auto-created)
```

## Examples

### Creating an AI Training Dataset
```bash
python interactive_downloader.py
```
Then follow the prompts:
- Choose "Extract frames from videos"
- Search for "nature photography"
- Process 20 albums
- Include only: "4k, hd, nature"
- Ignore: "watermark, preview"

### Downloading Photo Collections
```bash
python interactive_downloader.py
```
- Choose "Download videos normally" 
- Search for "street photography"
- Process 10 albums

### Batch Processing from File
Create `URLs.txt` with album URLs (one per line):
```
https://bunkr.cr/a/ABC123
https://bunkr.cr/a/DEF456
https://bunkr.cr/a/GHI789
```

Then run:
```bash
python main.py
```

### Single Album Download
```bash
python downloader.py https://bunkr.cr/a/ALBUM_ID
```

## Output Structure

```
Downloads/
├── Nature Photos (ABC123)/
│   ├── photo1.jpg
│   ├── photo2.png
│   └── video_sunset_frames/
│       ├── frame_001_t1500ms.jpg
│       ├── frame_002_t3200ms.jpg
│       └── frame_003_t4800ms.jpg
└── Street Photography (DEF456)/
    ├── street1.jpg
    └── street2.jpg
```

## Configuration Options

The interactive script will ask you about:

- **Video Handling**: Download normally or extract frames
- **Content Discovery**: Search with terms or browse from URLs.txt
- **Album Count**: How many albums to process (1-100)
- **File Filtering**: Include/exclude patterns (optional)

All video frame extraction parameters are optimized and hardcoded for best results.

## Troubleshooting

### Common Issues

1. **"ffmpeg not found"**: Install FFmpeg and add to PATH
2. **Import errors**: Run `pip install -r requirements.txt`
3. **No albums found**: Try different search terms or check network
4. **Download failures**: Check `session_log.txt` for details

### Performance Tips

- Use frame extraction mode for video-heavy content to save disk space
- Adjust concurrent workers in `helpers/config.py` if needed
- Use file filtering to avoid unwanted downloads

## Legal Notice

- Respect the website's terms of service and robots.txt
- Only download content you have permission to use
- Be mindful of bandwidth and server load
- This tool is for educational and personal use only

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

This feature is particularly useful when you want to skip files with certain extensions, such as `.zip` files. For instance:

```bash
python3 downloader.py https://bunkr.si/a/PUK068QE --ignore .zip
```

## Include List

The Include List is specified using the `--include` argument in the command line. This allows you to download a file from an album only if its filename contains at least one of the specified strings in the list. Items in the list should be separated by a space.

### Usage

```bash
python3 downloader.py <bunkr_album_url> --include <include_list>
```

### Example

```bash
python3 downloader.py https://bunkr.si/a/PUK068QE --include FullSizeRender
```

## Batch Download

To batch download from multiple URLs, you can use the `main.py` script. This script reads URLs from a file named `URLs.txt` and downloads each one using the media downloader.

### Usage

1. Create a file named `URLs.txt` in the root of your project, listing each URL on a new line.

- Example of `URLs.txt`:

```
https://bunkr.si/a/PUK068QE
https://bunkr.fi/f/gBrv5f8tAGlGW
https://bunkr.fi/a/kVYLh49Q
```

- Ensure that each URL is on its own line without any extra spaces.
- You can add as many URLs as you need, following the same format.

2. Run the batch download script:

```
python3 main.py
```

3. The downloaded files will be saved in the `Downloads` directory.

## Disable UI for Notebooks

When the script is executed in a notebook environment (such as Jupyter), excessive output may lead to performance issues or crashes.

### Usage

You can run the script with the `--disable-ui` argument to disable the progress bar and minimize log messages.

To disable the UI, use the following command:

```
python3 main.py --disable-ui
```

To download a single file or album without the UI, you can use this command:

```bash
python3 downloader.py <bunkr_url> --disable-ui
```

## Logging

The application logs any issues encountered during the download process in a file named `session_log.txt`. Check this file for any URLs that may have been blocked or had errors.
