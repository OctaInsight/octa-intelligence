"""Octa Intelligence - Google Drive Manager"""
import io
import json
import streamlit as st
from config import DRIVE_POLICY_SUBFOLDER, DRIVE_TIER_FOLDERS


def _get_credentials():
    """
    Load Google service account credentials from Streamlit secrets.
    Handles TOML triple-quoted strings where private_key \n
    sequences become literal newlines (invalid JSON).
    """
    creds_raw = st.secrets["google"]["credentials_json"]

    # Already a dict/mapping (Streamlit parsed the TOML inline table)
    if not isinstance(creds_raw, str):
        return dict(creds_raw)

    creds_str = creds_raw.strip()

    # Direct parse — works if JSON is on one line or already correct
    try:
        return json.loads(creds_str)
    except json.JSONDecodeError:
        pass

    # Fix: private_key has real newlines instead of \n sequences
    # Find the private key block and escape real newlines inside it
    import re
    def fix_key(m):
        inner = m.group(2)
        # Replace real newlines with the JSON escape sequence
        inner = inner.replace('\r\n', '\\n').replace('\n', '\\n')
        return m.group(1) + inner + m.group(3)

    fixed = re.sub(
        r'("private_key"\s*:\s*")([\s\S]*?)(?<!\\)(")',
        fix_key,
        creds_str
    )

    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse Google credentials JSON: {e}\n"
            "Tip: In Streamlit Cloud secrets, paste the entire JSON "
            "inside triple quotes using the credentials_json key."
        )


def _build_service():
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_service_account_info(
            _get_credentials(),
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        st.error(f"Drive auth failed: {e}")
        return None


def test_drive_connection():
    try:
        svc = _build_service()
        if not svc:
            return False, "Could not build Drive service."
        root_id = st.secrets.get("google", {}).get("drive_root_folder_id", "")
        if not root_id:
            return False, "drive_root_folder_id missing from secrets."
        meta = svc.files().get(
            fileId=root_id, fields="id,name", supportsAllDrives=True
        ).execute()
        return True, f"Connected - folder: {meta.get('name', root_id)}"
    except Exception as e:
        return False, f"Error: {e}"


def _get_or_create_folder(svc, name, parent_id):
    try:
        q = (
            "'" + parent_id + "' in parents"
            " and name = '" + name + "'"
            " and mimeType = 'application/vnd.google-apps.folder'"
            " and trashed = false"
        )
        resp = svc.files().list(
            q=q, fields="files(id,name)", pageSize=5,
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        files = resp.get("files", [])
        if files:
            return files[0]["id"]
        folder = svc.files().create(
            body={"name": name,
                  "mimeType": "application/vnd.google-apps.folder",
                  "parents": [parent_id]},
            fields="id", supportsAllDrives=True
        ).execute()
        return folder.get("id")
    except Exception as e:
        st.error(f"Folder {name}: {e}")
        return None


def _ensure_structure(svc):
    root_id = st.secrets.get("google", {}).get("drive_root_folder_id", "")
    if not root_id:
        st.error("drive_root_folder_id missing.")
        return None
    policy_id = _get_or_create_folder(svc, DRIVE_POLICY_SUBFOLDER, root_id)
    if not policy_id:
        return None
    tier_ids = {"policy_lib": policy_id}
    for tier_key, folder_name in DRIVE_TIER_FOLDERS.items():
        tier_ids[tier_key] = _get_or_create_folder(svc, folder_name, policy_id)
    return tier_ids


def upload_policy_document(file_bytes, file_name, mime_type, tier, category=""):
    svc = _build_service()
    if not svc:
        return None
    try:
        from googleapiclient.http import MediaIoBaseUpload
        tier_ids = _ensure_structure(svc)
        if not tier_ids:
            return None
        parent_id   = tier_ids.get(tier) or tier_ids["policy_lib"]
        folder_path = "Policy Library/" + DRIVE_TIER_FOLDERS.get(tier, tier)
        if category.strip():
            cat_id = _get_or_create_folder(svc, category.strip(), parent_id)
            if cat_id:
                parent_id    = cat_id
                folder_path += "/" + category.strip()
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes), mimetype=mime_type, resumable=False
        )
        uploaded = svc.files().create(
            body={"name": file_name, "parents": [parent_id]},
            media_body=media, fields="id,webViewLink",
            supportsAllDrives=True
        ).execute()
        file_id  = uploaded.get("id", "")
        view_url = uploaded.get("webViewLink", "")
        try:
            svc.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                supportsAllDrives=True
            ).execute()
        except Exception:
            pass
        return {"file_id": file_id, "drive_url": view_url, "folder_path": folder_path}
    except Exception as e:
        st.error(f"Drive upload failed: {e}")
        return None


def delete_drive_file(file_id):
    if not file_id:
        return False
    try:
        svc = _build_service()
        if not svc:
            return False
        svc.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        return True
    except Exception:
        return False
