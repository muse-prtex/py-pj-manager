#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility launcher.

The GUI now lives in the package at src/pj_manager/app.py (run it with
run.bat or `python -m pj_manager.app`). This shim keeps the old habit of
`py pjman.py` working.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pj_manager.app import main

if __name__ == "__main__":
    main()
