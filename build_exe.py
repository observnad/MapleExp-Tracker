import os
import subprocess
import sys

def build():
    print("=== Building MapleEXPTracker Standalone Executable ===")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "MapleEXPTracker",
        "--icon", "icon.ico",
        "--add-data", "icon.ico;.",
        "--collect-all", "customtkinter",
        "--collect-all", "PIL",
        "--collect-all", "windows_capture",
        "src/app.py"
    ]
    
    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("Build failed with return code:", res.returncode)
        sys.exit(res.returncode)
    else:
        exe_path = os.path.abspath("dist/MapleEXPTracker.exe")
        print("\n=======================================================")
        print(f"BUILD SUCCESSFUL!")
        print(f"Executable created at: {exe_path}")
        print(f"Size: {os.path.getsize(exe_path) / (1024 * 1024):.2f} MB")
        print("=======================================================")

if __name__ == "__main__":
    build()
