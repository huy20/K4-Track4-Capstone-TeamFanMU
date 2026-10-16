"""
VinRobotics Waste Sorter Sim - Integrated Backend Server
Connects Python modules/tracker.py with the 3D Simulator frontend.
Supports both REST API and live simulation stream.
"""

import json
import http.server
import socketserver
import os
import sys
from modules.tracker import WasteTemporalUncertaintyTracker, KalmanFilter3D

PORT = 8080
tracker = WasteTemporalUncertaintyTracker(
    window_size=5,
    min_consensus=4,
    max_error_mm=25.0,
    min_confidence=0.65,
    reject_error_mm=50.0,
)

frame_counter = 140

class SimulatorHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        global frame_counter
        if self.path == "/api/track":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid JSON"}')
                return

            geometric_items = data.get("geometric_items", [])
            sim_gt = data.get("sim_ground_truth", None)
            frame_id = data.get("frame_id", frame_counter)
            frame_counter += 1

            # Gọi trực tiếp module Thành viên 3: WasteTemporalUncertaintyTracker
            tracked_state = tracker.update(geometric_items, sim_gt)

            raw_pos = [0.0, 0.0, 0.0]
            if geometric_items and len(geometric_items) > 0:
                raw_pos = geometric_items[0].get("target_world_3d", [0.0, 0.0, 0.0])

            log_trace = tracker.format_log(frame_id, raw_pos, tracked_state, sim_gt)

            # In trace chuẩn ra console
            print(f"\n{log_trace}")

            response_payload = {
                "frame_id": frame_id,
                "tracked_state": tracked_state,
                "log_trace": log_trace,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))

        elif self.path == "/api/reset":
            tracker.reset()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "reset_success"}')
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with socketserver.TCPServer(("", PORT), SimulatorHandler) as httpd:
        print("=" * 70)
        print(f"  VinRobotics Simulator Server running at: http://localhost:{PORT}/simulator.html")
        print("  Integrated with Member 3: modules/tracker.py (Kalman 3D & Uncertainty)")
        print("=" * 70)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == "__main__":
    run_server()
