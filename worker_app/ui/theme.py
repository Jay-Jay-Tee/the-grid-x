"""
90s Hacking Terminal Theme - Enhanced with more retro computer vibes.
Inspired by classic terminals, DOS, and early cyberpunk aesthetics.
"""

# Core palette - Matrix/Terminal green
BG_DARK = "#0a0a0a"       # Near black background
BG_PANEL = "#0d0d0d"      # Slightly lighter for panels
BG_DARKEST = "#050505"    # For depth effects
GREEN = "#00ff41"         # Matrix/hacker green
GREEN_DIM = "#00cc33"     # Dimmer green for secondary
GREEN_DARK = "#009922"    # Dark green for subtle elements
GREEN_BRIGHT = "#39ff14"  # Bright accent neon green
GREEN_GLOW = "#00ff00"    # Pure green for glow effects
GREEN_NEON = "#00dd38"    # Slightly dimmed neon for terminal borders (less eye strain)

# Accent colors - Classic terminal palette
AMBER = "#ffb000"         # Amber for warnings (like old terminals)
CYAN = "#00ffff"          # Cyan accent
MAGENTA = "#ff00ff"       # Magenta accent
RED = "#ff3333"           # Error red
RED_BRIGHT = "#ff0033"    # Bright alert red
RED_BORDER = "#cc2222"    # Darker red for terminate button border (visible, not washed out)
GRAY = "#4a4a4a"          # Muted gray
GRAY_DARK = "#2a2a2a"     # Dark gray for borders
GRAY_LIGHT = "#6a6a6a"    # Light gray for disabled

# Tab selected: clearly visible green tint, text stays readable
TAB_SELECTED_BG = "#0f2812"
TAB_SELECTED_HOVER_BG = "#123018"

# Font - Terminal monospace
TERMINAL_FONT = ("Consolas", 14)
TERMINAL_FONT_SMALL = ("Consolas", 12)
TERMINAL_FONT_LARGE = ("Consolas", 16)
TERMINAL_FONT_TITLE = ("Consolas", 20, "bold")
TERMINAL_FONT_MEGA = ("Consolas", 24, "bold")

# Button style - terminal look with hover states
BTN_FG = BG_PANEL
BTN_TEXT = GREEN
BTN_BORDER = GREEN_DIM
BTN_HOVER = GREEN_DIM

# Animation timing (milliseconds)
ANIM_CURSOR_BLINK = 500
ANIM_PULSE_FAST = 400
ANIM_PULSE_SLOW = 800
ANIM_SCAN_LINE = 100
