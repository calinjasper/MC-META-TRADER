"""
Check which Python processes are running and identify the data source
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def get_python_processes():
    """Get all running Python processes"""
    processes = []
    try:
        if sys.platform == 'win32':
            # Windows: Use tasklist or wmic
            try:
                result = subprocess.run(
                    ['wmic', 'process', 'where', 'name="python.exe"', 'get', 'ProcessId,CommandLine'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                pid = parts[0]
                                cmdline = ' '.join(parts[1:])
                                if 'python' in cmdline.lower() or 'py' in cmdline.lower():
                                    processes.append({
                                        'pid': pid,
                                        'cmdline': cmdline
                                    })
            except Exception as e:
                print(f"[WARNING] Could not use wmic: {e}")
                # Fallback: Use tasklist
                try:
                    result = subprocess.run(
                        ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/V'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        print("[INFO] Found Python processes (using tasklist)")
                        print(result.stdout)
                except Exception as e2:
                    print(f"[WARNING] Could not use tasklist: {e2}")
        else:
            # Linux/Mac: Use ps
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'python' in line.lower():
                        parts = line.split()
                        if len(parts) >= 11:
                            processes.append({
                                'pid': parts[1],
                                'cmdline': ' '.join(parts[10:])
                            })
    except Exception as e:
        print(f"[ERROR] Error getting processes: {e}")
    
    return processes

def check_log_files(project_root):
    """Check log files to see which is actively being written"""
    log_dir = project_root / "logs"
    
    gui_log = log_dir / "trading_platform.log"
    headless_log = log_dir / "trading_platform_headless.log"
    
    results = {}
    
    for log_file, name in [(gui_log, "GUI"), (headless_log, "Headless")]:
        if log_file.exists():
            # Get file modification time
            mtime = os.path.getmtime(log_file)
            mtime_dt = datetime.fromtimestamp(mtime)
            age_seconds = (datetime.now() - mtime_dt).total_seconds()
            
            # Get file size
            size = log_file.stat().st_size
            
            # Read last few lines
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    last_lines = lines[-5:] if len(lines) >= 5 else lines
                    last_line = lines[-1] if lines else ""
            except Exception as e:
                last_lines = [f"[ERROR reading file: {e}"]
                last_line = ""
            
            results[name] = {
                'exists': True,
                'mtime': mtime_dt,
                'age_seconds': age_seconds,
                'size': size,
                'last_lines': last_lines,
                'last_line': last_line
            }
        else:
            results[name] = {
                'exists': False,
                'mtime': None,
                'age_seconds': None,
                'size': 0,
                'last_lines': [],
                'last_line': ""
            }
    
    return results

def identify_script(cmdline):
    """Identify which script is being run from command line"""
    cmdline_lower = cmdline.lower()
    
    if 'main_headless.py' in cmdline_lower or 'headless' in cmdline_lower:
        return "Headless Script"
    elif 'main.py' in cmdline_lower and 'headless' not in cmdline_lower:
        return "GUI Application"
    elif 'trading_platform' in cmdline_lower:
        return "Trading Platform (unknown type)"
    else:
        return "Unknown Python Script"

def main():
    print("=" * 80)
    print("  Checking Running Processes and Data Source")
    print("=" * 80)
    print()
    
    # Get project root
    project_root = Path(__file__).resolve().parent.parent
    
    # Check Python processes
    print("1. Checking Python Processes:")
    print("-" * 80)
    processes = get_python_processes()
    
    if not processes:
        print("[INFO] No Python processes found (or could not detect)")
        print("       This might be because:")
        print("       - No Python scripts are running")
        print("       - Process detection failed (try running as admin)")
        print("       - Application is running as a compiled executable")
    else:
        print(f"[OK] Found {len(processes)} Python process(es):")
        print()
        
        relevant_processes = []
        for proc in processes:
            script_type = identify_script(proc['cmdline'])
            print(f"  PID: {proc['pid']}")
            print(f"  Type: {script_type}")
            print(f"  Command: {proc['cmdline'][:100]}...")
            print()
            
            if 'main' in proc['cmdline'].lower() or 'trading' in proc['cmdline'].lower():
                relevant_processes.append((proc, script_type))
        
        if relevant_processes:
            print(f"[INFO] Found {len(relevant_processes)} relevant trading platform process(es)")
        else:
            print("[INFO] No trading platform processes detected in command line")
    
    print()
    print("-" * 80)
    print()
    
    # Check log files
    print("2. Checking Log Files:")
    print("-" * 80)
    log_results = check_log_files(project_root)
    
    for name, info in log_results.items():
        print(f"\n{name} Application Log:")
        if info['exists']:
            print(f"  [EXISTS] {info['mtime'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Age: {info['age_seconds']:.1f} seconds ago")
            print(f"  Size: {info['size']:,} bytes")
            
            if info['age_seconds'] < 60:
                print(f"  [ACTIVE] Log file was modified recently (likely running)")
            elif info['age_seconds'] < 300:
                print(f"  [RECENT] Log file was modified within last 5 minutes")
            else:
                print(f"  [INACTIVE] Log file hasn't been modified recently")
            
            if info['last_line']:
                print(f"  Last line: {info['last_line'][:80]}...")
        else:
            print(f"  [NOT FOUND] Log file does not exist")
    
    print()
    print("-" * 80)
    print()
    
    # Determine active application
    print("3. Determining Active Application:")
    print("-" * 80)
    
    gui_info = log_results.get('GUI', {})
    headless_info = log_results.get('Headless', {})
    
    gui_active = gui_info.get('exists') and gui_info.get('age_seconds', 999) < 60
    headless_active = headless_info.get('exists') and headless_info.get('age_seconds', 999) < 60
    
    if gui_active and headless_active:
        print("[WARNING] Both GUI and Headless applications appear to be running!")
        print("          This could cause duplicate data storage.")
    elif gui_active:
        print("[RESULT] GUI Application is ACTIVE (storing data)")
        print("         Log: logs/trading_platform.log")
    elif headless_active:
        print("[RESULT] Headless Script is ACTIVE (storing data)")
        print("         Log: logs/trading_platform_headless.log")
    elif gui_info.get('exists') or headless_info.get('exists'):
        print("[INFO] Log files exist but haven't been modified recently")
        print("       Application may have stopped or is not storing data")
    else:
        print("[INFO] No log files found")
        print("       Neither application appears to be running")
    
    print()
    print("=" * 80)
    print()
    print("To check recent data storage activity, run:")
    print("  python tools/check_abbvm_data.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED]")
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

