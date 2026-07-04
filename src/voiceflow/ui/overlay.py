"""Floating AI Orb overlay using pywebview for HTML5 Canvas."""

import time
import math
import asyncio
from typing import TYPE_CHECKING
import threading

from voiceflow.core.events import AudioLevelChanged, StatusChanged, TranscriptReady, PipelineError
from voiceflow.core.logger import logger
from voiceflow.utils.window import get_active_window_info

if TYPE_CHECKING:
    from voiceflow.core.config import UIConfig
    from voiceflow.core.events import EventBus

_webview_window = None

def get_webview_window():
    global _webview_window
    if _webview_window is None:
        import webview
        import os
        import sys
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            current_dir = os.path.join(sys._MEIPASS, "voiceflow", "ui")
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
        html_path = os.path.join(current_dir, "assets", "orb.html")
        
        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            html = "<html><body>Orb HTML not found</body></html>"
            
        # Hide demo controls and make it draggable
        html = html.replace('<div class="demo">', '<div class="demo" style="display:none;">')
        html = html.replace('<label>Mic level', '<label style="display:none;">Mic level')
        html = html.replace('<body', '<body class="pywebview-drag"')
        
        _webview_window = webview.create_window(
            'VoiceOrb',
            html=html,
            transparent=True,
            frameless=True,
            on_top=True,
            width=300,
            height=320,
            x=100,
            y=100
        )
    return _webview_window


class FloatingOverlay:
    def __init__(self, config: 'UIConfig', event_bus: 'EventBus') -> None:
        self._config = config
        self._bus = event_bus
        self._window = None
        self._is_visible = False
        self._loop = asyncio.get_running_loop()

    async def start(self) -> None:
        """Subscribe to events."""
        if not self._config.show_orb:
            return

        self._window = _webview_window
        
        self._bus.subscribe(StatusChanged, self._on_status_changed)
        self._bus.subscribe(AudioLevelChanged, self._on_audio_level)
        self._bus.subscribe(TranscriptReady, self._on_transcript)
        logger.info("Floating Orb (WebView) started.")
        
        # Initially hide the window by moving it offscreen or hiding it
        if self._window:
            self._hide_window()
            self._loop.call_later(1.0, self._update_app_icon)

    async def stop(self) -> None:
        if not self._config.show_orb:
            return
        self._bus.unsubscribe(StatusChanged, self._on_status_changed)
        self._bus.unsubscribe(AudioLevelChanged, self._on_audio_level)
        self._bus.unsubscribe(TranscriptReady, self._on_transcript)
        if self._window:
            self._window.destroy()

    def _execute_js(self, script: str):
        if self._window:
            try:
                # evaluate_js must be thread-safe in pywebview, but just in case
                self._window.evaluate_js(script)
            except Exception as e:
                logger.error(f"Failed to execute JS: {e}")

    def _place_near_cursor(self):
        try:
            import win32gui
            x, y = win32gui.GetCursorPos()
            offset = 20
            if self._window:
                self._window.move(x + offset, y + offset)
                self._window.show()
                self._window.restore()
        except Exception as e:
            logger.error(f"Failed to place window: {e}")

    def _hide_window(self):
        if self._window:
            # move offscreen as pywebview hide() sometimes has issues on Windows
            self._window.move(-1000, -1000)

    def _update_app_icon(self):
        """Fetch active app icon and send to webview."""
        if self._config.show_app_icon and self._is_visible:
            name, img = get_active_window_info()
            if img:
                import io
                import base64
                img = img.resize((32, 32))
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                self._execute_js(f"if(typeof orb !== 'undefined') orb.setIcon('{b64}');")
            else:
                self._execute_js("if(typeof orb !== 'undefined') orb.setIcon(null);")
        if self._window:
            self._loop.call_later(1.0, self._update_app_icon)

    # ---------------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------------

    async def _on_status_changed(self, event: StatusChanged) -> None:
        if not self._window:
            return
            
        if event.status == "recording":
            self._is_visible = True
            # We must use a thread to call window methods if they block or have issues
            threading.Thread(target=self._place_near_cursor, daemon=True).start()
            self._execute_js("if(typeof orb !== 'undefined') orb.setState('listening');")
            
        elif event.status == "processing":
            self._execute_js("if(typeof orb !== 'undefined') orb.setState('thinking');")
            
        elif event.status == "refining":
            self._execute_js("if(typeof orb !== 'undefined') orb.setState('thinking');")
            
        elif event.status == "error":
            self._execute_js("if(typeof orb !== 'undefined') orb.setState('idle');")
            self._loop.call_later(2.0, self._hide_window)
            
        elif event.status == "idle":
            self._execute_js("if(typeof orb !== 'undefined') orb.setState('idle');")
            self._is_visible = False
            self._hide_window()

    async def _on_audio_level(self, event: AudioLevelChanged) -> None:
        if self._window and self._is_visible:
            # scale the level if necessary
            level = min(1.0, max(0.0, event.level))
            self._execute_js(f"if(typeof orb !== 'undefined') orb.setLevel({level});")

    async def _on_transcript(self, event: TranscriptReady) -> None:
        if self._window:
            self._execute_js("if(typeof orb !== 'undefined') orb.setState('speaking');")
            self._loop.call_later(1.5, self._hide_window)
