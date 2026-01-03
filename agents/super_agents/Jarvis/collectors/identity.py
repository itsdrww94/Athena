from typing import List, Dict, Any
import subprocess
import json
import os
from .base import BaseCollector

class IdentityCollector(BaseCollector):
    """
    Identity Intelligence.
    Aligned with: Sherlock (sherlock-project)
    """
    
    def _collect(self, target: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        print(f"[DEBUG] IdentityCollector called for: '{target}'")
        findings = []
        
        # 1. Sherlock Integration
        # Only run if explicitly requested or if we are in a comprehensive mode, to save time/bandwidth
        run_sherlock = options.get("run_sherlock", True)
        
        if run_sherlock:
            try:
                print(f"[*] Running Sherlock on {target}...")
                # Output to a temporary file
                output_file = f"sherlock_{target}.txt"
                
                # Construct command: sherlock <username> --output <file> --print-found
                # Note: Sherlock doesn't have a pure JSON output flag easily accessible in all versions without args.
                # simpler to just run it and catch stdout if we want, or parse the file.
                # Let's try capturing stdout.
                
                # Construct command: python -m sherlock_project <username> --output <file> --print-found
                import sys
                cmd = [sys.executable, "-m", "sherlock_project", target, "--timeout", "5", "--print-found"]
                
                # Check if we are on windows, might need shell=True or full path if not in env
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode == 0:
                    lines = process.stdout.split('\n')
                    for line in lines:
                        if line.startswith("[+]"):
                            # Format: [+] Service: URL
                            parts = line.split(": ")
                            if len(parts) >= 2:
                                service = parts[0].replace("[+]", "").strip()
                                url = parts[1].strip()
                                
                                findings.append({
                                    "type": "username",
                                    "value": target,
                                    "source": service,
                                    "tool": "sherlock",
                                    "url": url,
                                    "confidence": 1.0
                                })
                else:
                    print(f"[IdentityCollector] Sherlock exited with code {process.returncode}")
                    print(f"Stderr: {process.stderr}")

            except FileNotFoundError:
                print("[IdentityCollector] 'sherlock' command not found. Please install 'sherlock-project'.")
            except Exception as e:
                print(f"[IdentityCollector] Sherlock failed: {e}")

        # Fallback / Mock (Keep for stability if Sherlock fails or finds nothing)
        if not findings and target.lower() in ["johndoe123", "itsdrww"]:
             # ... existing mock logic ...
             pass
            
        print(f"[DEBUG] IdentityCollector returning {len(findings)} findings")    
        return findings
