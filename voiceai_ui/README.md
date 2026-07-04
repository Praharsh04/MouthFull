# VoiceFlow AI — Desktop UI (Frontend Only)

A polished, native-feeling Windows desktop frontend built with **PySide6**,
designed to be dropped in front of an existing Python backend (hotkeys,
audio recording, STT, LLM processing, text injection, event bus). This
package contains **zero backend logic** — every backend touch-point is an
explicit Qt Signal (UI → backend) or a plain method (backend → UI).

Visual language takes cues from PowerToys, Docker Desktop, Ollama Desktop,
EarTrumpet, and Phone Link: dark theme, single accent color, rounded cards,
a left nav rail, and small live status indicators everywhere.

## Running the demo

```bash
pip install -r requirements.txt
python main.py
```

The demo runs standalone with realistic placeholder data and a few internal
timers (e.g. simulated CPU/RAM graphs, a fake model-download progress bar)
so every screen looks alive even with no backend attached. Search the code
for `# BACKEND HOOK` and `_demo_` to find the exact spots meant to be
replaced or removed once a real backend is wired in.

## Project structure

```
ui/
    app.py          Main window shell: nav rail + page stack + tray + orb + notifications
    theme.py         Design tokens (colors, spacing) + global QSS stylesheet
    tray.py          System tray icon + menu
    overlay.py       Floating AI Orb (frameless always-on-top status indicator)
    dashboard.py     Dashboard page (status, quick actions, activity feed)
    models.py        Speech Models page (install/download/select STT models)
    llms.py          LLM Providers page (API keys, model variants, test connection)
    performance.py   Performance Dashboard (CPU/RAM/GPU sparklines, latency breakdown)
    logs.py          Log Viewer (filterable, color-coded table)
    settings.py      Settings page (General / Hotkeys / Audio / Advanced tabs)
    wizard.py        Setup Wizard (first-run onboarding flow)
    notifications.py Notification Center (slide-out panel, persistent history)
    widgets/
        toggle_switch.py     Animated on/off switch
        status_badge.py      StatusDot + StatusBadge (colored state pills)
        card.py              Rounded surface container
        audio_meter.py       Segmented VU meter for mic input level
        nav_rail.py          Left sidebar navigation
        toast.py             Transient toast notifications (Toast + ToastManager)
        hotkey_recorder.py   Click-to-record global hotkey field
main.py              Entry point
requirements.txt
```

## Integration contract

Every page/widget follows the same pattern:

- **Signals** (suffixed `_clicked`, `_changed`, `on_*`, or plain past-tense
  like `toggled`) fire **UI → backend**. Connect your backend logic to
  these; do not call them yourself except from within the UI.
- **Methods** (prefixed `update_*` or `set_*`) are how the **backend pushes
  state into the UI**. Call these from your event bus handlers.

Example — wiring the Dashboard's start/stop button and status to a backend:

```python
from ui.app import MainWindow

window = MainWindow()

# UI -> backend
window.dashboard.on_start_clicked.connect(backend.start_listening)
window.dashboard.on_stop_clicked.connect(backend.stop_listening)
window.dashboard.on_quick_action.connect(backend.run_quick_action)

# backend -> UI (e.g. from your event bus subscriber)
event_bus.on("state_changed", lambda s: window.dashboard.update_status(s))
event_bus.on("audio_level",  lambda lvl: window.dashboard.update_audio_level(lvl))
event_bus.on("audio_level",  lambda lvl: window.orb.update_audio_level(lvl))
event_bus.on("state_changed", lambda s: window.orb.set_state(s))
event_bus.on("state_changed", lambda s: window.tray.update_status(s))
```

Every page's module docstring (top of each `.py` file) lists its exact
Signals and methods. Highlights:

| Page | Key UI → backend signals | Key backend → UI methods |
|---|---|---|
| `tray.py` | `start_stop_toggled`, `quick_action_triggered` | `update_status()`, `show_message()` |
| `overlay.py` (Orb) | `clicked_signal`, `dragged_signal` | `set_state()`, `update_audio_level()`, `show_transcript_preview()` |
| `dashboard.py` | `on_start_clicked`, `on_stop_clicked`, `on_quick_action` | `update_status()`, `update_audio_level()`, `update_stats()`, `add_activity_entry()` |
| `models.py` | `on_model_install_clicked`, `on_model_selected` | `update_models()`, `update_download_progress()`, `set_model_status()` |
| `llms.py` | `on_test_connection_clicked`, `on_api_key_changed` | `update_providers()`, `set_connection_status()` |
| `performance.py` | `on_reset_stats_clicked` | `update_metric()`, `update_latency_breakdown()`, `update_pipeline_stats()` |
| `logs.py` | `on_clear_logs_clicked`, `on_export_logs_clicked` | `update_logs()`, `append_log()` |
| `settings.py` | `on_setting_changed`, `on_hotkey_changed` | `set_setting()`, `set_hotkey()`, `set_audio_devices()` |
| `wizard.py` | `on_permission_requested`, `on_model_chosen`, `on_hotkey_configured` | `set_permission_status()`, `set_download_progress()` |
| `notifications.py` | `on_notification_dismissed`, `on_mark_all_read_clicked` | `add_notification()`, `set_notifications()` |

## Notes for the next engineer wiring up the backend

1. Replace the `_demo_*` methods and the `QTimer`-driven fake data
   generators in `app.py` and `performance.py` — they only exist to make
   the UI feel alive in isolation.
2. `MainWindow.closeEvent` currently just hides the window ("minimize to
   tray" behavior). If your backend needs a clean shutdown path, hook a
   real quit sequence into `tray.quit_requested`.
3. All dummy data (`DUMMY_MODELS`, `DUMMY_PROVIDERS`, `DUMMY_MESSAGES`, the
   dashboard's seeded activity feed) is clearly named and isolated at the
   top of its module — swap it for a `update_*()` call from real data on
   startup.
4. The app never imports or touches anything related to audio, speech
   recognition, LLMs, or global hotkeys — only Qt/PySide6.
