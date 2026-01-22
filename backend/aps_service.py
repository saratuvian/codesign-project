import os
import math
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("APS_CLIENT_ID")
CLIENT_SECRET = os.getenv("APS_CLIENT_SECRET")
APS_BUCKET_KEY = os.getenv("APS_BUCKET_KEY")
APS_BASE_URL = os.getenv("APS_BASE_URL", "https://developer.api.autodesk.com")

AUTH_URL = f"{APS_BASE_URL}/authentication/v2/token"

# In APS Signed S3 Upload: each part except the last must be at least 5MB.
MIN_PART_SIZE = 5 * 1024 * 1024


def get_aps_token() -> dict:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("APS_CLIENT_ID / APS_CLIENT_SECRET are not set in .env")

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "data:read data:write bucket:create bucket:read code:all",
    }

    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=30)
    if resp.status_code == 200:
        return resp.json()

    raise Exception(f"APS authentication failed: {resp.status_code} {resp.text}")


def _get_access_token() -> str:
    return get_aps_token()["access_token"]


def create_bucket_if_needed() -> dict:
    if not APS_BUCKET_KEY:
        raise RuntimeError("APS_BUCKET_KEY is not set in .env")

    url = f"{APS_BASE_URL}/oss/v2/buckets"
    access_token = _get_access_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    body = {"bucketKey": APS_BUCKET_KEY, "policyKey": "persistent"}

    resp = requests.post(url, json=body, headers=headers, timeout=30)

    # 200/201 success, 409 already exists
    if resp.status_code in (200, 201, 409):
        data = {}
        if resp.text:
            try:
                data = resp.json()
            except Exception:
                data = {"raw_text": resp.text}
        return {"status": resp.status_code, "data": data}

    raise Exception(f"Bucket creation failed: {resp.status_code} {resp.text}")


def get_signed_s3_download_url(object_name: str, minutes_expiration: int = 10) -> dict:
    """
    Generate a signed S3 download URL for an object in the configured bucket.
    Endpoint: GET .../signeds3download
    """
    if not APS_BUCKET_KEY:
        raise RuntimeError("APS_BUCKET_KEY is not set in .env")

    access_token = _get_access_token()
    safe_object_name = urllib.parse.quote(object_name, safe="")

    url = f"{APS_BASE_URL}/oss/v2/buckets/{APS_BUCKET_KEY}/objects/{safe_object_name}/signeds3download"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"minutesExpiration": minutes_expiration}

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code == 200:
        return resp.json()

    raise Exception(f"Signed download failed: {resp.status_code} {resp.text}")


def _get_signed_upload_urls(object_name: str, parts: int, first_part: int = 1) -> dict:
    """
    Request signed S3 upload URLs from APS.
    Endpoint: GET .../signeds3upload?parts=N&firstPart=1
    """
    if not APS_BUCKET_KEY:
        raise RuntimeError("APS_BUCKET_KEY is not set in .env")

    access_token = _get_access_token()
    safe_object_name = urllib.parse.quote(object_name, safe="")

    url = f"{APS_BASE_URL}/oss/v2/buckets/{APS_BUCKET_KEY}/objects/{safe_object_name}/signeds3upload"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"parts": parts, "firstPart": first_part}

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code == 200:
        return resp.json()

    raise Exception(f"Get signed upload URLs failed: {resp.status_code} {resp.text}")


def _complete_signed_upload(object_name: str, upload_key: str, parts_payload: list[dict]) -> dict:
    """
    Finalize a signed S3 upload in APS.
    Endpoint: POST .../signeds3upload
    Body: { uploadKey, parts: [{part, etag}, ...] }
    """
    if not APS_BUCKET_KEY:
        raise RuntimeError("APS_BUCKET_KEY is not set in .env")

    access_token = _get_access_token()
    safe_object_name = urllib.parse.quote(object_name, safe="")

    url = f"{APS_BASE_URL}/oss/v2/buckets/{APS_BUCKET_KEY}/objects/{safe_object_name}/signeds3upload"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    body = {"uploadKey": upload_key, "parts": parts_payload}

    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code in (200, 201):
        if resp.text:
            try:
                return resp.json()
            except Exception:
                return {"raw_text": resp.text}
        return {}

    raise Exception(f"Complete signed upload failed: {resp.status_code} {resp.text}")


def upload_file_signed_s3(file_path: str, object_name: str) -> dict:
    """
    Upload a local file to APS OSS using Signed S3 upload flow.
    """
    if not APS_BUCKET_KEY:
        raise RuntimeError("APS_BUCKET_KEY is not set in .env")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)

    # Determine part sizes. If > 5MB then use 5MB parts.
    if file_size <= MIN_PART_SIZE:
        total_parts = 1
        part_size = file_size
    else:
        total_parts = math.ceil(file_size / MIN_PART_SIZE)
        part_size = MIN_PART_SIZE

    signed = _get_signed_upload_urls(object_name, parts=total_parts, first_part=1)
    upload_key = signed.get("uploadKey")
    urls = signed.get("urls", [])

    if not upload_key or len(urls) != total_parts:
        raise Exception(f"Unexpected signed upload response: {signed}")

    parts_payload: list[dict] = []

    with open(file_path, "rb") as f:
        for i in range(total_parts):
            part_number = i + 1
            chunk = f.read(part_size)
            if chunk is None or len(chunk) == 0:
                raise Exception(f"Unexpected EOF while reading part {part_number}")

            put_resp = requests.put(urls[i], data=chunk, timeout=60)
            if put_resp.status_code not in (200, 201):
                raise Exception(
                    f"S3 PUT failed for part {part_number}: {put_resp.status_code} {put_resp.text}"
                )

            etag = put_resp.headers.get("ETag") or put_resp.headers.get("etag")
            if not etag:
                raise Exception(f"Missing ETag for part {part_number}")

            etag = etag.strip('"')
            parts_payload.append({"part": part_number, "etag": etag})

    return _complete_signed_upload(object_name, upload_key, parts_payload)
