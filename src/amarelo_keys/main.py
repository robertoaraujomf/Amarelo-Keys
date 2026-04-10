#!/usr/bin/env python3
"""
Amarelo Keys - Keyboard remapping utility
Helps users with defective keyboards by allowing custom key combinations
"""
import sys
import signal
import argparse
from .daemon import KeyRemapperDaemon
from .config import ConfigManager


def main():
    parser = argparse.ArgumentParser(
        description="Amarelo Keys - Keyboard Remapping Utility"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background daemon"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch configuration GUI"
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the running daemon"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show daemon status"
    )
    
    args = parser.parse_args()
    
    if args.stop:
        _stop_daemon()
        return
    
    if args.status:
        _show_status()
        return
    
    if args.gui:
        from .gui import launch_gui
        launch_gui()
        return
    
    if args.daemon or not args.gui:
        daemon = KeyRemapperDaemon()
        signal.signal(signal.SIGINT, lambda *_: daemon.stop())
        signal.signal(signal.SIGTERM, lambda *_: daemon.stop())
        daemon.start()


def _stop_daemon():
    import os
    pid_file = "/tmp/amarelo-keys.pid"
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print("Daemon stopped")
        except ProcessLookupError:
            print("Daemon not running")
        os.remove(pid_file)
    else:
        print("Daemon not running")


def _show_status():
    import os
    pid_file = "/tmp/amarelo-keys.pid"
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"Daemon running (PID: {pid})")
        except ProcessLookupError:
            print("Daemon not running (stale PID file)")
    else:
        print("Daemon not running")


if __name__ == "__main__":
    main()
