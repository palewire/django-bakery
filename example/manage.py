#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
