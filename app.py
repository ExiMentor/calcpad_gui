#!/usr/bin/env python3
"""Compatibility launcher for existing desktop files and python3 app.py."""
from calcpad_gui.application import CalcpadApp, CalcpadWindow, main, run_doctor

if __name__ == "__main__":
    raise SystemExit(main())
