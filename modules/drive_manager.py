"""
Octa Intelligence — Google Drive Manager
Handles folder creation and file upload for the Policy Library.
"""
import io
import json
import streamlit as st
from config import (DRIVE_ROOT_FOLDER_NAME, DRIVE_POLICY_SUBFOLDER,
                    DRIVE_TIER_FOLDERS)


@st.cache_resource
def _service():
    """Build and return Google Drive API service."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        # Load credentials from Streamlit secrets
        creds_raw = st.secrets["google"]["credentials_json"]

        # Handle both string and dict formats
        if isinstance(creds_raw, str):
            creds_info = json.loads(creds_raw)
        else:
            # Streamlit may parse TOML into a dict directly
            creds_info = dict(creds_raw)

        creds = Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        svc = build("drive", "v3", credentials=creds)
        return svc
    except Exception as e:
        st.error(f"Google Drive connection failed: {e}")
        return None


def _get_or_create_folder(service, name: str,
                           parent_id: str = None) -> str | None:
    """Find folder by name under parent, create if missing. Returns folder ID."""
    try:
        # Escape single quotes in name
        safe_name = name.replace("'", "\'")
        query = (f"name=\'{safe_name}\' and "
                 f"mimeType=\'application/vnd.google-apps.folder\' and "
                 f"trashed=false")
        if parent_id:
            query += f" and \'{parent_id}\' in parents"

        results = service.files().list(
            q=query, fields="files(id, name)", pageSize=1,
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        files = results.get("files", [])

        if files:
            return files[0]["id"]

        # Create folder
        meta = {
            "name":     name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            meta["parents"] = [parent_id]

        folder = service.files().create(
            body=meta, fields="id",
            supportsAllDrives=True
        ).execute()
        return folder.get("id")
    except Exception as e:
        st.error(f"Drive folder error (\'{name}\'): {e}")
        return None


def test_drive_connection() -> bool:
    """Test that Drive connection works. Returns True if OK."""
    try:
        svc = _service()
        if not svc:
            return False
        # Try listing files — minimal API call
        svc.files().list(pageSize=1, fields="files(id)").execute()
        return True
    except Exception as e:
        st.error(f"Drive test failed: {e}")
        return False


def ensure_policy_folder_structure() -> dict | None:
    """
    Ensures the full folder structure exists in the root folder.
    Returns dict of folder IDs or None on error.
    """
    svc = _service()
    if not svc:
        return None

    try:
        root_id = st.secrets.get("google", {}).get("drive_root_folder_id", "")
        if not root_id:
            st.error("drive_root_folder_id not set in secrets.")
            return None

        # Create Policy Library subfolder inside root
        policy_id = _get_or_create_folder(svc, DRIVE_POLICY_SUBFOLDER, root_id)
        if not policy_id:
            return None

        # Create tier subfolders
        tier_ids = {}
        for tier_key, folder_name in DRIVE_TIER_FOLDERS.items():
            fid = _get_or_create_folder(svc, folder_name, policy_id)
            tier_ids[tier_key] = fid

        return {
            "root_id":       root_id,
            "policy_lib_id": policy_id,
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
    Returns {file_id, drive_url, folder_path} or None on error.
    """
    svc = _service()
    if not svc:
        return None

    try:
        from googleapiclient.http import MediaIoBaseUpload

        folders = ensure_policy_folder_structure()
        if not folders:
            return None

        # Determine parent folder
        tier_folder_id = folders.get(f"{tier}_id") or folders["policy_lib_id"]
        parent_id      = tier_folder_id
        folder_path    = f"Policy Library/{DRIVE_TIER_FOLDERS.get(tier, tier)}"

        # Create category sub-folder if provided
        if category.strip():
            cat_id = _get_or_create_folder(svc, category.strip(), tier_folder_id)
            if cat_id:
                parent_id   = cat_id
                folder_path += f"/{category.strip()}"

        # Upload file
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype=mime_type,
            resumable=False
        )
        meta = {
            "name":    file_name,
            "parents": [parent_id],
        }
        uploaded = svc.files().create(
            body=meta,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()

        file_id  = uploaded.get("id", "")
        view_url = uploaded.get("webViewLink", "")

        # Make file readable by anyone with the link
        try:
            svc.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                supportsAllDrives=True
            ).execute()
        except Exception:
            pass  # Permission setting is optional

        return {
            "file_id":     file_id,
            "drive_url":   view_url,
            "folder_path": folder_path,
        }
    except Exception as e:
        st.error(f"Drive upload error: {e}")
        return None


def delete_drive_file(file_id: str) -> bool:
    """Delete a file from Drive."""
    try:
        svc = _service()
        if not svc or not file_id:
            return False
        svc.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()
        return True
    except Exception:
        return False
