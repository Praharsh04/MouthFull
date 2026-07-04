import asyncio
import httpx
import os
import time
import hashlib
from typing import Callable, Optional
from mouthfull.utils.logger import logger

class DownloadTask:
    def __init__(
        self,
        url: str,
        dest_path: str,
        expected_checksum: Optional[str] = None,
        on_progress: Optional[Callable[[dict], None]] = None
    ):
        self.url = url
        self.dest_path = dest_path
        self.expected_checksum = expected_checksum
        self.on_progress = on_progress
        
        self.status = "Preparing" # Preparing, Downloading, Verifying, Installing, Complete, Paused, Error
        self.total_size = 0
        self.downloaded = 0
        self.speed = 0
        self.eta = 0
        
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._cancel_flag = False
        self._task = None

    def pause(self):
        self.status = "Paused"
        self._pause_event.clear()
        self._notify()

    def resume(self):
        self.status = "Downloading"
        self._pause_event.set()
        self._notify()

    def cancel(self):
        self._cancel_flag = True
        self.status = "Cancelled"
        self._pause_event.set()
        self._notify()

    def _notify(self):
        if self.on_progress:
            self.on_progress({
                "status": self.status,
                "total_size": self.total_size,
                "downloaded": self.downloaded,
                "speed": self.speed,
                "eta": self.eta
            })

    async def run(self):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self._download_loop()
                if self._cancel_flag:
                    self._cleanup()
                    return False
                break
            except Exception as e:
                logger.error(f"Download error: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    self.status = "Error"
                    self._notify()
                    return False
                await asyncio.sleep(2)

        if self._cancel_flag:
            return False

        self.status = "Verifying"
        self._notify()
        
        if self.expected_checksum:
            valid = await self._verify_checksum()
            if not valid:
                self.status = "Error"
                self._notify()
                return False

        self.status = "Installing"
        self._notify()
        # In a real app we might extract or move files here
        await asyncio.sleep(1) 

        self.status = "Complete"
        self._notify()
        return True

    async def _download_loop(self):
        headers = {}
        file_mode = "wb"
        
        if os.path.exists(self.dest_path):
            self.downloaded = os.path.getsize(self.dest_path)
            headers["Range"] = f"bytes={self.downloaded}-"
            file_mode = "ab"
            
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
            async with client.stream("GET", self.url, headers=headers) as response:
                if response.status_code not in (200, 206):
                    raise Exception(f"HTTP {response.status_code}")
                
                if response.status_code == 200:
                    self.downloaded = 0
                    file_mode = "wb"
                
                content_length = response.headers.get("Content-Length")
                if content_length:
                    self.total_size = self.downloaded + int(content_length)
                
                self.status = "Downloading"
                self._notify()
                
                os.makedirs(os.path.dirname(self.dest_path), exist_ok=True)
                
                # Use standard synchronous file I/O in thread
                def _write(chunk):
                    with open(self.dest_path, file_mode) as f:
                        f.write(chunk)
                        
                # Wait for any previous partial write to finish and re-open mode as ab
                if file_mode == "wb":
                    open(self.dest_path, "wb").close()
                    file_mode = "ab"

                f = open(self.dest_path, file_mode)
                try:
                    chunk_size = 1024 * 64
                    last_time = time.time()
                    downloaded_since_last = 0
                    
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        if self._cancel_flag:
                            break
                            
                        await self._pause_event.wait()
                        
                        f.write(chunk)
                        self.downloaded += len(chunk)
                        downloaded_since_last += len(chunk)
                        
                        now = time.time()
                        if now - last_time >= 0.5:
                            self.speed = downloaded_since_last / (now - last_time)
                            if self.speed > 0:
                                remaining = self.total_size - self.downloaded
                                self.eta = remaining / self.speed
                            self._notify()
                            last_time = now
                            downloaded_since_last = 0
                finally:
                    f.close()

    async def _verify_checksum(self):
        def _hash():
            h = hashlib.sha256()
            with open(self.dest_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            return h.hexdigest()
        
        actual = await asyncio.to_thread(_hash)
        return actual == self.expected_checksum

    def _cleanup(self):
        try:
            if os.path.exists(self.dest_path):
                os.remove(self.dest_path)
        except:
            pass

class DownloadManager:
    def __init__(self):
        self.tasks = {}

    def start_download(self, model_id, url, dest_path, checksum, on_progress):
        if model_id in self.tasks:
            return
            
        task = DownloadTask(url, dest_path, checksum, on_progress)
        self.tasks[model_id] = task
        asyncio.create_task(self._run_task(model_id, task))

    async def _run_task(self, model_id, task):
        await task.run()
        if model_id in self.tasks and self.tasks[model_id].status in ["Complete", "Error", "Cancelled"]:
            del self.tasks[model_id]

    def pause(self, model_id):
        if model_id in self.tasks:
            self.tasks[model_id].pause()

    def resume(self, model_id):
        if model_id in self.tasks:
            self.tasks[model_id].resume()

    def cancel(self, model_id):
        if model_id in self.tasks:
            self.tasks[model_id].cancel()
            
manager = DownloadManager()
