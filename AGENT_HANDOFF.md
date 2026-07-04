# Agent Handoff Summary - MouthFull AI

## Overview
This file contains the architectural context, bug fixes, and feature additions implemented during the latest session to assist future agent iterations.

## Current State & Next Steps (CRITICAL)
- **Status:** All code fixes have been pushed to GitHub cleanly.
- **Pending Action:** The PyInstaller packaging process was manually CANCELLED because the user had to shut down their PC for the night. 
- **Next Step:** The next agent *MUST* run `python scripts/build.py --config Release` first thing tomorrow to finalize the executable for the user. (Wait for ~7-9 mins and notify the user when the executable is ready in `dist/Release/MouthFull`).

## Recent Architectural Additions
1. **Prompt Processor Service (`backend/prompt/service.py`)**
   - **Purpose:** Injects a dynamic prompt template between the STT generation and LLM refinement stages.
   - **Pipeline Integration:** Listens to `TranscriptReady`, replaces `{{input}}` in the configurable template, and emits a new event `PromptReady`.
   - **LLM Bypass Logic:** The `PromptReady` event now contains an `is_prompt: bool` flag. If the Prompt Processor is disabled, it emits `is_prompt=False`. The `LLMService` sees this and instantly bypasses the LLM processing, providing zero-latency dictation when AI generation is not explicitly requested.
2. **Performance Configurations (`configs/config.py`)**
   - **Injection Engine:** Changed default `method` from `typewrite` to `clipboard` for instant, multi-line injection without key-by-key typing latency.
   - **STT Engine:** Hardcoded defaults switched from `faster_whisper` to `parakeet` (`nvidia/parakeet-tdt-1.1b`) for drastically reduced latency.
   - **LLM Default:** Disabled by default to prevent Ollama from silently introducing 5+ second delays for standard voice dictation.

## Critical Bug Fixes
1. **LLM UI Controls & Bridge Fixes**
   - **Issue:** The LLM Providers page lacked a master toggle, and modifying `ui/bridge.py` introduced an `AttributeError` for `_api_keys`.
   - **Fix:** Added a master `Enable LLM Provider` toggle switch to `ui/llms.py`. Fixed the local scope referencing of `api_keys` in `ui/bridge.py` during list population.
2. **Prompt Processor Toggle Desync (`ui/prompt.py`)**
   - **Issue:** The UI toggle switch visually flipped but did not save the config to the backend unless the separate "Save Settings" button was clicked.
   - **Fix:** Wired `self.enable_toggle.toggled_signal` to trigger `_on_save()` instantly. Also swapped `setChecked` for `set_checked_silent` on initial load to prevent signal cascading.
3. **DownloadManager Asyncio Crash (`utils/download_manager.py`)**
   - **Issue:** `RuntimeError: no running event loop` was thrown when triggering model downloads via UI buttons.
   - **Fix:** `DownloadManager` is now instantiated by `UIBridge` with `loop=self.loop`. Downloads use `asyncio.run_coroutine_threadsafe`.

## Build Pipeline
- **Command:** `python scripts/build.py --config Release`
- **Output Directory:** `dist/Release/MouthFull/`
- **Known Quirks:** When rebuilding, the running `MouthFull.exe` must be killed via `taskkill /IM MouthFull.exe /F` to avoid `WinError 5 Access is denied`.
