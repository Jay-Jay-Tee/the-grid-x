"""
Grid-X Worker Desktop App - Entry point.

Run from project root:
  python -m worker_app.main
"""

import sys
import os

# Ensure project root is on path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

import customtkinter as ctk

# 90s terminal aesthetic - dark mode, no blue theme
ctk.set_appearance_mode("dark")
# No default theme - we use custom terminal colors everywhere

from worker_app.ui.app import GridXApp


def main():
    app = GridXApp()
    app.mainloop()


if __name__ == "__main__":
    main()
