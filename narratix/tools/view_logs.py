#!/usr/bin/env python3
"""
Log viewer tool for Narratix.
Allows viewing and filtering logs from the command line.
"""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from narratix.utils.config import settings

def parse_args():
    parser = argparse.ArgumentParser(description="Narratix Log Viewer")
    parser.add_argument(
        "--level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Filter logs by level"
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Filter logs by date (YYYYMMDD)"
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=None,
        help="Show only the last N lines"
    )
    parser.add_argument(
        "--search",
        default=None,
        help="Search for a specific string in logs"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    return parser.parse_args()

def get_log_file(date=None):
    logs_dir = Path(settings.logs_dir)
    if not logs_dir.exists():
        print(f"Logs directory {logs_dir} does not exist")
        sys.exit(1)
        
    if date:
        log_file = logs_dir / f"narratix_{date}.log"
    else:
        today = datetime.now().strftime("%Y%m%d")
        log_file = logs_dir / f"narratix_{today}.log"
        
    if not log_file.exists():
        print(f"Log file {log_file} does not exist")
        sys.exit(1)
        
    return log_file

def process_logs(args):
    log_file = get_log_file(args.date)
    
    lines = log_file.read_text().splitlines()
    
    # Process and filter logs
    filtered_logs = []
    for line in lines:
        if args.search and args.search not in line:
            continue
            
        try:
            # Try to parse as JSON if structured logging is enabled
            if settings.structured_logging:
                log_entry = json.loads(line)
                if args.level and log_entry.get("level") != args.level:
                    continue
                filtered_logs.append(log_entry if args.json else line)
            else:
                # Simple string filtering for non-structured logs
                if args.level and f" - {args.level} - " not in line:
                    continue
                filtered_logs.append(line)
        except json.JSONDecodeError:
            # Fall back to treating as plain text
            if args.level and f" - {args.level} - " not in line:
                continue
            filtered_logs.append(line)
    
    # Apply tail if requested
    if args.tail and len(filtered_logs) > args.tail:
        filtered_logs = filtered_logs[-args.tail:]
    
    return filtered_logs

def main():
    args = parse_args()
    logs = process_logs(args)
    
    if args.json:
        print(json.dumps(logs, indent=2))
    else:
        for log in logs:
            print(log)

if __name__ == "__main__":
    main()
