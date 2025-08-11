"""Module that facilitates the downloading of entire Bunkr albums.

This module provides features for managing progress, handling failed downloads, and
integrating with live task displays. Includes support for advanced video frame
extraction with memory-based processing.
"""

import asyncio
from asyncio import Semaphore

from helpers.config import MAX_WORKERS, AlbumInfo, DownloadInfo, SessionInfo
from helpers.crawlers.crawler_utils import get_download_info
from helpers.general_utils import fetch_page
from helpers.managers.live_manager import LiveManager
from helpers.video.video_utils import is_video_file
from helpers.video.frame_extractor import extract_frames_from_video
from helpers.video.memory_frame_extractor import extract_frames_smart

from .media_downloader import MediaDownloader


class AlbumDownloader:
    """Manage the downloading of entire Bunkr albums."""

    def __init__(
        self,
        session_info: SessionInfo,
        album_info: AlbumInfo,
        live_manager: LiveManager,
    ) -> None:
        """Initialize the AlbumDownloader instance."""
        self.session_info = session_info
        self.album_info = album_info
        self.live_manager = live_manager
        self.failed_downloads = []

    async def execute_item_download(
        self,
        item_page: str,
        current_task: int,
        semaphore: Semaphore,
    ) -> None:
        """Handle the download of an individual item in the album."""
        async with semaphore:
            task = self.live_manager.add_task(current_task=current_task)

            # Process the download of an item
            item_soup = await fetch_page(item_page)
            item_download_link, item_filename = await get_download_info(
                item_page, item_soup,
            )

            # Check if this is a video and if video frame extraction is enabled
            extract_frames = getattr(self.session_info.args, 'extract_frames', False)
            use_memory_extraction = getattr(self.session_info.args, 'memory_extraction', True)  # Default to new method
            
            if item_download_link:
                if extract_frames and is_video_file(item_filename):
                    # Extract frames instead of downloading the video
                    try:
                        self.live_manager.update_log(
                            "Smart frame extraction", 
                            f"Processing video: {item_filename}"
                        )
                        
                        # Choose extraction method
                        if use_memory_extraction:
                            # New memory-based extraction with advanced features
                            frame_data, saved_frames = await extract_frames_smart(
                                video_url=item_download_link,
                                output_dir=self.session_info.download_path,
                                video_filename=item_filename,
                                max_frames=getattr(self.session_info.args, 'max_frames_per_video', None),
                                save_to_disk=True,
                                min_quality_threshold=getattr(self.session_info.args, 'min_frame_quality', 0.3),
                                cand_mult=getattr(self.session_info.args, 'candidate_multiplier', 3.0)
                            )
                            frame_count = len(saved_frames)
                        else:
                            # Legacy extraction method
                            saved_frames = await extract_frames_from_video(
                                video_url=item_download_link,
                                output_dir=self.session_info.download_path,
                                video_filename=item_filename,
                                target_frames=getattr(self.session_info.args, 'frames_per_video', None)
                            )
                            frame_count = len(saved_frames)
                        
                        extraction_method = "memory-based" if use_memory_extraction else "disk-based"
                        self.live_manager.update_log(
                            "Frame extraction complete", 
                            f"Extracted {frame_count} frames from {item_filename} ({extraction_method})"
                        )
                        
                        # Mark task as complete
                        self.live_manager.update_task(task, completed=100, visible=False)
                        
                    except Exception as e:
                        self.live_manager.update_log(
                            "Frame extraction failed", 
                            f"Failed to extract frames from {item_filename}: {str(e)}"
                        )
                        self.live_manager.update_task(task, visible=False)
                else:
                    # Normal download (for non-videos or when frame extraction is disabled)
                    downloader = MediaDownloader(
                        session_info=self.session_info,
                        download_info=DownloadInfo(
                            download_link=item_download_link,
                            filename=item_filename,
                            task=task,
                        ),
                        live_manager=self.live_manager,
                    )

                    failed_download = await asyncio.to_thread(downloader.download)
                    if failed_download:
                        self.failed_downloads.append(failed_download)

    async def retry_failed_download(
        self,
        task: int,
        filename: str,
        download_link: str,
    ) -> None:
        """Handle failed downloads and retries them."""
        downloader = MediaDownloader(
            session_info=self.session_info,
            download_info=DownloadInfo(download_link, filename, task),
            live_manager=self.live_manager,
            retries=1,  # Retry once for failed downloads
        )
        # Run the synchronous download function in a separate thread
        await asyncio.to_thread(downloader.download)

    async def process_failed_downloads(self) -> None:
        """Process any failed downloads after the initial attempt."""
        for data in self.failed_downloads:
            await self.retry_failed_download(
                data["id"],
                data["filename"],
                data["download_link"],
            )
        self.failed_downloads.clear()

    async def download_album(self, max_workers: int = MAX_WORKERS) -> None:
        """Handle the album download."""
        num_tasks = len(self.album_info.item_pages)
        self.live_manager.add_overall_task(
            description=self.album_info.album_id,
            num_tasks=num_tasks,
        )

        # Create tasks for downloading each item in the album
        semaphore = asyncio.Semaphore(max_workers)
        tasks = [
            self.execute_item_download(item_page, current_task, semaphore)
            for current_task, item_page in enumerate(self.album_info.item_pages)
        ]
        await asyncio.gather(*tasks)

        # If there are failed downloads, process them after all downloads are complete
        if self.failed_downloads:
            await self.process_failed_downloads()
