#!/usr/bin/env python3
"""
Launcher script for Anki Danish Vocabulary Generator TUI
"""

import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    required = [
        'textual',
        'rich', 
        'py_ankiconnect',
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Missing required packages:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\n📦 Install with: pip install -r requirements.txt")
        return False
    
    return True

def check_modules():
    """Check if custom modules exist."""
    required_files = ['tts.py', 'gemini.py']
    missing = []
    
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print("⚠️  Missing custom modules:")
        for file in missing:
            print(f"   - {file}")
        print("\n💡 Make sure your TTS and Gemini modules are in this directory")
        return False
    
    return True

def main():
    """Launch the TUI application."""
    print("🚀 Starting Anki Danish Vocabulary Generator...\n")
    
    if not check_dependencies():
        sys.exit(1)
    
    if not check_modules():
        print("\n⚠️  Continuing anyway - errors may occur during processing")
    
    print("✅ All checks passed!\n")
    
    try:
        from anki_tui import main as tui_main
        tui_main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
