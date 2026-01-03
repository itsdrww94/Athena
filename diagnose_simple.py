
import sys
import os
import subprocess
from pathlib import Path

def log(msg):
    try:
        print(msg) # Print to console too
        with open("diagnosis_v4.log", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception as e:
        pass

# Clear previous log
if Path("diagnosis_v4.log").exists():
    Path("diagnosis_v4.log").unlink()

log("--- Starting Diagnosis v4 ---")

# 3. Check Jarvis
log("3. Checking Jarvis...")
try:
    cmd = [sys.executable, "agents/jarvis_runner.py", "itsdrww"]
    log(f"Running: {' '.join(cmd)}")
    # Timeout 20s to be faster
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    log(f"Jarvis Return Code: {res.returncode}")
    log(f"Jarvis Stdout:\n{res.stdout}")
    if res.stderr:
        log(f"Jarvis Stderr:\n{res.stderr}")
except subprocess.TimeoutExpired as e:
    log("❌ Jarvis TIMED OUT!")
    if e.stdout:
         log(f"Partial Stdout:\n{e.stdout}")
    if e.stderr:
         log(f"Partial Stderr:\n{e.stderr}")
except Exception as e:
    log(f"Jarvis failed to run: {e}")

# 4. Check Hakari
log("4. Checking Hakari...")
try:
    cmd = [sys.executable, "agents/parlay/agent.py", "--command", "/check Kevin Durant pts 26.5"]
    log(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    log(f"Hakari Return Code: {res.returncode}")
    log(f"Hakari Stdout:\n{res.stdout}")
    if res.stderr:
         log(f"Hakari Stderr:\n{res.stderr}")
except subprocess.TimeoutExpired as e:
    log("❌ Hakari TIMED OUT!")
    if e.stdout:
         log(f"Partial Stdout:\n{e.stdout}")
    if e.stderr:
         log(f"Partial Stderr:\n{e.stderr}")
except Exception as e:
    log(f"Hakari failed to run: {e}")

log("--- End Diagnosis ---")
