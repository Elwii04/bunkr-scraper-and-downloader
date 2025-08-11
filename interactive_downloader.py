#!/usr/bin/env python3
"""
Interactive Bunkr Album Downloader with Video Frame Extraction

A user-friendly script that asks questions to configure downloads instead of
requiring command-line arguments. Supports both video downloads and frame extraction
for AI training datasets.
"""

import asyncio
import sys
import time
from pathlib import Path
from urllib.parse import quote
from typing import List, Set

import requests
from bs4 import BeautifulSoup

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.bunkr_utils import get_bunkr_status
from helpers.config import HEADERS
from downloader import initialize_managers, validate_and_download


class BunkrSearchScraper:
    """Simple scraper for finding Bunkr album URLs via search."""
    
    def __init__(self, 
                 base_url: str = "https://bunkr-albums.io",
                 album_domain: str = "https://bunkr.cr",
                 delay: float = 0.6):
        self.base_url = base_url
        self.album_domain = album_domain
        self.delay = delay
        
        # Create session with headers
        self.session = requests.Session()
        self.session.headers.update({
            **HEADERS,
            "Accept-Language": "en-US,en;q=0.9"
        })
    
    def build_search_url(self, query: str, page: int = 1) -> str:
        """Build search URL for given query and page."""
        q = quote(query)
        if page == 1:
            return f"{self.base_url}/?search={q}"
        return f"{self.base_url}/?search={q}&page={page}"
    
    def fetch_soup(self, url: str, timeout: int = 30) -> BeautifulSoup:
        """Fetch and parse HTML from URL."""
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    
    def normalize_album_url(self, href: str) -> str:
        """Normalize relative/absolute album URLs."""
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"{self.album_domain}{href}"
        return href
    
    def extract_album_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extract album URLs from search results page."""
        found_urls = []
        seen: Set[str] = set()
        
        # Robust selector: any anchor within <main> whose href contains '/a/'
        for anchor in soup.select("main a[href*='/a/']"):
            href = anchor.get("href")
            if not href:
                continue
                
            # Skip javascript: links
            if href.startswith("javascript:"):
                continue
                
            url = self.normalize_album_url(href)
            if "/a/" in url and url not in seen:
                seen.add(url)
                found_urls.append(url)
        
        return found_urls
    
    def scrape_search_results(self, 
                            query: str, 
                            max_pages: int = 50,
                            max_albums: int = None) -> List[str]:
        """Scrape album URLs from search results."""
        all_albums = []
        
        for page in range(1, max_pages + 1):
            url = self.build_search_url(query, page)
            print(f"   🔍 Searching page {page}...")
            
            try:
                soup = self.fetch_soup(url)
                albums = self.extract_album_urls(soup)
                
                if not albums:
                    print(f"   ℹ️  No more albums found on page {page}")
                    break
                
                all_albums.extend(albums)
                print(f"   ✅ Found {len(albums)} albums on page {page}")
                
                # Check if we've reached the maximum
                if max_albums and len(all_albums) >= max_albums:
                    all_albums = all_albums[:max_albums]
                    print(f"   🎯 Reached target of {max_albums} albums")
                    break
                
                # Delay between requests
                if page < max_pages:
                    time.sleep(self.delay)
                    
            except Exception as e:
                print(f"   ❌ Failed to search page {page}: {e}")
                continue
        
        return all_albums


class InteractiveBunkrDownloader:
    """Interactive downloader that asks user questions for configuration."""
    
    def __init__(self):
        self.config = {}
        
    def welcome_message(self):
        """Display welcome message and information."""
        print("=" * 60)
        print("🚀 Bunkr Album Downloader with Frame Extraction")
        print("=" * 60)
        print()
        print("This tool can:")
        print("  📥 Download images and files from Bunkr albums")
        print("  🎬 Extract frames from videos (for AI training)")
        print("  🔍 Search and automatically find albums")
        print()
    
    def ask_download_mode(self):
        """Ask user what to do with videos."""
        print("🎥 Video handling options:")
        print("  1. Download videos normally")
        print("  2. Extract frames from videos (recommended for AI training)")
        print()
        
        while True:
            choice = input("Choose video handling (1 or 2): ").strip()
            if choice == "1":
                self.config['extract_frames'] = False
                print("✅ Videos will be downloaded normally")
                break
            elif choice == "2":
                self.config['extract_frames'] = True
                print("✅ Frames will be extracted from videos")
                break
            else:
                print("❌ Please enter 1 or 2")
        print()
    
    def ask_search_or_browse(self):
        """Ask user if they want to search or browse."""
        print("🔍 Content discovery:")
        print("  1. Search for specific content")
        print("  2. Browse default/popular content")
        print()
        
        while True:
            choice = input("Choose discovery method (1 or 2): ").strip()
            if choice == "1":
                self.config['use_search'] = True
                search_term = input("Enter search term (e.g., 'nature photos'): ").strip()
                if search_term:
                    self.config['search_term'] = search_term
                    print(f"✅ Will search for: '{search_term}'")
                else:
                    print("❌ Search term cannot be empty")
                    continue
                break
            elif choice == "2":
                self.config['use_search'] = False
                self.config['search_term'] = ""  # Empty will browse default content
                print("✅ Will browse default/popular content")
                break
            else:
                print("❌ Please enter 1 or 2")
        print()
    
    def ask_album_count(self):
        """Ask how many albums to process."""
        print("📊 Number of albums to process:")
        while True:
            try:
                count = input("Enter number of albums (1-100, default 10): ").strip()
                if not count:
                    self.config['max_albums'] = 10
                    print("✅ Will process 10 albums (default)")
                    break
                
                count = int(count)
                if 1 <= count <= 100:
                    self.config['max_albums'] = count
                    print(f"✅ Will process {count} albums")
                    break
                else:
                    print("❌ Please enter a number between 1 and 100")
            except ValueError:
                print("❌ Please enter a valid number")
        print()
    
    def ask_file_filtering(self):
        """Ask about file filtering preferences."""
        print("📁 File filtering (optional):")
        print("Leave empty to download all files")
        
        # Include filter
        include = input("Only download files containing (comma-separated): ").strip()
        if include:
            self.config['include'] = [word.strip() for word in include.split(',')]
            print(f"✅ Will only download files containing: {', '.join(self.config['include'])}")
        else:
            self.config['include'] = None
        
        # Ignore filter
        ignore = input("Skip files containing (comma-separated): ").strip()
        if ignore:
            self.config['ignore'] = [word.strip() for word in ignore.split(',')]
            print(f"✅ Will skip files containing: {', '.join(self.config['ignore'])}")
        else:
            self.config['ignore'] = None
        print()
    
    def display_config_summary(self):
        """Show the user what will happen."""
        print("📋 Configuration Summary:")
        print("-" * 40)
        
        if self.config['use_search']:
            print(f"🔍 Search term: '{self.config['search_term']}'")
        else:
            print("🔍 Mode: Browse default content")
            
        print(f"📊 Albums to process: {self.config['max_albums']}")
        
        if self.config['extract_frames']:
            print("🎬 Videos: Extract frames (AI training mode)")
        else:
            print("🎬 Videos: Download normally")
            
        if self.config['include']:
            print(f"✅ Include only: {', '.join(self.config['include'])}")
        if self.config['ignore']:
            print(f"❌ Ignore: {', '.join(self.config['ignore'])}")
            
        print("-" * 40)
        print()
    
    def confirm_start(self):
        """Ask for final confirmation."""
        while True:
            confirm = input("Start download? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return True
            elif confirm in ['n', 'no']:
                print("❌ Download cancelled")
                return False
            else:
                print("❌ Please enter 'y' or 'n'")
    
    def configure_interactive(self):
        """Run the interactive configuration process."""
        self.welcome_message()
        self.ask_download_mode()
        self.ask_search_or_browse()
        self.ask_album_count()
        self.ask_file_filtering()
        self.display_config_summary()
        
        return self.confirm_start()
    
    def create_args_object(self):
        """Create an args-like object from the configuration."""
        class Args:
            def __init__(self, config):
                self.extract_frames = config['extract_frames']
                self.frames_per_video = None  # Use automatic calculation
                self.include = config['include']
                self.ignore = config['ignore']
                self.disable_ui = False
        
        return Args(self.config)
    
    async def run_download(self):
        """Execute the download process based on configuration."""
        try:
            print("🚀 Starting download process...")
            print()
            
            # Get album URLs
            if self.config['use_search'] and self.config['search_term']:
                print(f"🔍 Searching for: '{self.config['search_term']}'")
                scraper = BunkrSearchScraper(delay=0.6)
                album_urls = scraper.scrape_search_results(
                    query=self.config['search_term'],
                    max_pages=20,  # Reasonable default
                    max_albums=self.config['max_albums']
                )
            else:
                # For browse mode, we could implement browsing popular/recent albums
                # For now, show message that this mode needs URLs.txt
                print("📁 Browse mode: Please add album URLs to 'URLs.txt' file")
                print("   (One URL per line)")
                
                urls_file = Path("URLs.txt")
                if not urls_file.exists():
                    urls_file.write_text("# Add Bunkr album URLs here, one per line\n# Example: https://bunkr.cr/a/ALBUM_ID\n")
                    print(f"❌ Created empty {urls_file.name}. Please add URLs and run again.")
                    return
                
                album_urls = []
                for line in urls_file.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        album_urls.append(line)
                
                if not album_urls:
                    print("❌ No album URLs found in URLs.txt")
                    return
                
                # Limit to requested count
                album_urls = album_urls[:self.config['max_albums']]
            
            if not album_urls:
                print("❌ No albums found to download")
                return
            
            print(f"✅ Found {len(album_urls)} albums to process")
            print()
            
            # Initialize download system
            bunkr_status = get_bunkr_status()
            args = self.create_args_object()
            live_manager = initialize_managers(disable_ui=False)
            
            # Process each album
            try:
                with live_manager.live:
                    for i, album_url in enumerate(album_urls, 1):
                        print(f"📥 Processing album {i}/{len(album_urls)}: {album_url}")
                        
                        try:
                            await validate_and_download(
                                bunkr_status=bunkr_status,
                                url=album_url,
                                live_manager=live_manager,
                                args=args
                            )
                            
                            # Small delay between albums
                            if i < len(album_urls):
                                await asyncio.sleep(1.0)
                                
                        except Exception as e:
                            print(f"❌ Failed to download album {album_url}: {e}")
                            continue
                    
                    live_manager.stop()
                    
            except KeyboardInterrupt:
                print("\n⚠️  Download interrupted by user")
                return
            
            print("🎉 Download process completed!")
            
        except Exception as e:
            print(f"❌ Error during download: {e}")


def check_dependencies():
    """Check if required dependencies are available."""
    missing = []
    
    try:
        import numpy
        import PIL
        import scipy
    except ImportError as e:
        missing.append("Video frame extraction dependencies (numpy, PIL, scipy)")
    
    try:
        import requests
        import bs4
        import rich
    except ImportError:
        missing.append("Core dependencies (requests, beautifulsoup4, rich)")
    
    if missing:
        print("❌ Missing dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\n💡 Install with: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main entry point."""
    if not check_dependencies():
        sys.exit(1)
    
    downloader = InteractiveBunkrDownloader()
    
    try:
        if downloader.configure_interactive():
            asyncio.run(downloader.run_download())
        else:
            print("👋 Goodbye!")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
