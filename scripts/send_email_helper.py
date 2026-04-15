"""Helper script to send email via Gmail API. Called by the dashboard."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

def main():
    if len(sys.argv) < 2:
        print("ERROR: No input file provided")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        from gmail_watcher import build_gmail_service, send_email
        creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        service = build_gmail_service(creds_path, token_path)
        result = send_email(service, data["to"], data["subject"], data["body"])
        if result:
            print("SUCCESS")
        else:
            print("FAILED: send_email returned False")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
