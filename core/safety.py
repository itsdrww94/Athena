"""
Athena Safety Module
====================
Security checks, secret redaction, and safety gates.
"""

import re
import os
from typing import List, Set

# Patterns to redact from logs
SECRET_PATTERNS = [
    # API Keys
    re.compile(r'(api[_-]?key\s*[=:]\s*)["\']?[\w-]{20,}["\']?', re.IGNORECASE),
    re.compile(r'(bearer\s+)[\w-]{20,}', re.IGNORECASE),
    re.compile(r'(sk-[a-zA-Z0-9]{20,})', re.IGNORECASE),  # OpenAI
    re.compile(r'(AIza[a-zA-Z0-9_-]{35})', re.IGNORECASE),  # Google
    re.compile(r'(ghp_[a-zA-Z0-9]{36})', re.IGNORECASE),  # GitHub
    
    # Passwords
    re.compile(r'(password\s*[=:]\s*)["\']?[^\s"\']{8,}["\']?', re.IGNORECASE),
    re.compile(r'(secret\s*[=:]\s*)["\']?[^\s"\']{8,}["\']?', re.IGNORECASE),
    
    # Tokens
    re.compile(r'(token\s*[=:]\s*)["\']?[\w-]{20,}["\']?', re.IGNORECASE),
    
    # Credit cards (basic pattern)
    re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
    
    # SSN pattern
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
]

# Dangerous shell commands to block
BLOCKED_COMMANDS: Set[str] = {
    # File system destruction
    "rm -rf /",
    "rm -rf /*",
    "del /s /q c:\\",
    "format c:",
    "mkfs",
    
    # System modification
    "shutdown",
    "reboot",
    "halt",
    
    # Network attacks
    "nc -l",
    "nmap",
    
    # Crypto miners
    "xmrig",
    "minerd",
}

# Paths that should never be written to
BLOCKED_PATHS: Set[str] = {
    "/etc/passwd",
    "/etc/shadow",
    "C:\\Windows\\System32",
    "C:\\Windows\\system.ini",
}


def redact_secrets(text: str) -> str:
    """
    Redact sensitive information from text.
    
    Args:
        text: Input text that may contain secrets
        
    Returns:
        Text with secrets replaced by [REDACTED]
    """
    result = text
    
    for pattern in SECRET_PATTERNS:
        # For patterns with groups, preserve the prefix
        if pattern.groups:
            result = pattern.sub(r'\1[REDACTED]', result)
        else:
            result = pattern.sub('[REDACTED]', result)
    
    return result


def is_command_safe(command: str) -> dict:
    """
    Check if a shell command is safe to execute.
    
    Args:
        command: Shell command to check
        
    Returns:
        Dict with 'safe', 'reason' keys
    """
    command_lower = command.lower().strip()
    
    # Check exact matches
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in command_lower:
            return {
                "safe": False,
                "reason": f"Blocked command pattern: {blocked}"
            }
    
    # Check for dangerous patterns
    dangerous_patterns = [
        (r"rm\s+-rf\s+/", "Recursive delete from root"),
        (r">\s*/dev/sd", "Direct disk write"),
        (r"dd\s+if=.*of=/dev", "Direct disk write"),
        (r"chmod\s+777\s+/", "Dangerous permissions"),
        (r"curl.*\|\s*sh", "Remote code execution"),
        (r"wget.*\|\s*sh", "Remote code execution"),
    ]
    
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, command_lower):
            return {
                "safe": False,
                "reason": reason
            }
    
    return {"safe": True, "reason": "OK"}


def is_path_safe(path: str) -> dict:
    """
    Check if a file path is safe to write to.
    
    Args:
        path: File path to check
        
    Returns:
        Dict with 'safe', 'reason' keys
    """
    path_normalized = os.path.normpath(path)
    
    # Block system paths
    for blocked in BLOCKED_PATHS:
        if path_normalized.lower().startswith(blocked.lower()):
            return {
                "safe": False,
                "reason": f"System path blocked: {blocked}"
            }
    
    # Block paths outside project
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not path_normalized.startswith(project_dir):
        # Allow temp and user dirs
        allowed_prefixes = [
            os.path.expanduser("~"),
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
        ]
        if not any(path_normalized.startswith(p) for p in allowed_prefixes if p):
            return {
                "safe": False,
                "reason": "Path outside allowed directories"
            }
    
    return {"safe": True, "reason": "OK"}


def sanitize_for_log(data: dict) -> dict:
    """
    Sanitize a dictionary for safe logging.
    
    Redacts values for sensitive keys.
    """
    sensitive_keys = {
        "password", "secret", "token", "key", "api_key",
        "apikey", "auth", "credential", "private"
    }
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        if any(s in key_lower for s in sensitive_keys):
            result[key] = "[REDACTED]"
        elif isinstance(value, str):
            result[key] = redact_secrets(value)
        elif isinstance(value, dict):
            result[key] = sanitize_for_log(value)
        else:
            result[key] = value
    
    return result


def check_rate_limit(user_id: str, action: str, limit: int = 10, window_seconds: int = 60) -> dict:
    """
    Simple in-memory rate limiting.
    
    Returns:
        Dict with 'allowed', 'remaining', 'reset_in' keys
    """
    # Simple implementation - in production use Redis
    import time
    
    # Use module-level cache
    if not hasattr(check_rate_limit, "_cache"):
        check_rate_limit._cache = {}
    
    cache = check_rate_limit._cache
    key = f"{user_id}:{action}"
    now = time.time()
    
    # Clean old entries
    cache[key] = [t for t in cache.get(key, []) if now - t < window_seconds]
    
    if len(cache[key]) >= limit:
        oldest = min(cache[key])
        return {
            "allowed": False,
            "remaining": 0,
            "reset_in": int(window_seconds - (now - oldest))
        }
    
    cache[key].append(now)
    return {
        "allowed": True,
        "remaining": limit - len(cache[key]),
        "reset_in": 0
    }
