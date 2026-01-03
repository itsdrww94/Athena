
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 for Windows Console
sys.stdout.reconfigure(encoding='utf-8')

def check_env():
    print("\n--- 1. Environment Check ---")
    load_dotenv()
    required = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY"]
    missing = []
    for key in required:
        val = os.getenv(key)
        if not val:
            missing.append(key)
        else:
            print(f"✅ {key} is set (len={len(val)})")
    
    if missing:
        print(f"❌ Missing keys: {missing}")
    else:
        print("✅ All required keys present.")

def check_athena_remote():
    print("\n--- 2. Athena Remote Check ---")
    try:
        from athena_remote import AthenaRemote
        print("✅ Successfully imported AthenaRemote")
        # Try instantiation (might fail if services not ready)
        bot = AthenaRemote()
        print(f"✅ Successfully instantiated AthenaRemote. Ready? {bot.is_ready}")
    except ImportError as e:
        print(f"❌ Failed to import AthenaRemote: {e}")
    except Exception as e:
        print(f"❌ Failed to instantiate AthenaRemote: {e}")

def check_jarvis():
    print("\n--- 3. Jarvis Agent Check ---")
    cmd = [sys.executable, "agents/jarvis_runner.py", "itsdrww"]
    try:
        print("Running Jarvis test (timeout 30s)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Jarvis ran successfully.")
            # Verify output content roughly
            if "risk_score" in result.stdout or "JARVIS REPORT" in result.stdout:
                print("✅ Output looks valid.")
            else:
                print("⚠️ Output might be empty or invalid.")
                print(result.stdout[:500])
        else:
            print("❌ Jarvis failed.")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
    except subprocess.TimeoutExpired:
        print("❌ Jarvis timed out.")
    except Exception as e:
        print(f"❌ Jarvis execution error: {e}")

def check_hakari():
    print("\n--- 4. Hakari Agent Check ---")
    # /check Kevin Durant pts 26.5
    cmd = [sys.executable, "agents/parlay/agent.py", "--command", "/check Kevin Durant pts 26.5"]
    try:
        print("Running Hakari test...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # Hakari might return non-zero if it's just a CLI tool processing a command, but usually 0 is success.
        if result.returncode == 0:
            print("✅ Hakari ran successfully.")
            print("Output snippet:")
            print(result.stdout[:500])
        else:
            print("❌ Hakari failed.")
            print("STDERR:", result.stderr)
            print("STDOUT:", result.stdout)
    except Exception as e:
        print(f"❌ Hakari execution error: {e}")

if __name__ == "__main__":
    check_env()
    check_athena_remote()
    check_jarvis()
    check_hakari()
