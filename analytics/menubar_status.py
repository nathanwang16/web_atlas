"""
menubar_status.py — Web Atlas Menu Bar Status App

Displays server status in macOS menu bar with quick actions.
Requires: pip install rumps requests

Usage: python menubar_status.py
"""

import subprocess
import webbrowser
from pathlib import Path

import requests
import rumps

# ---------- Config ----------
SERVER_URL = "http://127.0.0.1:5000"
LOG_FILE = Path(__file__).parent / "logs" / "events.jsonl"
CHECK_INTERVAL = 30  # seconds


class WebAtlasStatusBar(rumps.App):
    def __init__(self):
        super().__init__("Web Atlas", icon=None, quit_button=None)
        self.server_alive = False
        self.event_count = 0
        self.update_status()
    
    def update_status(self):
        """Check server status and update menu bar."""
        try:
            resp = requests.get(f"{SERVER_URL}/ping", timeout=2)
            self.server_alive = resp.status_code == 200
        except requests.RequestException:
            self.server_alive = False
        
        # Count events
        if LOG_FILE.exists():
            self.event_count = sum(1 for _ in LOG_FILE.open("r", encoding="utf-8"))
        
        # Update title (emoji in menu bar)
        self.title = "🌐" if self.server_alive else "⚠️"
        
        # Update menu items
        self.menu.clear()
        
        status_text = "✅ Server Running" if self.server_alive else "❌ Server Offline"
        self.menu.add(rumps.MenuItem(status_text, callback=None))
        self.menu.add(rumps.separator)
        
        self.menu.add(rumps.MenuItem(f"📊 Events: {self.event_count:,}", callback=None))
        
        if LOG_FILE.exists():
            size_mb = LOG_FILE.stat().st_size / 1024 / 1024
            self.menu.add(rumps.MenuItem(f"💾 Log Size: {size_mb:.1f} MB", callback=None))
        
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("🔄 Refresh Status", callback=self.refresh_clicked))
        self.menu.add(rumps.MenuItem("📂 Open Logs Folder", callback=self.open_logs))
        self.menu.add(rumps.MenuItem("📈 Run Analysis", callback=self.run_analysis))
        self.menu.add(rumps.separator)
        
        if not self.server_alive:
            self.menu.add(rumps.MenuItem("🚀 Start Server", callback=self.start_server))
        
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))
    
    @rumps.timer(CHECK_INTERVAL)
    def periodic_check(self, _):
        """Periodically check server status."""
        self.update_status()
    
    def refresh_clicked(self, _):
        self.update_status()
        rumps.notification(
            title="Web Atlas",
            subtitle="Status Refreshed",
            message=f"Server: {'Online' if self.server_alive else 'Offline'} | Events: {self.event_count:,}"
        )
    
    def open_logs(self, _):
        logs_dir = Path(__file__).parent / "logs"
        subprocess.run(["open", str(logs_dir)])
    
    def run_analysis(self, _):
        script = Path(__file__).parent / "analyse.py"
        subprocess.Popen(["python3", str(script)], cwd=str(script.parent))
        rumps.notification("Web Atlas", "Analysis Started", "Graph will appear shortly...")
    
    def start_server(self, _):
        start_script = Path(__file__).parent.parent / "start_logger.sh"
        if start_script.exists():
            subprocess.Popen(["bash", str(start_script)])
            rumps.notification("Web Atlas", "Starting Server", "Server should be online shortly...")
        else:
            rumps.notification("Web Atlas", "Error", "start_logger.sh not found")


if __name__ == "__main__":
    WebAtlasStatusBar().run()
