"""Simple HTTP server for the P&L dashboard."""

from __future__ import annotations

import json

from get_me_money.config import DASHBOARD_DB


def main() -> None:
    """Run a minimal HTTP server exposing the dashboard JSON."""
    try:
        from http.server import HTTPServer, SimpleHTTPRequestHandler
    except ImportError:
        print("http.server not available")
        return

    class DashboardHandler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/" or self.path == "/dashboard":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if DASHBOARD_DB.exists():
                    self.wfile.write(DASHBOARD_DB.read_bytes())
                else:
                    from get_me_money.dashboard import compute_pnl, save_pnl
                    snap = compute_pnl()
                    save_pnl(snap)
                    self.wfile.write(DASHBOARD_DB.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass  # Silence request logs

    server = HTTPServer(("0.0.0.0", 8080), DashboardHandler)
    print("Dashboard server running on http://0.0.0.0:8080")
    server.serve_forever()


if __name__ == "__main__":
    main()
