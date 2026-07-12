"""
compat.py -- Windows UTF-8 console fix

Import this at the top of any file that prints emoji.
Harmless on Mac/Linux.
"""
import sys
import os

def fix_encoding():
    """Reconfigure stdout/stderr to UTF-8 on Windows if needed."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

fix_encoding()

# Also set PYTHONUTF8 for any child processes
os.environ['PYTHONUTF8'] = '1'
