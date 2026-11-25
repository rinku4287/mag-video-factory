"""
One-time helper to generate YT_REFRESH_TOKEN for GitHub Actions Secrets.

Steps:
1. Go to https://console.cloud.google.com -> Create Project -> Enable "YouTube Data API v3".
2. OAuth Consent Screen -> External -> Add your Google account as a Test User.
3. Credentials -> Create OAuth Client ID -> Desktop App -> Download client_secret.json into this folder.
4. Run:  python scripts/get_youtube_token.py client_secret.json
5. Copy the printed YT_CLIENT_ID, YT_CLIENT_SECRET, and YT_REFRESH_TOKEN into GitHub Repo Secrets.
"""

import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/get_youtube_token.py path/to/client_secret.json")
        sys.exit(1)
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    print("\n=== COPY THESE INTO GITHUB REPO SECRETS ===")
    print("YT_CLIENT_ID     =", creds.client_id)
    print("YT_CLIENT_SECRET =", creds.client_secret)
    print("YT_REFRESH_TOKEN =", creds.refresh_token)


if __name__ == "__main__":
    main()
