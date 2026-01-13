"""
Start script for PocketBase Data Viewer
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from data_viewer.config import HOST, PORT, DEBUG

if __name__ == "__main__":
    print("=" * 70)
    print("Starting PocketBase Data Viewer")
    print("=" * 70)
    print(f"Server will be available at: http://{HOST}:{PORT}")
    print(f"Dashboard: http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    uvicorn.run(
        "data_viewer.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )

