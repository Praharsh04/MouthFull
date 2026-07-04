"""Expanded Modern Settings window using Tkinter and ttk."""

from __future__ import annotations

import os
import re
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING

from voiceflow.audio.devices import list_input_devices
from voiceflow.core.logger import logger
from voiceflow.llm.prompts import manager as prompt_manager

if TYPE_CHECKING:
    from voiceflow.core.config import AppConfig


class SettingsWindow:
    """A minimal, modern Tkinter dialog for changing settings."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._root = tk.Tk()
        self._root.title("Settings - VoiceFlow Local")
        self._root.geometry("650x550")
        self._root.resizable(False, False)

        # Apply theme
        self._apply_theme()

        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("TNotebook", background=self._bg_color)
        style.configure("TNotebook.Tab", padding=[15, 5], font=("Segoe UI", 10))
        style.configure("TFrame", background=self._fg_color)
        style.configure("TLabel", background=self._fg_color, foreground=self._text_color, font=("Segoe UI", 9))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground=self._text_color)
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("TCheckbutton", background=self._fg_color, foreground=self._text_color)
        style.configure("TRadiobutton", background=self._fg_color, foreground=self._text_color)

        self._root.configure(bg=self._bg_color)
        self._root.eval('tk::PlaceWindow . center')

        self._notebook = ttk.Notebook(self._root)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_general_tab()
        self._build_speech_llm_tab()
        self._build_prompts_tab()
        self._build_orb_tab()
        self._build_advanced_tab()

        # Bottom bar
        bottom_frame = ttk.Frame(self._root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(bottom_frame, text="Save & Close", command=self._save).pack(side=tk.RIGHT)
        ttk.Button(bottom_frame, text="Cancel", command=self._root.destroy).pack(side=tk.RIGHT, padx=5)

    def _apply_theme(self):
        theme = self._config.ui.theme
        if theme == "dark":
            self._bg_color = "#1e1e1e"
            self._fg_color = "#2d2d2d"
            self._text_color = "#ffffff"
        else: # light / system (fallback)
            self._bg_color = "#f0f0f0"
            self._fg_color = "#ffffff"
            self._text_color = "#333333"

    def _build_general_tab(self) -> None:
        frame = ttk.Frame(self._notebook, padding=20)
        self._notebook.add(frame, text="General")

        # UI/System
        ttk.Label(frame, text="System", style="Header.TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 5), columnspan=2)

        self._startup_var = tk.BooleanVar(value=self._config.ui.startup_on_windows)
        ttk.Checkbutton(frame, text="Run on Windows Startup", variable=self._startup_var).grid(row=1, column=0, sticky=tk.W, pady=2, columnspan=2)

        ttk.Label(frame, text="Theme:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self._theme_var = tk.StringVar(value=self._config.ui.theme)
        ttk.Combobox(frame, textvariable=self._theme_var, values=["light", "dark", "system"], state="readonly", width=15).grid(row=2, column=1, sticky=tk.W, padx=10)

        # Microphone
        ttk.Label(frame, text="Microphone", style="Header.TLabel").grid(row=3, column=0, sticky=tk.W, pady=(15, 5), columnspan=2)
        self._devices = list_input_devices()
        self._device_names = [f"{d.index}: {d.name}" for d in self._devices]
        self._selected_device = tk.StringVar()
        current_idx = self._config.audio.device_index
        if current_idx is not None:
            for name in self._device_names:
                if name.startswith(f"{current_idx}:"):
                    self._selected_device.set(name)
                    break
        if not self._selected_device.get() and self._device_names:
            self._selected_device.set(self._device_names[0])

        ttk.Combobox(frame, textvariable=self._selected_device, values=self._device_names, state="readonly", width=50).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # Hotkey
        ttk.Label(frame, text="Global Hotkey", style="Header.TLabel").grid(row=5, column=0, sticky=tk.W, pady=(15, 5), columnspan=2)

        ttk.Label(frame, text="Combination:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self._hotkey_var = tk.StringVar(value=self._config.hotkey.combination)
        ttk.Entry(frame, textvariable=self._hotkey_var, width=20).grid(row=6, column=1, sticky=tk.W, padx=10)

        ttk.Label(frame, text="Mode:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self._hotkey_mode_var = tk.StringVar(value=self._config.hotkey.mode)
        ttk.Combobox(frame, textvariable=self._hotkey_mode_var, values=["push_to_talk", "toggle"], state="readonly", width=15).grid(row=7, column=1, sticky=tk.W, padx=10)

        # Injection
        ttk.Label(frame, text="Text Injection", style="Header.TLabel").grid(row=8, column=0, sticky=tk.W, pady=(15, 5), columnspan=2)
        ttk.Label(frame, text="Method:").grid(row=9, column=0, sticky=tk.W, pady=2)
        self._injection_method_var = tk.StringVar(value=self._config.injection.method)
        ttk.Combobox(frame, textvariable=self._injection_method_var, values=["clipboard", "typewrite"], state="readonly", width=15).grid(row=9, column=1, sticky=tk.W, padx=10)

        ttk.Label(frame, text="Typing Speed (delay):").grid(row=10, column=0, sticky=tk.W, pady=2)
        self._injection_speed_var = tk.DoubleVar(value=self._config.injection.keystroke_delay)
        ttk.Spinbox(frame, textvariable=self._injection_speed_var, from_=0.0, to_=1.0, increment=0.01, width=15).grid(row=10, column=1, sticky=tk.W, padx=10)

    def _build_speech_llm_tab(self) -> None:
        frame = ttk.Frame(self._notebook, padding=20)
        self._notebook.add(frame, text="Speech & LLM")

        # STT
        ttk.Label(frame, text="Speech-to-Text (STT)", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self._stt_engines = ["faster_whisper", "parakeet"]
        self._selected_stt = tk.StringVar(value=self._config.stt.engine)
        ttk.Combobox(frame, textvariable=self._selected_stt, values=self._stt_engines, state="readonly", width=30).pack(anchor=tk.W, pady=(0, 20))

        # LLM
        ttk.Label(frame, text="LLM Provider", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self._llm_providers = ["ollama", "openai", "anthropic", "gemini", "openrouter", "custom", "llamacpp"]
        self._selected_llm = tk.StringVar(value=self._config.llm.provider)
        cb = ttk.Combobox(frame, textvariable=self._selected_llm, values=self._llm_providers, state="readonly", width=30)
        cb.pack(anchor=tk.W, pady=(0, 15))
        cb.bind("<<ComboboxSelected>>", self._on_llm_provider_change)

        self._llm_fields_frame = ttk.Frame(frame)
        self._llm_fields_frame.pack(fill=tk.BOTH, expand=True)

        self._llm_model = tk.StringVar(value=self._config.llm.model)
        self._llm_endpoint = tk.StringVar(value=self._config.llm.api_base or "")
        self._llm_api_key = tk.StringVar()
        self._load_api_key_for_provider(self._config.llm.provider)
        self._on_llm_provider_change()

    def _load_api_key_for_provider(self, provider: str) -> None:
        key_name = f"{provider.upper()}_API_KEY"
        from dotenv import load_dotenv
        load_dotenv()
        self._llm_api_key.set(os.getenv(key_name, ""))

    def _on_llm_provider_change(self, event=None) -> None:
        for widget in self._llm_fields_frame.winfo_children():
            widget.destroy()
        provider = self._selected_llm.get()
        if event:
            self._load_api_key_for_provider(provider)

        ttk.Label(self._llm_fields_frame, text="Model Name").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self._llm_fields_frame, textvariable=self._llm_model, width=40).grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)

        if provider not in ["ollama", "llamacpp"]:
            ttk.Label(self._llm_fields_frame, text="API Key").grid(row=1, column=0, sticky=tk.W, pady=5)
            ttk.Entry(self._llm_fields_frame, textvariable=self._llm_api_key, width=40, show="*").grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)

        if provider in ["ollama", "custom", "openrouter"]:
            ttk.Label(self._llm_fields_frame, text="Endpoint URL").grid(row=2, column=0, sticky=tk.W, pady=5)
            ttk.Entry(self._llm_fields_frame, textvariable=self._llm_endpoint, width=40).grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

    def _build_prompts_tab(self) -> None:
        frame = ttk.Frame(self._notebook, padding=10)
        self._notebook.add(frame, text="Prompts")

        top_bar = ttk.Frame(frame)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(top_bar, text="Template:").pack(side=tk.LEFT)
        self._prompt_names = list(prompt_manager.templates.keys())
        self._selected_prompt = tk.StringVar(value=self._config.llm.prompt_template)

        if self._selected_prompt.get() not in self._prompt_names:
            self._selected_prompt.set("default")

        self._prompt_cb = ttk.Combobox(
            top_bar, textvariable=self._selected_prompt, values=self._prompt_names, state="readonly", width=20
        )
        self._prompt_cb.pack(side=tk.LEFT, padx=5)
        self._prompt_cb.bind("<<ComboboxSelected>>", self._on_prompt_change)

        ttk.Button(top_bar, text="New", command=self._new_prompt).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="Duplicate", command=self._duplicate_prompt).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="Delete", command=self._delete_prompt).pack(side=tk.LEFT, padx=2)

        self._active_lbl = ttk.Label(top_bar, text="(Active)", foreground="green")
        self._active_lbl.pack(side=tk.RIGHT)

        self._prompt_text = tk.Text(frame, height=15, width=60, font=("Consolas", 10), bg="#fafafa")
        self._prompt_text.pack(fill=tk.BOTH, expand=True)

        btn_bar = ttk.Frame(frame)
        btn_bar.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_bar, text="Save Template", command=self._save_current_prompt).pack(side=tk.LEFT)
        ttk.Button(btn_bar, text="Import", command=self._import_prompts).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_bar, text="Export", command=self._export_prompts).pack(side=tk.LEFT)
        ttk.Button(btn_bar, text="Set as Default", command=self._set_active_prompt).pack(side=tk.RIGHT)

        self._on_prompt_change()

    def _on_prompt_change(self, event=None) -> None:
        name = self._selected_prompt.get()
        content = prompt_manager.get_template(name)
        self._prompt_text.delete("1.0", tk.END)
        self._prompt_text.insert("1.0", content)
        if name == self._config.llm.prompt_template:
            self._active_lbl.config(text="(Active)", foreground="green")
        else:
            self._active_lbl.config(text="")

    def _new_prompt(self) -> None:
        name = simpledialog.askstring("New Prompt", "Enter template name:")
        if name:
            prompt_manager.set_template(name, "You are a dictation assistant.\n\nDictated text: {raw_text}")
            self._update_prompt_dropdown(name)

    def _duplicate_prompt(self) -> None:
        current = self._selected_prompt.get()
        name = simpledialog.askstring("Duplicate Prompt", "New name:", initialvalue=f"{current}_copy")
        if name:
            content = self._prompt_text.get("1.0", tk.END).strip()
            prompt_manager.set_template(name, content)
            self._update_prompt_dropdown(name)

    def _update_prompt_dropdown(self, name: str) -> None:
        self._prompt_names = list(prompt_manager.templates.keys())
        self._prompt_cb.config(values=self._prompt_names)
        self._selected_prompt.set(name)
        self._on_prompt_change()

    def _delete_prompt(self) -> None:
        name = self._selected_prompt.get()
        if name in ["default", "formal", "code_comment", "email"]:
            messagebox.showerror("Error", "Cannot delete built-in templates.")
            return
        if messagebox.askyesno("Confirm", f"Delete template '{name}'?"):
            prompt_manager.delete_template(name)
            self._update_prompt_dropdown("default")

    def _save_current_prompt(self) -> None:
        name = self._selected_prompt.get()
        content = self._prompt_text.get("1.0", tk.END).strip()
        prompt_manager.set_template(name, content)
        messagebox.showinfo("Saved", f"Template '{name}' saved.")

    def _set_active_prompt(self) -> None:
        name = self._selected_prompt.get()
        self._config.llm.prompt_template = name
        self._on_prompt_change()
        messagebox.showinfo("Active Prompt", f"'{name}' is now the active prompt.")

    def _import_prompts(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("YAML", "*.yaml"), ("JSON", "*.json")])
        if path:
            try:
                import yaml
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        prompt_manager.set_template(k, str(v))
                    self._update_prompt_dropdown(self._selected_prompt.get())
                    messagebox.showinfo("Import", "Prompts imported.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import: {e}")

    def _export_prompts(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".yaml", filetypes=[("YAML", "*.yaml")])
        if path:
            try:
                import yaml
                with open(path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(prompt_manager.templates, f)
                messagebox.showinfo("Export", "Prompts exported.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")

    def _build_orb_tab(self) -> None:
        frame = ttk.Frame(self._notebook, padding=20)
        self._notebook.add(frame, text="Orb & UX")
        
        ttk.Label(frame, text="AI Orb Configuration", style="Header.TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 15), columnspan=2)
        
        self._show_orb_var = tk.BooleanVar(value=self._config.ui.show_orb)
        ttk.Checkbutton(frame, text="Enable Floating Orb", variable=self._show_orb_var).grid(row=1, column=0, sticky=tk.W, pady=2, columnspan=2)
        
        self._show_icon_var = tk.BooleanVar(value=self._config.ui.show_app_icon)
        ttk.Checkbutton(frame, text="Show Active Application Icon", variable=self._show_icon_var).grid(row=2, column=0, sticky=tk.W, pady=2, columnspan=2)
        
        self._voice_anim_var = tk.BooleanVar(value=self._config.ui.voice_animations)
        ttk.Checkbutton(frame, text="Voice Reactive Animations", variable=self._voice_anim_var).grid(row=3, column=0, sticky=tk.W, pady=2, columnspan=2)
        
        self._always_on_top_var = tk.BooleanVar(value=self._config.ui.always_on_top)
        ttk.Checkbutton(frame, text="Always on Top", variable=self._always_on_top_var).grid(row=4, column=0, sticky=tk.W, pady=2, columnspan=2)
        
        ttk.Label(frame, text="Transparency:").grid(row=5, column=0, sticky=tk.W, pady=(10, 2))
        self._orb_alpha_var = tk.DoubleVar(value=self._config.ui.orb_transparency)
        ttk.Spinbox(frame, textvariable=self._orb_alpha_var, from_=0.1, to=1.0, increment=0.1, width=10).grid(row=5, column=1, sticky=tk.W, padx=10, pady=(10, 2))
        
        ttk.Label(frame, text="Animation Intensity:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self._orb_intensity_var = tk.DoubleVar(value=self._config.ui.animation_intensity)
        ttk.Spinbox(frame, textvariable=self._orb_intensity_var, from_=0.1, to=3.0, increment=0.1, width=10).grid(row=6, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(frame, text="Orb Size (px):").grid(row=7, column=0, sticky=tk.W, pady=2)
        self._orb_size_var = tk.IntVar(value=self._config.ui.orb_size)
        ttk.Spinbox(frame, textvariable=self._orb_size_var, from_=40, to=200, increment=10, width=10).grid(row=7, column=1, sticky=tk.W, padx=10)

    def _build_advanced_tab(self) -> None:
        frame = ttk.Frame(self._notebook, padding=20)
        self._notebook.add(frame, text="Advanced")

        ttk.Label(frame, text="Data Management", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(frame, text="Backup all settings, prompts, and API keys to a zip archive, or restore from one.", wraplength=400).pack(anchor=tk.W, pady=(0, 15))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(anchor=tk.W)
        ttk.Button(btn_frame, text="Export Configuration Backup", command=self._export_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Restore Configuration Backup", command=self._import_config).pack(side=tk.LEFT)

    def _export_config(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Zip Archives", "*.zip")], initialfile="voiceflow_backup.zip")
        if not path:
            return
        try:
            with zipfile.ZipFile(path, 'w') as zf:
                for f in ["config.yaml", "prompts.yaml", ".env"]:
                    if Path(f).exists():
                        zf.write(f)
            messagebox.showinfo("Export Backup", "Configuration successfully backed up.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to backup configuration: {e}")

    def _import_config(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Zip Archives", "*.zip")])
        if not path:
            return
        if messagebox.askyesno("Confirm Restore", "This will overwrite your current settings, API keys, and prompts. Continue?"):
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    for member in zf.namelist():
                        if member in ["config.yaml", "prompts.yaml", ".env"]:
                            zf.extract(member)
                messagebox.showinfo("Restore Backup", "Configuration successfully restored. Please restart VoiceFlow.")
                # We do not dynamically reload everything here to keep it simple, suggest restart.
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restore configuration: {e}")

    def _save(self) -> None:
        # Toggle Windows Startup
        self._toggle_windows_startup(self._startup_var.get())

        from voiceflow.core.config import get_default_config_path
        config_path = get_default_config_path()
        if not config_path.exists():
            config_path.write_text("audio:\n  device_index: null\nstt:\n  engine: parakeet\nllm:\n  enabled: true\n  provider: ollama\nhotkey:\n  combination: ctrl+space\ninjection:\n  method: clipboard\nui:\n  theme: system\n")

        content = config_path.read_text(encoding="utf-8")

        def _upsert(yaml_text, section, key, val, quote=False):
            # Naive regex replacement or insertion
            q = '"' if quote else ''
            new_line = f"{key}: {q}{val}{q}"

            # If section exists
            if re.search(rf"^{section}:", yaml_text, re.MULTILINE):
                # If key exists under section (simple check)
                if re.search(rf"^  {key}:.*", yaml_text, re.MULTILINE):
                    yaml_text = re.sub(rf"(?<=\n)  {key}:.*", f"  {new_line}", yaml_text)
                else:
                    # Append under section
                    yaml_text = re.sub(rf"(^{section}:[^\n]*)", f"\\1\n  {new_line}", yaml_text, flags=re.MULTILINE)
            else:
                # Add section
                yaml_text += f"\n{section}:\n  {new_line}\n"
            return yaml_text

        # Audio
        sel = self._selected_device.get()
        if sel:
            idx = sel.split(":")[0]
            content = _upsert(content, "audio", "device_index", idx)

        # STT
        content = _upsert(content, "stt", "engine", self._selected_stt.get(), True)

        # LLM
        provider = self._selected_llm.get()
        content = _upsert(content, "llm", "provider", provider, True)
        content = _upsert(content, "llm", "model", self._llm_model.get().strip(), True)
        ep = self._llm_endpoint.get().strip()
        if ep:
            content = _upsert(content, "llm", "api_base", ep, True)

        content = _upsert(content, "llm", "prompt_template", self._config.llm.prompt_template, True)

        # Hotkey
        content = _upsert(content, "hotkey", "combination", self._hotkey_var.get(), True)
        content = _upsert(content, "hotkey", "mode", self._hotkey_mode_var.get(), True)

        # Injection
        content = _upsert(content, "injection", "method", self._injection_method_var.get(), True)
        content = _upsert(content, "injection", "keystroke_delay", str(self._injection_speed_var.get()))

        # UI
        content = _upsert(content, "ui", "startup_on_windows", str(self._startup_var.get()).lower())
        content = _upsert(content, "ui", "theme", self._theme_var.get(), True)
        content = _upsert(content, "ui", "show_orb", str(self._show_orb_var.get()).lower())
        content = _upsert(content, "ui", "show_app_icon", str(self._show_icon_var.get()).lower())
        content = _upsert(content, "ui", "voice_animations", str(self._voice_anim_var.get()).lower())
        content = _upsert(content, "ui", "always_on_top", str(self._always_on_top_var.get()).lower())
        content = _upsert(content, "ui", "orb_transparency", str(self._orb_alpha_var.get()))
        content = _upsert(content, "ui", "animation_intensity", str(self._orb_intensity_var.get()))
        content = _upsert(content, "ui", "orb_size", str(self._orb_size_var.get()))

        config_path.write_text(content, encoding="utf-8")

        # API Keys
        if provider not in ["ollama", "llamacpp"]:
            api_key = self._llm_api_key.get().strip()
            if api_key:
                from voiceflow.core.config import get_appdata_dir
                env_path = get_appdata_dir() / ".env"
                env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
                key_name = f"{provider.upper()}_API_KEY"
                if f"{key_name}=" in env_content:
                    env_content = re.sub(rf"{key_name}=.*", f"{key_name}={api_key}", env_content)
                else:
                    env_content += f"\n{key_name}={api_key}\n"
                env_path.write_text(env_content.strip() + "\n", encoding="utf-8")

        logger.info("Saved all settings.")
        self._root.destroy()

    def _toggle_windows_startup(self, enable: bool) -> None:
        """Add or remove VoiceFlow from Windows startup registry."""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enable:
                import sys
                script = Path(sys.argv[0]).resolve()
                winreg.SetValueEx(key, "VoiceFlowLocal", 0, winreg.REG_SZ, f'"{sys.executable}" "{script}"')
            else:
                try:
                    winreg.DeleteValue(key, "VoiceFlowLocal")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.warning("Failed to toggle Windows startup: {}", e)

    def show(self) -> None:
        self._root.mainloop()
