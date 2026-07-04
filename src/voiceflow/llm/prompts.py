"""Prompt templates for LLM text refinement.

Responsibilities:
- Define built-in prompt templates (default, formal, code_comment, email).
- Allow user-defined templates loaded from and saved to prompts.yaml.
- Render templates with the raw STT text.
"""

from __future__ import annotations

from pathlib import Path

import yaml

BUILTIN_TEMPLATES: dict[str, str] = {
    "default": "You are a dictation assistant. Fix grammar, spelling, punctuation, and remove filler words (um, uh). Output ONLY the corrected text.\n\nDictated text: {raw_text}",
    "formal": "You are a professional writing assistant. Rewrite the following dictated text in a formal, professional tone. Output ONLY the corrected text.\n\nDictated text: {raw_text}",
    "code_comment": "You are a software documentation assistant. Rewrite as a clear, concise technical comment. Output ONLY the comment text.\n\nDictated text: {raw_text}",
    "email": "You are an email writing assistant. Format it properly with appropriate greeting. Output ONLY the corrected text.\n\nDictated text: {raw_text}",
}

class PromptManager:
    """Manages prompt templates and persistence."""

    def __init__(self, path: str = "prompts.yaml"):
        self.path = Path(path)
        self.templates = BUILTIN_TEMPLATES.copy()
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                with open(self.path, encoding="utf-8") as f:
                    custom = yaml.safe_load(f) or {}
                    self.templates.update(custom)
            except Exception:
                pass

    def save(self) -> None:
        custom_templates = {k: v for k, v in self.templates.items() if k not in BUILTIN_TEMPLATES or BUILTIN_TEMPLATES[k] != v}
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(custom_templates, f)

    def get_template(self, name: str) -> str:
        return self.templates.get(name, BUILTIN_TEMPLATES["default"])

    def set_template(self, name: str, content: str) -> None:
        self.templates[name] = content
        self.save()

    def delete_template(self, name: str) -> None:
        if name in self.templates:
            del self.templates[name]
            self.save()

# Global singleton for easy access
manager = PromptManager()

def get_template(name: str) -> str:
    return manager.get_template(name)

def render_prompt(template_name: str, raw_text: str) -> str:
    template = get_template(template_name)
    if "{raw_text}" not in template:
        template += "\n\n{raw_text}"
    return template.format(raw_text=raw_text)
