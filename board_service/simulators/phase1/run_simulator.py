import subprocess
import sys
import time
import os
import signal

def run():
    print("🚀 Starting Phase 1 Simulator (Database & Encryption)...")
    
    # Path setup
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Start Backend
    print("Starting FastAPI Backend on http://localhost:8001...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=current_dir
    )
    
    time.sleep(3) # Give backend time to initialize SQLite
    
    # Start Frontend
    print("Starting Streamlit Frontend...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend.py", "--server.port", "8501"],
        cwd=current_dir
    )
    
    print("\n✅ Simulator is running!")
    print("👉 Backend: http://localhost:8001")
    print("👉 Frontend: http://localhost:8501")
    print("\nPress Ctrl+C to stop the simulator.")
    
    try:
        while True:
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("Backend process terminated unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("Frontend process terminated unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping simulator...")
    finally:
        backend_process.terminate()
        frontend_process.terminate()
        print("Simulator shutdown complete.")

if __name__ == "__main__":
    run()
