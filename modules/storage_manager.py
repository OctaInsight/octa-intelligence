"""
Octa Intelligence — Supabase Storage Manager
Replaces Google Drive for policy document file storage.
Requires a public bucket called 'policy-documents' in Supabase Storage.
"""
import streamlit as st
from supabase import create_client, Client


def _client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"]
    )

BUCKET = "policy-documents"


def test_storage_connection() -> tuple:
    """Test Supabase Storage connection. Returns (success, message)."""
    try:
        c = _client()
        buckets = c.storage.list_buckets()
        names = [b.name for b in buckets]
        if BUCKET in names:
            return True, f"Connected — bucket '{BUCKET}' found."
        return False, (
            f"Bucket '{BUCKET}' not found. "
            f"Go to Supabase → Storage → New Bucket → name: policy-documents → Public: ON"
        )
    except Exception as e:
        return False, f"Storage error: {e}"


def _storage_path(tier: str, category: str, file_name: str) -> str:
    """Build a clean storage path: tier/category/filename"""
    safe_cat  = category.strip().replace("/", "-") if category.strip() else "General"
    safe_name = file_name.replace(" ", "_")
    return f"{tier}/{safe_cat}/{safe_name}"


def upload_policy_document(file_bytes: bytes,
                            file_name: str,
                            mime_type: str,
                            tier: str,
                            category: str = "") -> dict | None:
    """
    Upload a policy document to Supabase Storage.
    Returns {file_id, drive_url, folder_path} matching existing DB schema.
    Returns None on failure.
    """
    try:
        c    = _client()
        path = _storage_path(tier, category, file_name)

        # Upload — upsert=True overwrites if same path exists
        c.storage.from_(BUCKET).upload(
            path        = path,
            file        = file_bytes,
            file_options= {"content-type": mime_type, "upsert": "true"}
        )

        # Get public URL
        public_url = c.storage.from_(BUCKET).get_public_url(path)

        return {
            "file_id":     path,           # reuse drive_file_id field as storage path
            "drive_url":   public_url,     # reuse drive_url field as public URL
            "folder_path": f"{tier}/{category}".strip("/"),
        }
    except Exception as e:
        st.error(f"Storage upload failed: {e}")
        return None


def delete_policy_document_file(storage_path: str) -> bool:
    """Delete a file from Supabase Storage."""
    if not storage_path:
        return False
    try:
        _client().storage.from_(BUCKET).remove([storage_path])
        return True
    except Exception:
        return False


def get_public_url(storage_path: str) -> str:
    """Get public URL for an existing stored file."""
    try:
        return _client().storage.from_(BUCKET).get_public_url(storage_path)
    except Exception:
        return ""
