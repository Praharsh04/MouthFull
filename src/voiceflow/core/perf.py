import asyncio
import psutil
from typing import Optional

from voiceflow.core.events import EventBus, PerformanceMetrics
from voiceflow.core.logger import logger

class PerformanceCollector:
    """Polls system metrics and emits PerformanceMetrics events."""
    
    def __init__(self, bus: EventBus, interval: float = 1.0):
        self.bus = bus
        self.interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Initialize psutil
        psutil.cpu_percent()
        
    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("PerformanceCollector started")
        
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PerformanceCollector stopped")
        
    async def _poll_loop(self):
        while self._running:
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                
                gpu = None
                try:
                    # Very basic GPU check using pynvml if available
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu = float(util.gpu)
                except Exception:
                    pass
                
                await self.bus.emit(PerformanceMetrics(cpu_percent=cpu, ram_percent=ram, gpu_percent=gpu))
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                
            await asyncio.sleep(self.interval)
