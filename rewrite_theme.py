import re

def rewrite_theme():
    with open('E:/Apps/Voky/src/mouthfull/ui/theme.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Create light theme colors
    light_theme_str = """
class LightColors:
    BG_APP = "#F5F5F5"
    BG_SURFACE = "#FFFFFF"
    BG_SURFACE_ALT = "#F9F9F9"
    BG_CARD = "#F0F0F0"
    BG_CARD_HOVER = "#E8E8E8"
    BG_INPUT = "#FFFFFF"
    BORDER = "#E0E0E0"
    BORDER_SOFT = "#EEEEEE"

    TEXT_PRIMARY = "#1e1f22"
    TEXT_SECONDARY = "#55565a"
    TEXT_MUTED = "#75767a"
    TEXT_DISABLED = "#a7a8ac"

    ACCENT = "#D4AF37"
    ACCENT_HOVER = "#E5C07B"
    ACCENT_PRESSED = "#B3922D"
    ACCENT_SOFT = "#D4AF3726"

    SUCCESS = "#36B359"
    WARNING = "#E69500"
    ERROR = "#CC4444"
    INFO = "#3388EE"

    ORB_IDLE = "#A89A80"
    ORB_LISTENING = "#D4AF37"
    ORB_PROCESSING = "#3388EE"
    ORB_SPEAKING = "#36B359"
    ORB_ERROR = "#CC4444"

class DarkColors:
    BG_APP = "#1e1f22"
    BG_SURFACE = "#242528"
    BG_SURFACE_ALT = "#2a2b2f"
    BG_CARD = "#28292d"
    BG_CARD_HOVER = "#2f3034"
    BG_INPUT = "#1b1c1e"
    BORDER = "#36373b"
    BORDER_SOFT = "#2d2e32"

    TEXT_PRIMARY = "#f2f2f3"
    TEXT_SECONDARY = "#a7a8ac"
    TEXT_MUTED = "#75767a"
    TEXT_DISABLED = "#55565a"

    ACCENT = "#D4AF37"
    ACCENT_HOVER = "#E5C07B"
    ACCENT_PRESSED = "#B3922D"
    ACCENT_SOFT = "#D4AF3726"

    SUCCESS = "#50C878"
    WARNING = "#F5A623"
    ERROR = "#E06666"
    INFO = "#4DA6FF"

    ORB_IDLE = "#8A795D"
    ORB_LISTENING = "#D4AF37"
    ORB_PROCESSING = "#4DA6FF"
    ORB_SPEAKING = "#50C878"
    ORB_ERROR = "#E06666"

"""
    # Replace Colors with empty class that gets populated later
    content = re.sub(r'class Colors:\s+.*?class Metrics:', 'class Colors:\n    pass\n\nclass Metrics:', content, flags=re.DOTALL)
    content = content.replace('class Colors:\n    pass', light_theme_str + '\nclass Colors(DarkColors):\n    pass')

    # Convert APP_QSS to a function
    content = content.replace('APP_QSS = f"""', 'def get_app_qss():\n    return f"""')
    content = content.replace('APP_QSS = f"""', 'def get_app_qss():\n    return f"""')
    content = content.replace('"""\n', '"""\n\nAPP_QSS = get_app_qss()\n\ndef apply_theme(theme_name: str, app=None):\n    source = LightColors if theme_name == "light" else DarkColors\n    for k, v in source.__dict__.items():\n        if not k.startswith("__"):\n            setattr(Colors, k, v)\n    global APP_QSS\n    APP_QSS = get_app_qss()\n    if app:\n        app.setStyleSheet(APP_QSS)\n')

    with open('E:/Apps/Voky/src/mouthfull/ui/theme.py', 'w', encoding='utf-8') as f:
        f.write(content)

rewrite_theme()
