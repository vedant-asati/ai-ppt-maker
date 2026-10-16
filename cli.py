#!/usr/bin/env python3
"""
AI Presentation Agency — Command-Line Interface.

Usage:
  python cli.py init        # create config.yaml
  python cli.py generate    # build presentation.pdf
  python cli.py audit       # run design quality audit
  python cli.py fonts       # download fonts for offline rendering
"""

import sys
from ppt_maker.cli import main

if __name__ == "__main__":
    main()
