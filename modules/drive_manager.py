"""
Octa Intelligence — Google Drive Manager
Handles folder creation and file upload for the Policy Library.
Uses Google Drive API v3 with service account credentials.
"""
import io
import streamlit as st
from config import (DRIVE_ROOT_FOLDER_NAME, DRIVE_POLICY_SUBFOLDER,
                    DRIVE_TIER_FOLDERS)


def _service():
    """Build and return Google Drive API service."""
    try:
        import json
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds_json = st.secrets["google"]["credentials_json"]
        if isinstance(creds_json, str):
            creds_info = json.loads(creds_json)
        else:
            creds_info = dict(creds_json)

        creds = Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"Google Drive connection failed: {e}")
        return None


def _get_or_create_folder(service, name: str,
                           parent_id: str = None) -> str | None:
    """Find a folder by name under parent, create it if missing. Returns folder ID."""
    try:
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(
            q=query, fields="files(id, name)", pageSize=1
        ).execute()
        files = results.get("files", [])

        if files:
            return files[0]["id"]

        # Create
        meta = {
            "name":     name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            meta["parents"] = [parent_id]

        folder = service.files().create(body=meta, fields="id").execute()
        return folder["id"]
    except Exception as e:
        st.error(f"Drive folder error: {e}")
        return None


def ensure_policy_folder_structure() -> dict | None:
    """
    Ensures the full folder structure exists.
    Returns dict of folder IDs:
    {root_id, policy_lib_id, core_id, programme_id, call_specific_id}
    """
    svc = _service()
    if not svc:
        return None

    try:
        # Try to get root folder ID from secrets, else find/create
        root_id = st.secrets.get("google", {}).get("drive_root_folder_id", "")
        if not root_id:
            root_id = _get_or_create_folder(svc, DRIVE_ROOT_FOLDER_NAME)
        if not root_id:
            return None

        policy_id = _get_or_create_folder(svc, DRIVE_POLICY_SUBFOLDER, root_id)
        if not policy_id:
            return None

        tier_ids = {}
        for tier_key, folder_name in DRIVE_TIER_FOLDERS.items():
            fid = _get_or_create_folder(svc, folder_name, policy_id)
            tier_ids[tier_key] = fid

        return {
            "root_id":        root_id,
            "policy_lib_id":  policy_id,
            **{f"{k}_id": v for k, v in tier_ids.items()}
        }
    except Exception as e:
        st.error(f"Drive structure error: {e}")
        return None


def upload_policy_document(file_bytes: bytes, file_name: str,
                            mime_type: str, tier: str,
                            category: str = "") -> dict | None:
    """
    Upload a policy document to the correct Drive folder.
    Returns dict with {file_id, drive_url, folder_path} or None on error.
    """
    svc = _service()
    if not svc:
        return None

    try:
        folders = ensure_policy_folder_structure()
        if not folders:
            return None

        # Put in tier folder; create category sub-folder if given
        tier_folder_id = folders.get(f"{tier}_id")
        if not tier_folder_id:
            tier_folder_id = folders["policy_lib_id"]

        parent_id = tier_folder_id
        folder_path = f"Policy Library/{DRIVE_TIER_FOLDERS.get(tier,tier)}"

        if category:
            cat_id = _get_or_create_folder(svc, category, tier_folder_id)
            if cat_id:
                parent_id   = cat_id
                folder_path += f"/{category}"

        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype=mime_type,
            resumable=True
        )
        meta = {"name": file_name, "parents": [parent_id]}
        f    = svc.files().create(
            body=meta, media_body=media, fields="id, webViewLink"
        ).execute()

        # Make publicly readable (view only)
        svc.permissions().create(
            fileId=f["id"],
            body={"type": "anyone", "role": "reader"}
        ).execute()

        return {
            "file_id":     f["id"],
            "drive_url":   f.get("webViewLink",""),
            "folder_path": folder_path,
        }
    except Exception as e:
        st.error(f"Drive upload error: {e}")
        return None


def delete_drive_file(file_id: str) -> bool:
    """Move a file to trash in Drive."""
    try:
        svc = _service()
        if not svc: return False
        svc.files().delete(fileId=file_id).execute()
        return True
    except Exception:
        return False
