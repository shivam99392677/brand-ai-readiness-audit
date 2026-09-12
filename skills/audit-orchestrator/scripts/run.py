#!/usr/bin/env python3
"""CLI wrapper script for the Audit Orchestrator skill."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator import main

if __name__ == "__main__":
    main()
