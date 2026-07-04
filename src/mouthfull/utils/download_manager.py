import time
import asyncio
from typing import Any
from tqdm import tqdm
from mouthfull.utils.logger import logger
from mouthfull.utils.events import EventBus, ModelDownloadProgress, ModelDownloadStatus

class DownloadManager:
    """Manages active model downloads, supporting pause, resume, and cancel via a global state and custom tqdm."""
    _instance = None
    
    def __init__(self, event_bus: EventBus, loop=None):
        self.bus = event_bus
        self.loop = loop
        self.active_tasks = {} # model_id -> dict of state
        DownloadManager._instance = self

    @classmethod
    def get_instance(cls):
        return cls._instance

    def start_download(self, model_id: str, name: str, download_func: callable):
        if model_id in self.active_tasks:
            logger.warning(f"Download for {model_id} already active.")
            return

        state = {
            "paused": False,
            "cancelled": False,
            "model_id": model_id,
            "name": name,
            "current_file": "",
            "total_size": 0,
            "downloaded": 0,
            "last_time": time.time(),
            "last_size": 0,
            "stage": "Preparing"
        }
        self.active_tasks[model_id] = state

        async def _run():
            try:
                await self.bus.emit(ModelDownloadStatus(model_id, "downloading"))
                # Run the blocking download function in a thread
                await asyncio.to_thread(download_func, model_id)
                if state["cancelled"]:
                    return
                await self.bus.emit(ModelDownloadStatus(model_id, "installed"))
            except Exception as e:
                if state["cancelled"]:
                    await self.bus.emit(ModelDownloadStatus(model_id, "cancelled"))
                else:
                    logger.error(f"Download failed for {model_id}: {e}")
                    await self.bus.emit(ModelDownloadStatus(model_id, "error", str(e)))
            finally:
                if model_id in self.active_tasks:
                    del self.active_tasks[model_id]

        if self.loop:
            asyncio.run_coroutine_threadsafe(_run(), self.loop)
        else:
            asyncio.create_task(_run())

    async def pause(self, model_id: str):
        if model_id in self.active_tasks:
            self.active_tasks[model_id]["paused"] = True
            await self.bus.emit(ModelDownloadStatus(model_id, "paused"))

    async def resume(self, model_id: str):
        if model_id in self.active_tasks:
            self.active_tasks[model_id]["paused"] = False
            await self.bus.emit(ModelDownloadStatus(model_id, "downloading"))

    async def cancel(self, model_id: str):
        if model_id in self.active_tasks:
            self.active_tasks[model_id]["cancelled"] = True
            await self.bus.emit(ModelDownloadStatus(model_id, "cancelled"))


class EventBusTqdm(tqdm):
    """Custom tqdm class that intercepts progress updates and emits them via EventBus, and supports pausing/cancelling."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dm = DownloadManager.get_instance()
        # Try to figure out which model we are downloading
        # For simplicity, if there's only one active download, we map to it.
        # A more robust way is to pass model_id via kwargs if possible, but huggingface_hub creates tqdm internally.
        self.model_id = None
        if self.dm and len(self.dm.active_tasks) == 1:
            self.model_id = list(self.dm.active_tasks.keys())[0]

    def update(self, n=1):
        super().update(n)
        if not self.dm or not self.model_id:
            return

        state = self.dm.active_tasks.get(self.model_id)
        if not state:
            return

        # Check for cancel
        if state["cancelled"]:
            raise Exception("Download Cancelled")

        # Check for pause
        while state["paused"]:
            if state["cancelled"]:
                raise Exception("Download Cancelled")
            time.sleep(0.5)

        # Emit progress
        now = time.time()
        if now - state["last_time"] > 0.2 or self.n == self.total:
            diff_time = now - state["last_time"]
            diff_size = self.n - state["last_size"]
            speed_mbps = (diff_size / diff_time) / (1024 * 1024) if diff_time > 0 else 0
            
            state["last_time"] = now
            state["last_size"] = self.n
            
            percentage = (self.n / self.total * 100) if self.total else 0
            rem_bytes = max(0, (self.total or 0) - self.n)
            eta = (rem_bytes / (speed_mbps * 1024 * 1024)) if speed_mbps > 0 else 0

            # Fire and forget emit to bus from a sync context
            # We must use run_coroutine_threadsafe
            loop = self.dm.loop if self.dm else None
            if not loop:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    pass
            
            if loop:
                asyncio.run_coroutine_threadsafe(
                    self.dm.bus.emit(ModelDownloadProgress(
                        model_id=self.model_id,
                        percentage=percentage,
                        speed_mbps=speed_mbps,
                        remaining_size_mb=rem_bytes / (1024 * 1024),
                        eta_sec=eta,
                        stage="Downloading",
                        name=state["name"]
                    )),
                    loop
                )

# Patch huggingface_hub's tqdm
try:
    import huggingface_hub.utils._tqdm as hf_tqdm
    hf_tqdm.tqdm = EventBusTqdm
except ImportError:
    pass
