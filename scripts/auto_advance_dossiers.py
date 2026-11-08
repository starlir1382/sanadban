#!/usr/bin/env python
"""
Standalone runner script for auto_advance_dossiers.
Can be executed directly via:
    python scripts/auto_advance_dossiers.py [--confirm]
"""
import os
import sys
import django

# Setup Django environment
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.management import call_command

if __name__ == "__main__":
    args = sys.argv[1:]
    call_command("auto_advance_dossiers", *args)
