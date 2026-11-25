"""
Multi-Platform Auto-Publishers for My Admission Guru:
  1. YouTube Data API v3 (16:9 Long Video + 9:16 Shorts)
  2. Facebook Page Reels (Meta Graph API 3-step upload)
  3. Instagram Reels (Meta Graph API using temporary GitHub Release asset URL, then auto-cleanup)
  4. My Admission Guru Callback (POST /api/video-callback to auto-embed YouTube video on the relevant page)
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


GRAPH_VERSION = "v21.0"


# ---------- 1. YouTube Data API v3 ----------
def _youtube_client():
    cid = os.getenv("YT_CLIENT_ID", "").strip()
    csec = os.getenv("YT_CLIENT_SECRET", "").strip()
    rtok = os.getenv("YT_REFRESH_TOKEN", "").strip()
    if not (cid and csec and rtok):
        return None
    creds = Credentials(
        token=None,
        refresh_token=rtok,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cid,
        client_secret=csec,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def upload_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy: str = "public",
) -> str:
    yt = _youtube_client()
    if yt is None:
        print("[youtube] Skipped: YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN not set.")
        return ""

    body = {
        "snippet": {
            "title": title[:99],
            "description": description[:4900],
            "tags": tags[:15],
            "categoryId": "27",  # Education
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = str(resp.get("id", ""))
    print(f"[youtube] Uploaded {video_path.name} -> https://youtu.be/{vid}")
    return vid


# ---------- 2. Facebook Page Reels (Meta Graph API) ----------
def upload_facebook_reel(video_path: Path, caption: str) -> str:
    page_id = os.getenv("FB_PAGE_ID", "").strip()
    token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not (page_id and token):
        print("[facebook] Skipped: FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN not set.")
        return ""

    # Step 1: Initialize upload session
    init_resp = requests.post(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/video_reels",
        data={"upload_phase": "start", "access_token": token},
        timeout=30,
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()
    video_id = init_data["video_id"]
    upload_url = init_data["upload_url"]

    # Step 2: Upload binary MP4
    file_bytes = video_path.read_bytes()
    up_resp = requests.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(len(file_bytes)),
            "Content-Type": "application/octet-stream",
        },
        data=file_bytes,
        timeout=120,
    )
    up_resp.raise_for_status()

    # Step 3: Publish Reel
    fin_resp = requests.post(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/video_reels",
        data={
            "access_token": token,
            "video_id": video_id,
            "upload_phase": "finish",
            "video_state": "PUBLISHED",
            "description": caption[:2000],
        },
        timeout=60,
    )
    fin_resp.raise_for_status()
    print(f"[facebook] Published Reel -> video_id={video_id}")
    return str(video_id)


# ---------- 3. Instagram Reels (Meta Graph API + Temporary GitHub Release Asset) ----------
def _gh_temp_upload(video_path: Path, tag_name: str) -> tuple[str, int]:
    """Uploads MP4 to a temporary GitHub release so Instagram Graph API can fetch a public URL."""
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    if not (repo and gh_token):
        return "", 0
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {gh_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    rel_resp = requests.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers=headers,
        json={"tag_name": tag_name, "name": tag_name, "prerelease": True, "body": "Temp reel host"},
        timeout=30,
    )
    rel_resp.raise_for_status()
    rel = rel_resp.json()
    rel_id = int(rel["id"])
    upload_url = rel["upload_url"].split("{")[0] + f"?name={video_path.name}"
    up_resp = requests.post(
        upload_url,
        headers={**headers, "Content-Type": "video/mp4"},
        data=video_path.read_bytes(),
        timeout=120,
    )
    up_resp.raise_for_status()
    return str(up_resp.json()["browser_download_url"]), rel_id


def _gh_temp_cleanup(rel_id: int, tag_name: str) -> None:
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    gh_token = os.getenv("GITHUB_TOKEN", "").strip()
    if not (repo and gh_token and rel_id):
        return
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {gh_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    requests.delete(f"https://api.github.com/repos/{repo}/releases/{rel_id}", headers=headers, timeout=20)
    requests.delete(f"https://api.github.com/repos/{repo}/git/refs/tags/{tag_name}", headers=headers, timeout=20)


def upload_instagram_reel(video_path: Path, caption: str, update_id: int) -> str:
    ig_user_id = os.getenv("IG_USER_ID", "").strip()
    token = os.getenv("IG_ACCESS_TOKEN", "").strip() or os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not (ig_user_id and token):
        print("[instagram] Skipped: IG_USER_ID or IG_ACCESS_TOKEN not set.")
        return ""

    tag_name = f"tmp-reel-{update_id}-{int(time.time())}"
    public_url, rel_id = _gh_temp_upload(video_path, tag_name)
    if not public_url:
        print("[instagram] Skipped: GITHUB_TOKEN/GITHUB_REPOSITORY needed to host temporary video URL.")
        return ""

    try:
        # Step 1: Create Reels media container
        c_resp = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{ig_user_id}/media",
            data={
                "media_type": "REELS",
                "video_url": public_url,
                "caption": caption[:2100],
                "share_to_feed": "true",
                "access_token": token,
            },
            timeout=60,
        )
        c_resp.raise_for_status()
        creation_id = c_resp.json()["id"]

        # Step 2: Poll until container status is FINISHED
        for _ in range(30):
            time.sleep(5)
            st_resp = requests.get(
                f"https://graph.facebook.com/{GRAPH_VERSION}/{creation_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=30,
            )
            st_resp.raise_for_status()
            code = st_resp.json().get("status_code", "")
            if code == "FINISHED":
                break
            if code == "ERROR":
                raise RuntimeError(f"Instagram processing failed: {st_resp.text}")

        # Step 3: Publish Reel
        p_resp = requests.post(
            f"https://graph.facebook.com/{GRAPH_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": token},
            timeout=60,
        )
        p_resp.raise_for_status()
        media_id = str(p_resp.json().get("id", ""))
        print(f"[instagram] Published Reel -> media_id={media_id}")
        return media_id
    finally:
        _gh_temp_cleanup(rel_id, tag_name)


# ---------- 4. Callback to myadmissionguru.com (Embed YouTube Video on Page) ----------
def notify_mag_callback(
    callback_url: str,
    update_id: int,
    youtube_id: str,
    youtube_short_id: str,
) -> bool:
    secret = os.getenv("MAG_CALLBACK_SECRET", "").strip()
    if not (callback_url and secret and update_id and (youtube_id or youtube_short_id)):
        print("[callback] Skipped: missing callback_url, MAG_CALLBACK_SECRET, update_id, or video ID.")
        return False

    resp = requests.post(
        callback_url,
        headers={"X-MAG-Secret": secret, "Content-Type": "application/json"},
        json={
            "update_id": update_id,
            "youtube_id": youtube_id,
            "youtube_short_id": youtube_short_id,
        },
        timeout=20,
    )
    if resp.ok:
        print(f"[callback] Embedded video on myadmissionguru.com update #{update_id}: {resp.text}")
        return True
    print(f"[callback] Failed ({resp.status_code}): {resp.text}")
    return False
