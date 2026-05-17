"""
shadowvault/upload.py
Stage 5 - YouTube Upload with OAuth2.

YouTubeUploader class holds the authenticated API service as state.
Supports public / unlisted / private uploads with resumable upload + progress tracking.
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from shadowvault.models import UploadResult, VideoResult, ContentResult
from shadowvault.utils.file_manager import archive_file

logger = logging.getLogger(__name__)

SCOPES: list[str] = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_CATEGORY_ID: str = "24"  # Entertainment

DEFAULT_TAGS: list[str] = [
    "shorts", "horror", "mystery", "scary", "creepypasta", "fyp", "viral",
]

UPLOAD_CHUNKSIZE: int = -1  # single-request upload


class YouTubeUploader:
    """
    Stateful YouTube uploader.

    Usage:
        uploader = YouTubeUploader()
        result = uploader.upload(video_result, content_result)
    """

    def __init__(
        self,
        client_secrets: str | None = None,
        token_file: str | None = None,
        archive_folder: str | None = None,
    ) -> None:
        from shadowvault.config import get_config
        cfg = get_config()

        self.client_secrets = client_secrets or cfg.client_secrets_file
        self.token_file = token_file or cfg.token_pickle_file
        self.archive_folder = archive_folder or cfg.archive_folder
        self._service = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _load_credentials(self):
        if not os.path.exists(self.token_file):
            return None
        with open(self.token_file, "rb") as fh:
            return pickle.load(fh)

    def _save_credentials(self, creds) -> None:
        with open(self.token_file, "wb") as fh:
            pickle.dump(creds, fh)
        logger.debug("Token saved to %s", self.token_file)

    def authenticate(self) -> bool:
        """
        Ensure valid credentials via:
        1. Load existing token
        2. Refresh if expired
        3. Browser-based OAuth flow if needed

        Returns True on success.
        """
        creds = self._load_credentials()

        if creds and creds.valid:
            logger.debug("Existing YouTube credentials are valid")
        elif creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired YouTube credentials")
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
            except Exception as exc:
                logger.error("Token refresh failed: %s", exc)
                creds = None
        else:
            creds = None

        if creds is None:
            if not os.path.exists(self.client_secrets):
                logger.error(
                    "client_secrets.json not found at %s - run auth_setup.py first",
                    self.client_secrets,
                )
                return False
            try:
                logger.info("Starting OAuth flow - browser will open")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets, SCOPES
                )
                creds = flow.run_local_server(port=0)
                self._save_credentials(creds)
            except Exception as exc:
                logger.error("OAuth flow failed: %s", exc)
                return False

        try:
            self._service = build("youtube", "v3", credentials=creds)
            logger.info("YouTube API service authenticated successfully")
            return True
        except Exception as exc:
            logger.error("Failed to build YouTube service: %s", exc)
            return False

    def _ensure_authenticated(self) -> bool:
        if self._service is not None:
            return True
        return self.authenticate()

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload(
        self,
        video: VideoResult,
        content: ContentResult,
        privacy: str = "public",
        extra_tags: Optional[list[str]] = None,
    ) -> UploadResult:
        """
        Upload a rendered video to YouTube.

        Parameters
        ----------
        video   : VideoResult from Stage 4
        content : ContentResult from Stage 1
        privacy : "public" | "unlisted" | "private"
        """
        if not os.path.isfile(video.video_path):
            msg = f"Video file not found: {video.video_path}"
            logger.error(msg)
            return UploadResult(success=False, error_message=msg)

        if not self._ensure_authenticated():
            return UploadResult(success=False, error_message="YouTube authentication failed")

        description = (
            f"{content.script}\n\n"
            "Follow for more scary content!\n\n"
            f"{content.tags}"
        )

        tag_string = content.tags.replace("#", "")
        parsed_tags = [t.strip() for t in tag_string.split() if t.strip()]
        all_tags = list(dict.fromkeys(DEFAULT_TAGS + parsed_tags + (extra_tags or [])))

        request_body = {
            "snippet": {
                "title": content.title[:100],
                "description": description[:4900],
                "tags": all_tags[:500],
                "categoryId": YOUTUBE_CATEGORY_ID,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        logger.info("Uploading '%s' as %s ...", content.title[:60], privacy)

        try:
            media = MediaFileUpload(
                video.video_path,
                chunksize=UPLOAD_CHUNKSIZE,
                resumable=True,
            )
            request = self._service.videos().insert(
                part="snippet,status",
                body=request_body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info("Upload progress: %d%%", int(status.progress() * 100))

            video_id: str = response.get("id", "")
            youtube_url = f"https://www.youtube.com/shorts/{video_id}"
            logger.info("Upload complete: %s", youtube_url)

            archived = archive_file(video.video_path, self.archive_folder)

            return UploadResult(
                success=True,
                video_id=video_id,
                youtube_url=youtube_url,
                archived_path=archived,
            )

        except Exception as exc:
            logger.error("YouTube upload failed: %s", exc)
            return UploadResult(success=False, error_message=str(exc))
