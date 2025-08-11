#!/usr/bin/env python3
"""
Simple launcher for the Bunkr Album Downloader
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the interactive downloader."""
    script_path = Path(__file__).parent / "interactive_downloader.py"
    
    print("🚀 Starting Bunkr Album Downloader...")
    print()
    
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running downloader: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
