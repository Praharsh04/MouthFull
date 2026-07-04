import asyncio
import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal

from voiceflow.core.events import EventBus
from voiceflow.core.events import (
    StatusChanged, 
    AudioLevelChanged, 
    TranscriptReady, 
    RefinedTextReady,
    NotificationEvent,
    PipelineError
)


class UIBridge(QObject):
    """
    Acts as the thread-safe translator between the async EventBus (backend)
    and the PySide6 MainWindow (frontend).
    """

    # Signals to safely trigger UI updates on the main Qt thread
    backend_status_changed = Signal(str)
    audio_level_changed = Signal(float)
    transcript_ready = Signal(str, str, str) # text, kind, timestamp
    notification_requested = Signal(str, str, str) # title, msg, kind
    log_entry_received = Signal(dict)
    
    perf_metric_received = Signal(str, float)
    pipeline_stats_updated = Signal(dict)
    latency_breakdown_updated = Signal(dict)

    def __init__(self, main_window, event_bus: EventBus, loop: asyncio.AbstractEventLoop, app):
        super().__init__()
        self.window = main_window
        self.bus = event_bus
        self.loop = loop
        self.app = app

        # ---------------------------------------------------------
        # 1. Wire PySide6 Signals to UI Methods
        # ---------------------------------------------------------
        self.backend_status_changed.connect(self._on_backend_status_changed)
        self.audio_level_changed.connect(self.window.dashboard.update_audio_level)
        self.audio_level_changed.connect(self.window.orb.update_audio_level)
        self.transcript_ready.connect(self.window.dashboard.add_activity_entry)
        self.notification_requested.connect(self._on_notification)
        
        self.perf_metric_received.connect(self.window.performance_page.update_metric)
        self.pipeline_stats_updated.connect(self.window.performance_page.update_pipeline_stats)
        self.latency_breakdown_updated.connect(self.window.performance_page.update_latency_breakdown)
        self.window.performance_page.on_reset_stats_clicked.connect(self._reset_perf_stats)
        
        self._latencies = {"capture": 0, "stt": 0, "llm": 0, "inject": 0}
        self._requests = 0
        self._all_total_latencies = []

        # ---------------------------------------------------------
        # 4. Sync Initial Config to UI
        # ---------------------------------------------------------
        self._sync_settings_to_ui()


        # ---------------------------------------------------------
        # 2. Connect UI interactions to Backend methods
        # ---------------------------------------------------------
        self.window.dashboard.on_start_clicked.connect(self._request_start)
        self.window.dashboard.on_stop_clicked.connect(self._request_stop)
        self.window.orb.clicked_signal.connect(self._toggle_recording)
        self.window.tray.start_stop_toggled.connect(self._on_tray_toggled)
        self.window.settings_page.on_setting_changed.connect(self._on_setting_changed)
        self.window.settings_page.on_hotkey_changed.connect(self._on_hotkey_changed)
        self.window.settings_page.on_audio_device_changed.connect(self._on_audio_device_changed)
        self.window.settings_page.on_reset_defaults_clicked.connect(self._on_reset_defaults_clicked)

        self.window.llms_page.on_provider_selected.connect(self._on_llm_provider_selected)
        self.window.llms_page.on_test_connection_clicked.connect(self._on_llm_test_connection)
        self.window.llms_page.on_api_key_changed.connect(self._on_llm_api_key_changed)
        self.window.llms_page.on_model_variant_changed.connect(self._on_llm_model_changed)
        self.window.llms_page.on_save_clicked.connect(self._on_llm_save)

        self.window.models_page.on_model_install_clicked.connect(self._on_stt_model_install)
        self.window.models_page.on_model_selected.connect(self._on_stt_model_selected)
        self.window.models_page.on_model_remove_clicked.connect(self._on_stt_model_remove)
        self.window.models_page.on_model_cancel_download.connect(self._on_stt_model_cancel)
        self.window.models_page.on_refresh_clicked.connect(self._sync_stt_models_to_ui)
        
        self.window.dashboard.on_quick_action.connect(self._on_quick_action)
        self.window.logs_page.on_export_logs_clicked.connect(self._export_logs)


    def _on_quick_action(self, action_id: str):
        if action_id == "mute_mic":
            self.window.dashboard.add_activity_entry("Microphone muted", "system", datetime.datetime.now().strftime("%H:%M:%S"))
        elif action_id == "clear_history":
            self.window.dashboard.activity_list.clear()
        elif action_id == "test_injection":
            from voiceflow.core.events import RefinedTextReady
            asyncio.run_coroutine_threadsafe(self.bus.emit(RefinedTextReady("Test injection text")), self.loop)
        elif action_id == "reload_model":
            asyncio.run_coroutine_threadsafe(self._restart_stt(), self.loop)
            asyncio.run_coroutine_threadsafe(self._restart_llm(), self.loop)
            self.notification_requested.emit("Reloaded", "Models reloading", "info")

    def _export_logs(self):
        import json
        from voiceflow.core.config import get_appdata_dir
        path = get_appdata_dir() / "logs_export.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.window.logs_page._all_entries, f, indent=2)
        self.notification_requested.emit("Logs Exported", f"Saved to {path}", "success")

    def _on_backend_status_changed(self, status: str):
        mapping = {
            "idle": "idle",
            "recording": "listening",
            "processing": "processing",
            "speaking": "speaking",
            "error": "error"
        }
        mapped_status = mapping.get(status, "idle")
        self.window.dashboard.update_status(mapped_status)
        self.window.orb.set_state(mapped_status)
        self.window.tray.update_status(mapped_status)

    def _on_notification(self, title: str, message: str, kind: str):
        self.window.toast_manager.notify(title, message, kind)

    def _request_start(self):
        from voiceflow.core.events import HotkeyPressed
        asyncio.run_coroutine_threadsafe(self.bus.emit(HotkeyPressed()), self.loop)

    def _request_stop(self):
        from voiceflow.core.events import HotkeyReleased
        asyncio.run_coroutine_threadsafe(self.bus.emit(HotkeyReleased()), self.loop)

    def _toggle_recording(self):
        if self.window.orb._state in ["listening", "processing"]:
            self._request_stop()
        else:
            self._request_start()

    def _on_tray_toggled(self, is_running):
        if is_running:
            self._request_start()
        else:
            self._request_stop()

    def _on_setting_changed(self, key: str, value: Any):
        from voiceflow.core.config import save_config
        config = self.app._config

        if key == "launch_at_startup":
            config.ui.startup_on_windows = value
            self._set_windows_startup(value)
        elif key == "minimize_to_tray":
            config.ui.minimize_to_tray = value
        elif key == "show_floating_orb":
            config.ui.show_orb = value
            self.window.orb.set_visible(value)
        elif key == "auto_check_updates":
            config.ui.auto_check_updates = value
        elif key == "theme":
            config.ui.theme = value.lower().split()[0]
        elif key == "input_gain":
            config.audio.input_gain = value
        elif key == "voice_activity_detection":
            config.vad.enabled = value
        elif key == "noise_suppression":
            config.audio.noise_suppression = value
        elif key == "silence_timeout":
            config.vad.padding_ms = int(float(value.replace("s", "")) * 1000)
        elif key == "debug_logging":
            config.logging.level = "DEBUG" if value else "INFO"
        elif key == "send_telemetry":
            config.logging.send_telemetry = value
        elif key == "prefer_gpu":
            config.stt.device = "cuda" if value else "cpu"

        save_config(config)

    def _on_hotkey_changed(self, action: str, combo: str):
        from voiceflow.core.config import save_config
        if action == "toggle_listen":
            self.app._config.hotkey.combination = combo
            save_config(self.app._config)
            asyncio.run_coroutine_threadsafe(self._restart_hotkey(), self.loop)

    async def _restart_hotkey(self):
        if hasattr(self.app, "_hotkey"):
            await self.app._hotkey.stop()
            from voiceflow.input.hotkey import HotkeyListener
            self.app._hotkey = HotkeyListener(self.app._config.hotkey, self.bus)
            await self.app._hotkey.start()

    def _on_audio_device_changed(self, device_name: str):
        from voiceflow.core.config import save_config
        import sounddevice as sd
        devices = sd.query_devices()
        idx = None
        for i, d in enumerate(devices):
            if d['name'] == device_name and d['max_input_channels'] > 0:
                idx = i
                break
        self.app._config.audio.device_index = idx
        save_config(self.app._config)
        asyncio.run_coroutine_threadsafe(self._restart_audio(), self.loop)

    async def _restart_audio(self):
        if hasattr(self.app, "_capture"):
            await self.app._capture.stop()
            from voiceflow.audio.capture import AudioCapture
            self.app._capture = AudioCapture(self.app._config.audio, self.bus)
            await self.app._capture.start()

    def _sync_settings_to_ui(self):
        config = self.app._config
        page = self.window.settings_page
        page.set_setting("launch_at_startup", config.ui.startup_on_windows)
        page.set_setting("minimize_to_tray", config.ui.minimize_to_tray)
        page.set_setting("show_floating_orb", config.ui.show_orb)
        page.set_setting("auto_check_updates", config.ui.auto_check_updates)
        page.set_setting("voice_activity_detection", config.vad.enabled)
        page.set_setting("noise_suppression", config.audio.noise_suppression)
        page.set_setting("debug_logging", config.logging.level == "DEBUG")
        page.set_setting("send_telemetry", config.logging.send_telemetry)
        page.set_setting("prefer_gpu", config.stt.device in ("cuda", "auto"))
        page.set_setting("input_gain", config.audio.input_gain)
        page.set_setting("theme", config.ui.theme)
        page.set_setting("silence_timeout", config.vad.padding_ms)
        
        # Audio devices
        try:
            import sounddevice as sd
            devices = [d['name'] for d in sd.query_devices() if d['max_input_channels'] > 0]
            page.set_audio_devices(devices)
            if config.audio.device_index is not None and config.audio.device_index < len(sd.query_devices()):
                dev_name = sd.query_devices()[config.audio.device_index]['name']
                page.audio_tab.device_combo.blockSignals(True)
                page.audio_tab.device_combo.setCurrentText(dev_name)
                page.audio_tab.device_combo.blockSignals(False)
        except Exception:
            pass

        # Hotkeys
        page.set_hotkey("toggle_listen", config.hotkey.combination)

        self._sync_llms_to_ui()
        self._sync_stt_models_to_ui()

    def _sync_stt_models_to_ui(self):
        from voiceflow.ui.models import AVAILABLE_MODELS
        import os
        config = self.app._config.stt
        
        models_state = []
        for m in AVAILABLE_MODELS:
            state = dict(m)
            # Basic check for faster-whisper models in huggingface cache
            if m["engine"] == "faster_whisper":
                try:
                    from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE
                    repo_id = f"Systran/faster-whisper-{m['id']}"
                    folder_name = "models--" + repo_id.replace("/", "--")
                    path = os.path.join(HUGGINGFACE_HUB_CACHE, folder_name)
                    state["status"] = "installed" if os.path.exists(path) else "not_installed"
                except ImportError:
                    state["status"] = "not_installed"
            else:
                # For Parakeet, checking ~/.cache/nemo or huggingface cache is harder. Assume installed if selected, else not_installed
                state["status"] = "installed" if config.model_size == m["id"] else "not_installed"
                
            models_state.append(state)
            
        self.window.models_page.update_models(models_state)
        # Select active
        self.window.models_page.set_active_model(config.model_size)

    def _on_stt_model_install(self, model_id: str):
        self.window.models_page.set_model_status(model_id, "downloading")
        self.window.models_page.update_download_progress(model_id, -1)
        asyncio.run_coroutine_threadsafe(self._download_stt_model(model_id), self.loop)

    async def _download_stt_model(self, model_id: str):
        from voiceflow.ui.models import AVAILABLE_MODELS
        import asyncio
        model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
        if not model_info: return
        
        try:
            if model_info["engine"] == "faster_whisper":
                from faster_whisper import WhisperModel
                def _do_download():
                    # Load model will trigger download if missing. We just use cpu for download.
                    WhisperModel(model_id, device="cpu", compute_type="int8")
                await asyncio.to_thread(_do_download)
            elif model_info["engine"] == "parakeet":
                def _do_download_parakeet():
                    import nemo.collections.asr as nemo_asr
                    nemo_asr.models.EncDecCTCModelBPE.from_pretrained(model_name=model_id)
                await asyncio.to_thread(_do_download_parakeet)
            self.window.models_page.set_model_status(model_id, "installed")
            self.notification_requested.emit("Downloaded", f"Model {model_id} installed.", "success")
        except Exception as e:
            self.window.models_page.set_model_status(model_id, "error")
            self.notification_requested.emit("Download Failed", str(e), "error")

    def _on_stt_model_remove(self, model_id: str):
        self.notification_requested.emit("Not Implemented", f"Removing {model_id} is not supported yet.", "warning")

    def _on_stt_model_cancel(self, model_id: str):
        self.notification_requested.emit("Not Implemented", f"Canceling download of {model_id} is not supported.", "warning")
        self.window.models_page.set_model_status(model_id, "not_installed")

    def _on_stt_model_selected(self, model_id: str):
        from voiceflow.ui.models import AVAILABLE_MODELS
        from voiceflow.core.config import save_config
        model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
        if not model_info: return
        
        self.app._config.stt.engine = model_info["engine"]
        self.app._config.stt.model_size = model_id
        save_config(self.app._config)
        self.window.models_page.set_active_model(model_id)
        asyncio.run_coroutine_threadsafe(self._restart_stt(), self.loop)

    async def _restart_stt(self):
        if hasattr(self.app, "_stt"):
            await self.app._stt.stop()
            from voiceflow.stt.service import STTService
            self.app._stt = STTService(self.app._config.stt, self.bus)
            await self.app._stt.start()

    def _sync_llms_to_ui(self):
        from voiceflow.ui.llms import AVAILABLE_PROVIDERS
        config = self.app._config
        from voiceflow.core.config import APIKeys
        api_keys = APIKeys()
        
        providers_state = []
        for p in AVAILABLE_PROVIDERS:
            state = dict(p)
            state["active"] = (config.llm.provider == p["id"])
            key_val = getattr(api_keys, f"{p['id']}_api_key", None)
            state["key_set"] = bool(key_val)
            state["status"] = "untested"
            if state["active"]:
                state["current_model"] = config.llm.model
            providers_state.append(state)
        
        self.window.llms_page.update_providers(providers_state)

    def _on_llm_provider_selected(self, provider_id: str):
        from voiceflow.core.config import save_config
        self.app._config.llm.provider = provider_id
        save_config(self.app._config)
        self.window.llms_page.set_active_provider(provider_id)
        asyncio.run_coroutine_threadsafe(self._restart_llm(), self.loop)

    def _on_llm_model_changed(self, provider_id: str, model_name: str):
        from voiceflow.core.config import save_config
        if self.app._config.llm.provider == provider_id:
            self.app._config.llm.model = model_name
            save_config(self.app._config)
            asyncio.run_coroutine_threadsafe(self._restart_llm(), self.loop)

    def _on_llm_api_key_changed(self, provider_id: str, key: str):
        if not hasattr(self, "_temp_keys"):
            self._temp_keys = {}
        if key and not key.startswith("sk-••••"):
            self._temp_keys[provider_id] = key

    def _on_llm_save(self, provider_id: str):
        if hasattr(self, "_temp_keys") and provider_id in self._temp_keys:
            key_val = self._temp_keys[provider_id]
            import dotenv
            from voiceflow.core.config import get_appdata_dir
            env_file = get_appdata_dir() / ".env"
            if not env_file.exists():
                env_file.touch()
            dotenv.set_key(str(env_file), f"{provider_id}_api_key".upper(), key_val)
            self.notification_requested.emit("Saved", f"API Key saved for {provider_id}.", "success")
            # Clear it
            del self._temp_keys[provider_id]
            # Reload keys
            from voiceflow.core.config import APIKeys
            self.app._api_keys = APIKeys()
            asyncio.run_coroutine_threadsafe(self._restart_llm(), self.loop)
            self._sync_llms_to_ui()

    def _on_llm_test_connection(self, provider_id: str):
        self.window.llms_page.set_connection_status(provider_id, "testing")
        # Run test asynchronously
        asyncio.run_coroutine_threadsafe(self._test_llm_connection(provider_id), self.loop)

    async def _test_llm_connection(self, provider_id: str):
        from voiceflow.llm.providers import get_provider
        import copy
        try:
            cfg = copy.deepcopy(self.app._config.llm)
            cfg.provider = provider_id
            cfg.max_tokens = 5
            # We must use the temp keys if they haven't saved yet, or the saved keys.
            import dataclasses
            # Actually api_keys is a Pydantic model
            keys_copy = self.app._api_keys.model_copy()
            if hasattr(self, "_temp_keys") and provider_id in self._temp_keys:
                setattr(keys_copy, f"{provider_id}_api_key", self._temp_keys[provider_id])
                
            engine_cls = get_provider(provider_id)
            engine = engine_cls(cfg, keys_copy)
            await engine.load_model()
            # Perform a very short test inference
            await engine.refine("Hello")
            self.window.llms_page.set_connection_status(provider_id, "success")
        except Exception as e:
            self.window.llms_page.set_connection_status(provider_id, "error")
            self.notification_requested.emit("Connection Failed", str(e), "error")

    async def _restart_llm(self):
        if hasattr(self.app, "_llm"):
            await self.app._llm.stop()
            from voiceflow.llm.service import LLMService
            self.app._llm = LLMService(self.app._config.llm, self.bus)
            self.app._llm._api_keys = getattr(self.app, "_api_keys", None)
            if not self.app._llm._api_keys:
                from voiceflow.core.config import APIKeys
                self.app._llm._api_keys = APIKeys()
            await self.app._llm.start()

    def _on_reset_defaults_clicked(self):
        # We delete the config file and reload
        import os
        from voiceflow.core.config import get_default_config_path, load_config
        path = get_default_config_path()
        if path.exists():
            os.remove(path)
        self.app._config = load_config()
        self.notification_requested.emit("Settings Reset", "Settings have been reset to defaults. Please restart the app.", "info")

    def _set_windows_startup(self, enable: bool):
        import sys
        import winreg
        import os
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "VoiceFlowLocal"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enable:
                executable = sys.executable
                script_path = os.path.abspath(sys.argv[0])
                cmd = f'"{executable}" -m voiceflow'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            self.notification_requested.emit("Startup Setting Failed", str(e), "error")

    # ---------------------------------------------------------
    # 3. Async Handlers: Subscribed to the EventBus
    # ---------------------------------------------------------
    async def on_status_changed(self, event: StatusChanged):
        self.backend_status_changed.emit(event.status)

    async def on_audio_level(self, event: AudioLevelChanged):
        self.audio_level_changed.emit(event.level)

    async def on_transcript(self, event: TranscriptReady):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.transcript_ready.emit(event.text, "transcript", ts)
        # Briefly show transcript on orb
        # Qt requires UI calls from main thread, so we should dispatch this via a signal if needed, 
        # but the UI demo didn't wire the preview bubble. We can do it if desired.

    async def on_refined_text(self, event: RefinedTextReady):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.transcript_ready.emit(event.text, "command", ts)
        self.notification_requested.emit("Typed successfully", event.text, "success")

    async def on_error(self, event: PipelineError):
        self.notification_requested.emit(f"Error in {event.stage}", str(event.error), "error")
        self.backend_status_changed.emit("error")

    async def on_notification(self, event: NotificationEvent):
        self.notification_requested.emit(event.title, event.message, "info")

    def subscribe_to_backend(self):
        self.bus.subscribe(StatusChanged, self.on_status_changed)
        self.bus.subscribe(AudioLevelChanged, self.on_audio_level)
        self.bus.subscribe(TranscriptReady, self.on_transcript)
        self.bus.subscribe(RefinedTextReady, self.on_refined_text)
        self.bus.subscribe(PipelineError, self.on_error)
        self.bus.subscribe(NotificationEvent, self.on_notification)
        from voiceflow.core.events import PerformanceMetrics, PipelineTiming
        self.bus.subscribe(PerformanceMetrics, self.on_perf_metrics)
        self.bus.subscribe(PipelineTiming, self.on_pipeline_timing)

    async def on_perf_metrics(self, event):
        self.perf_metric_received.emit("cpu", event.cpu_percent)
        self.perf_metric_received.emit("ram", event.ram_percent)
        if event.gpu_percent is not None:
            self.perf_metric_received.emit("gpu", event.gpu_percent)

    async def on_pipeline_timing(self, event):
        self._latencies[event.stage] = event.duration_ms
        self.latency_breakdown_updated.emit(self._latencies)
        
        # When pipeline finishes (inject stage), update overall stats
        if event.stage == "inject":
            self._requests += 1
            total = sum(self._latencies.values())
            self._all_total_latencies.append(total)
            if len(self._all_total_latencies) > 1000:
                self._all_total_latencies.pop(0)
                
            avg = int(sum(self._all_total_latencies) / len(self._all_total_latencies))
            
            sorted_lat = sorted(self._all_total_latencies)
            p95_idx = int(len(sorted_lat) * 0.95)
            p95 = int(sorted_lat[p95_idx]) if sorted_lat else avg
            
            self.pipeline_stats_updated.emit({
                "avg_latency_ms": avg,
                "p95_latency_ms": p95,
                "requests": self._requests
            })

    def _reset_perf_stats(self):
        self._latencies = {"capture": 0, "stt": 0, "llm": 0, "inject": 0}
        self._requests = 0
        self._all_total_latencies = []
        self.latency_breakdown_updated.emit(self._latencies)
        self.pipeline_stats_updated.emit({
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "requests": 0
        })
