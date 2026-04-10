#!/usr/bin/env python3
import sys
import os
import signal
import argparse

sys.path.insert(0, '/usr/share/amarelo-keys')

from amarelo_keys.config import ConfigManager
from amarelo_keys.daemon import KeyRemapperDaemon

PID_FILE = "/tmp/amarelo-keys.pid"


def stop_daemon():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print("Daemon stopped")
        except ProcessLookupError:
            print("Daemon not running")
        os.remove(PID_FILE)
    else:
        print("Daemon not running")


def show_status():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"Daemon running (PID: {pid})")
        except ProcessLookupError:
            print("Daemon not running (stale PID file)")
    else:
        print("Daemon not running")


def main():
    parser = argparse.ArgumentParser(prog='amarelo-keys', description="Amarelo Keys - Keyboard Remapping Utility")
    parser.add_argument('--daemon', action='store_true', help='Run as background daemon')
    parser.add_argument('--gui', action='store_true', help='Launch configuration GUI')
    parser.add_argument('--stop', action='store_true', help='Stop the running daemon')
    parser.add_argument('--status', action='store_true', help='Show daemon status')
    
    args = parser.parse_args()
    
    if args.stop:
        stop_daemon()
        return
    
    if args.status:
        show_status()
        return
    
    if args.gui or (not args.daemon and not args.stop and not args.status):
        from amarelo_keys.gui import launch_gui
        launch_gui()
        return
    
    if args.daemon:
        daemon = KeyRemapperDaemon()
        signal.signal(signal.SIGINT, lambda *_: daemon.stop())
        signal.signal(signal.SIGTERM, lambda *_: daemon.stop())
        daemon.start()


if __name__ == "__main__":
    main()
