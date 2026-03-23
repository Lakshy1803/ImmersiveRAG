import os
import sys
import shutil

def unlock_qdrant():
    print("--- Qdrant Database Unlocker ---")
    
    # Resolve the path to data/qdrant
    qdrant_path = os.path.join(os.getcwd(), "data", "qdrant")
    lock_file = os.path.join(qdrant_path, ".lock")
    
    if not os.path.exists(lock_file):
        print("[INFO] No lock file found. Qdrant should be ready.")
        return

    print(f"[WARN] Found lock file at: {lock_file}")
    
    # On Windows, we can't easily check for the specific PID in a cross-platform way 
    # but we can attempt a force delete.
    try:
        os.remove(lock_file)
        print("[SUCCESS] Successfully deleted the lock file.")
    except PermissionError:
        print("[FAIL] Permission Denied. Another process is STILL using the database.")
        print("       Action: Please close any running 'python' processes in Task Manager and try again.")
    except Exception as e:
        print(f"[ERROR] Failed to delete lock: {e}")

if __name__ == "__main__":
    unlock_qdrant()
