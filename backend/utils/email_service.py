"""
Gmail API Email Service wrapper.
Invokes backend/utils/gmailService.js via Node.js subprocess.
All Gmail OAuth credentials remain server-side only.
"""

import os
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

def send_password_reset_email(to_email: str, user_name: str, reset_url: str) -> dict:
    """
    Send a password reset email using Gmail API (via gmailService.js subprocess).

    Args:
        to_email:   Recipient email address
        user_name:  Recipient's display name
        reset_url:  Full URL containing the raw reset token (sent in email body)

    Returns:
        dict with keys: success (bool), messageId (str|None), error (str|None)
    """
    if not to_email or not user_name or not reset_url:
        return {"success": False, "error": "Missing required arguments"}

    base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path  = os.path.join(base_dir, "utils", "gmailService.js")

    if not os.path.exists(script_path):
        logger.error("gmailService.js not found at %s", script_path)
        return {"success": False, "error": "Gmail service script missing"}

    cmd = ["node", script_path, to_email, user_name, reset_url]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )

        # Parse JSON from stdout
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    payload = json.loads(line)
                    if payload.get("success"):
                        logger.info("Gmail API sent to %s (msgId=%s)", to_email, payload.get("messageId"))
                    else:
                        # Log detail to server log — do not bubble up to client
                        logger.error("Gmail API error: %s", payload.get("error"))
                    return payload
                except json.JSONDecodeError:
                    continue

        # Unexpected output — log stderr for debugging
        logger.error("gmailService.js unexpected output.\nstdout: %s\nstderr: %s",
                     result.stdout, result.stderr)
        return {"success": False, "error": "Email service returned unexpected response"}

    except subprocess.TimeoutExpired:
        logger.error("gmailService.js timed out for %s", to_email)
        return {"success": False, "error": "Email service timed out"}
    except Exception as exc:
        logger.exception("Error invoking Gmail service")
        return {"success": False, "error": str(exc)}
