# Theme design tokens for DIT Copy Pro (ShotPut Pro Dark Aesthetic)

BG_DARK = "#16161a"
PANEL_BG = "#1e1e24"
CARD_BG = "#26262e"
CARD_BORDER = "#363642"

ACCENT_PRIMARY = "#2d7ff9"       # ShotPut Pro Blue
ACCENT_PRIMARY_HOVER = "#1a68e0"
ACCENT_REPLICATION = "#34c759"   # ShotPut Pro Green
ACCENT_REPLICATION_HOVER = "#28a745"
ACCENT_SUCCESS = "#34c759"       # Success Green (same as replication)
ACCENT_WARNING = "#ff9500"       # Warning Orange
ACCENT_WARNING_HOVER = "#e08200"
ACCENT_DANGER = "#ff3b30"        # ShotPut Red
ACCENT_DANGER_HOVER = "#d72c21"
ACCENT_VERIFY = "#6c5ce7"        # Purple for verify button

TEXT_MAIN = "#f5f5f7"
TEXT_MUTED = "#9a9aa0"
TEXT_DIM = "#686870"

# File Status Colors
COLOR_VERIFIED = "#34c759"   # Green ✓
COLOR_COPYING = "#2d7ff9"    # Blue ▶
COLOR_QUEUED = "#686870"     # Gray ░
COLOR_FAILED = "#ff3b30"     # Red ✗

import sys

if sys.platform == "win32":
    FONT_FAMILY = "Segoe UI"
elif sys.platform == "darwin":
    FONT_FAMILY = "Helvetica Neue"
else:
    FONT_FAMILY = "DejaVu Sans"
