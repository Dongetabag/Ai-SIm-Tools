#!/usr/bin/env python3
"""
Simple static file server to serve the frontend HTML file
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8080

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/ai_enhanced_ui.html' # Serve the AI-enhanced UI
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # Change to the directory containing HTML files
    os.chdir(Path(__file__).parent)
    
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"🎵 AISim Tools Frontend Server")
        print(f"📱 Frontend: http://localhost:{PORT}")
        print(f"🔗 API Server: http://localhost:8000")
        print(f"🛑 Press Ctrl+C to stop")
        print()
        
        # Open browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}')
            print("🌐 Browser opened automatically!")
        except:
            print("⚠️  Could not open browser automatically")
        
        print()
        httpd.serve_forever()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Server stopped!")
