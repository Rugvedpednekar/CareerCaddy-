import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Callable


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
OTP_SUBJECT_TERMS = ("otp", "verification code", "confirm")
OTP_PATTERN = re.compile(r"(?<!\d)(?:\d[\s-]?){4,8}(?!\d)")


def _decode(data: str | None) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="ignore")


def _body_text(payload: dict) -> str:
    text = _decode((payload.get("body") or {}).get("data"))
    for part in payload.get("parts") or []:
        text += "\n" + _body_text(part)
    return text


def extract_numeric_code(text: str) -> str | None:
    for match in OTP_PATTERN.findall(text or ""):
        code = re.sub(r"\D", "", match)
        if 4 <= len(code) <= 8:
            return code
    return None


def build_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials_path = Path(os.getenv("GMAIL_OAUTH_CLIENT_FILE", "~/.careercaddy/gmail_credentials.json")).expanduser()
    token_path = Path(os.getenv("GMAIL_OAUTH_TOKEN_FILE", "~/.careercaddy/gmail_token.json")).expanduser()
    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), [GMAIL_READONLY_SCOPE])
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), [GMAIL_READONLY_SCOPE])
        credentials = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


class OTPHandler:
    def __init__(
        self,
        service=None,
        sleep_fn: Callable[[float], None] = time.sleep,
        input_fn: Callable[[str], str] = input,
    ):
        self.service = service
        self.sleep_fn = sleep_fn
        self.input_fn = input_fn

    def _latest_code(self, portal_domain: str) -> str | None:
        if self.service is None:
            self.service = build_gmail_service()
        query = f'is:unread newer_than:1d from:({portal_domain}) (subject:OTP OR subject:"verification code" OR subject:confirm)'
        result = self.service.users().messages().list(userId="me", q=query, maxResults=10).execute()
        for summary in result.get("messages", []):
            message = self.service.users().messages().get(userId="me", id=summary["id"], format="full").execute()
            payload = message.get("payload") or {}
            headers = {item.get("name", "").lower(): item.get("value", "") for item in payload.get("headers") or []}
            subject = headers.get("subject", "")
            sender = headers.get("from", "")
            if portal_domain.lower() not in sender.lower():
                continue
            if not any(term in subject.lower() for term in OTP_SUBJECT_TERMS):
                continue
            code = extract_numeric_code(subject + "\n" + _body_text(payload))
            if code:
                return code
        return None

    def wait_for_code(self, portal_domain: str, attempts: int = 5, interval: float = 5.0) -> str | None:
        for attempt in range(attempts):
            code = self._latest_code(portal_domain)
            if code:
                return code
            if attempt < attempts - 1:
                self.sleep_fn(interval)
        manual = self.input_fn("OTP was not found in Gmail. Enter it manually (or press Enter to abort): ").strip()
        return extract_numeric_code(manual)
