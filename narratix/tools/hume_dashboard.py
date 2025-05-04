#!/usr/bin/env python3
"""
Hume AI dashboard tool for Narratix.
Provides a dashboard to monitor and analyze emotion data from Hume AI.
"""
import argparse
import sys
from pathlib import Path
import json
import webbrowser
import http.server
import socketserver
import threading
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from narratix.utils.config import settings

# HTML template for the dashboard
DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Narratix - Hume AI Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; border-radius: 5px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart { height: 300px; margin-top: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
        .metric { text-align: center; padding: 20px; }
        .metric h3 { margin: 0; color: #666; }
        .metric .value { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .emotions { display: flex; flex-wrap: wrap; gap: 10px; }
        .emotion { padding: 8px 12px; border-radius: 20px; background: #e0e0e0; display: inline-block; }
        .positive { background: #d4edda; color: #155724; }
        .negative { background: #f8d7da; color: #721c24; }
        .neutral { background: #e2e3e5; color: #383d41; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <h1>Narratix - Hume AI Dashboard</h1>
        <p>Data last updated: <span id="last-updated">Loading...</span></p>
        
        <div class="card">
            <h2>Overview</h2>
            <div class="grid">
                <div class="metric">
                    <h3>Analyzed Text Segments</h3>
                    <div class="value" id="segment-count">-</div>
                </div>
                <div class="metric">
                    <h3>Characters</h3>
                    <div class="value" id="character-count">-</div>
                </div>
                <div class="metric">
                    <h3>Top Emotion</h3>
                    <div class="value" id="top-emotion">-</div>
                </div>
                <div class="metric">
                    <h3>Emotional Variance</h3>
                    <div class="value" id="emotion-variance">-</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Emotion Distribution</h2>
            <div class="chart">
                <canvas id="emotion-chart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>Character Emotions</h2>
            <div id="character-emotions">Loading...</div>
        </div>
    </div>
    
    <script>
        // Mock data - would be replaced with actual API data
        const mockData = {
            lastUpdated: new Date().toISOString(),
            segmentCount: 42,
            characterCount: 5,
            topEmotion: "Joy",
            emotionVariance: "High",
            emotionDistribution: {
                Joy: 35,
                Sadness: 15,
                Anger: 12,
                Fear: 8,
                Surprise: 18,
                Disgust: 5,
                Neutral: 7
            },
            characterEmotions: {
                "Character 1": ["Joy", "Excitement", "Anticipation"],
                "Character 2": ["Sadness", "Fear", "Anxiety"],
                "Character 3": ["Anger", "Frustration", "Determination"],
                "Character 4": ["Surprise", "Confusion", "Curiosity"],
                "Character 5": ["Neutral", "Calm", "Thoughtful"]
            }
        };
        
        // Update the UI with data
        document.getElementById('last-updated').textContent = new Date(mockData.lastUpdated).toLocaleString();
        document.getElementById('segment-count').textContent = mockData.segmentCount;
        document.getElementById('character-count').textContent = mockData.characterCount;
        document.getElementById('top-emotion').textContent = mockData.topEmotion;
        document.getElementById('emotion-variance').textContent = mockData.emotionVariance;
        
        // Create emotion chart
        const ctx = document.getElementById('emotion-chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(mockData.emotionDistribution),
                datasets: [{
                    label: 'Emotion Frequency',
                    data: Object.values(mockData.emotionDistribution),
                    backgroundColor: [
                        '#ffcc00', // Joy
                        '#6699cc', // Sadness
                        '#ff6666', // Anger
                        '#99cc99', // Fear
                        '#cc99cc', // Surprise
                        '#669999', // Disgust
                        '#cccccc'  // Neutral
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // Display character emotions
        const characterContainer = document.getElementById('character-emotions');
        characterContainer.innerHTML = '';
        
        for (const [character, emotions] of Object.entries(mockData.characterEmotions)) {
            const characterDiv = document.createElement('div');
            characterDiv.className = 'card';
            
            const characterTitle = document.createElement('h3');
            characterTitle.textContent = character;
            characterDiv.appendChild(characterTitle);
            
            const emotionsDiv = document.createElement('div');
            emotionsDiv.className = 'emotions';
            
            for (const emotion of emotions) {
                const emotionSpan = document.createElement('span');
                emotionSpan.className = 'emotion';
                emotionSpan.textContent = emotion;
                emotionsDiv.appendChild(emotionSpan);
            }
            
            characterDiv.appendChild(emotionsDiv);
            characterContainer.appendChild(characterDiv);
        }
        
        // In a real implementation, this would fetch data from an API
        function fetchDashboardData() {
            // This would be an API call in a real implementation
            console.log("Would fetch dashboard data here");
        }
        
        // Initial data fetch
        fetchDashboardData();
        
        // Refresh data every 30 seconds
        setInterval(fetchDashboardData, 30000);
    </script>
</body>
</html>
"""

def parse_args():
    parser = argparse.ArgumentParser(description="Narratix Hume AI Dashboard")
    parser.add_argument(
        "--port", 
        type=int,
        default=8050,
        help="Port for the dashboard server"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )
    return parser.parse_args()

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        else:
            self.send_error(404)

def start_server(port):
    handler = DashboardHandler
    httpd = socketserver.TCPServer(("", port), handler)
    print(f"Serving dashboard at http://localhost:{port}")
    httpd.serve_forever()

def main():
    args = parse_args()
    
    # Start server in a thread
    server_thread = threading.Thread(target=start_server, args=(args.port,))
    server_thread.daemon = True
    server_thread.start()
    
    # Open browser if not disabled
    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.port}")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Dashboard server stopped.")

if __name__ == "__main__":
    main()
