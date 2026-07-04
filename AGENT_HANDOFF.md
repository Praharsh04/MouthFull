# Agent Handoff Summary - MouthFull AI

## Overview
This file contains the architectural context, bug fixes, and feature additions implemented during the latest session to assist future agent iterations.

## Recent Architectural Additions
1. **Prompt Processor Service (`backend/prompt/service.py`)**
   - **Purpose:** Injects a dynamic prompt template between the STT generation and LLM refinement stages.
   - **Pipeline Integration:** Listens to `TranscriptReady`, replaces `{{input}}` in the configurable template, and emits a new event `PromptReady`.
   - **Decoupling:** `LLMService` now subscribes to `PromptReady` instead of `TranscriptReady`.
   - **UI Integration:** A dedicated `PromptProcessorPage` was added to `ui/prompt.py` and inserted into the application `NavRail` and stacked pages.
2. **Performance Configurations (`configs/config.py`)**
   - **Injection Engine:** Changed default `method` from `typewrite` to `clipboard` for instant, multi-line injection without key-by-key typing latency.
   - **STT Engine:** Hardcoded defaults switched from `faster_whisper` to `parakeet` (`nvidia/parakeet-tdt-1.1b`) for drastically reduced latency.

## Critical Bug Fixes
1. **PySide6 BrushStyle Crash (`ui/overlay.py`)**
   - **Issue:** Calling `Qt.PenStyle.NoPen` on `setBrush()` caused a fatal `ValueError` terminating the application.
   - **Fix:** Switched to `Qt.BrushStyle.NoBrush`.
2. **DownloadManager Asyncio Crash (`utils/download_manager.py`)**
   - **Issue:** `RuntimeError: no running event loop` was thrown when triggering model downloads via UI buttons. The PySide6 UI thread lacked an event loop for `asyncio.create_task`.
   - **Fix:** `DownloadManager` is now instantiated by `UIBridge` with `loop=self.loop` passed as an argument. Downloads are triggered using `asyncio.run_coroutine_threadsafe`.
3. **Orb UI Rendering and Positioning (`ui/overlay.py`)**
   - **Fixes:** Squarish aura clipping was resolved by ensuring the container has equal dimensions and `border-radius: 50%` is applied securely. Positioning was changed from bottom-right to absolute bottom-center using `QScreen` geometry. Colors were mapped strictly to Sky Blue (listening) and Yellowish Green (processing).

## Build Pipeline
- **Command:** `python scripts/build.py --config Release`
- **Output Directory:** `dist/Release/MouthFull/`
- **Known Quirks:** When rebuilding, the running `MouthFull.exe` must be killed via `taskkill /IM MouthFull.exe /F` to avoid `WinError 5 Access is denied` during the `COLLECT` PyInstaller phase.

## Future Considerations
- Monitor the transition from `faster_whisper` to `parakeet` regarding cache verification; currently `models.py` uses simplified checks for Parakeet presence.
- Ensure that clipboard restoration in `TextInjector._clipboard_inject` successfully retains rich formatting from the user's previous clipboard buffer.
