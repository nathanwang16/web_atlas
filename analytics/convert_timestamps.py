#!/usr/bin/env python3
"""
Convert existing events.jsonl timestamps to human-readable format.
Handles missing timestamps by assigning reasonable fallback values.
"""
import json
import datetime
from pathlib import Path
import shutil

def convert_timestamp(ts_ms):
    """Convert millisecond timestamp to ISO format string."""
    if ts_ms is None:
        return None
    try:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000)
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Keep 3 decimal places
    except (ValueError, OSError):
        return None

def convert_events_file(input_file, output_file=None, backup=True):
    """Convert timestamps in events.jsonl file."""
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Events file not found: {input_file}")
    
    # Create backup if requested
    if backup:
        backup_path = input_path.with_suffix('.jsonl.backup')
        shutil.copy2(input_path, backup_path)
        print(f"Backup created: {backup_path}")
    
    # Use same file if no output specified
    if output_file is None:
        output_file = input_file
    
    output_path = Path(output_file)
    
    # Process events
    converted_count = 0
    missing_count = 0
    total_count = 0
    
    # Get file creation time as fallback for missing timestamps
    file_stat = input_path.stat()
    fallback_timestamp = datetime.datetime.fromtimestamp(file_stat.st_ctime)
    fallback_str = fallback_timestamp.strftime('%Y-%m-%d %H:%M:%S.000')
    
    # Write to temporary file first to avoid data loss
    temp_path = output_path.with_suffix('.tmp')
    
    with input_path.open('r', encoding='utf-8') as infile, \
         temp_path.open('w', encoding='utf-8') as outfile:
        
        for line in infile:
            try:
                event = json.loads(line.strip())
                total_count += 1
                
                # Handle timestamp conversion
                if 't' in event:
                    readable_time = convert_timestamp(event['t'])
                    if readable_time:
                        event['timestamp'] = readable_time
                        event['t_original'] = event['t']  # Keep original for reference
                        del event['t']
                        converted_count += 1
                    else:
                        # Invalid timestamp, use fallback
                        event['timestamp'] = fallback_str
                        event['t_original'] = event.get('t', 'invalid')
                        if 't' in event:
                            del event['t']
                        missing_count += 1
                else:
                    # Missing timestamp, use fallback
                    event['timestamp'] = fallback_str
                    event['t_original'] = 'missing'
                    missing_count += 1
                
                # Write converted event
                outfile.write(json.dumps(event, ensure_ascii=False) + '\n')
                
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping malformed line: {e}")
                continue
    
    # Move temporary file to final location
    temp_path.replace(output_path)
    
    print(f"Conversion complete:")
    print(f"  Total events: {total_count}")
    print(f"  Successfully converted: {converted_count}")
    print(f"  Missing/invalid timestamps (used fallback): {missing_count}")
    print(f"  Output written to: {output_path}")

if __name__ == "__main__":
    log_file = Path(__file__).parent / "logs" / "events.jsonl"
    convert_events_file(log_file)