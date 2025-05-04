#!/usr/bin/env python3
"""
Resource monitor tool for Narratix.
Monitors system resources used by the application.
"""
import argparse
import psutil
import time
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from narratix.utils.config import settings

def parse_args():
    parser = argparse.ArgumentParser(description="Narratix Resource Monitor")
    parser.add_argument(
        "--interval", 
        type=int,
        default=5,
        help="Sampling interval in seconds"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path for metrics (default: stdout)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after collecting N samples"
    )
    return parser.parse_args()

def get_process_by_name(name="python"):
    """Find all Python processes potentially running Narratix."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == name:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'narratix' in cmdline.lower():
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def collect_metrics(process=None):
    """Collect system and process metrics."""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
        }
    }
    
    if process and process.is_running():
        try:
            with process.oneshot():
                metrics["process"] = {
                    "pid": process.pid,
                    "cpu_percent": process.cpu_percent(),
                    "memory_percent": process.memory_percent(),
                    "memory_mb": process.memory_info().rss / (1024 * 1024),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "status": process.status()
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            metrics["process"] = {"status": "not_accessible"}
    else:
        metrics["process"] = {"status": "not_running"}
        
    return metrics

def main():
    args = parse_args()
    
    output_file = None
    if args.output:
        output_file = open(args.output, 'w')
    
    count = 0
    
    try:
        while True:
            process = get_process_by_name()
            metrics = collect_metrics(process)
            
            if args.json:
                output = json.dumps(metrics)
            else:
                # Simple formatted output
                output = (
                    f"[{metrics['timestamp']}] "
                    f"CPU: {metrics['system']['cpu_percent']}% | "
                    f"MEM: {metrics['system']['memory_percent']}% | "
                    f"DISK: {metrics['system']['disk_usage_percent']}%"
                )
                
                if metrics['process']['status'] != 'not_running':
                    output += (
                        f" | Process: "
                        f"CPU: {metrics['process'].get('cpu_percent', 'N/A')}% | "
                        f"MEM: {metrics['process'].get('memory_mb', 'N/A'):.1f} MB"
                    )
            
            if output_file:
                output_file.write(output + "\n")
                output_file.flush()
            else:
                print(output)
            
            count += 1
            if args.limit and count >= args.limit:
                break
                
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Monitoring stopped.")
    finally:
        if output_file:
            output_file.close()

if __name__ == "__main__":
    main()
