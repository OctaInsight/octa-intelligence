"""Octa Intelligence — Database layer."""
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone, date
import json


@st.cache_resource
def _client() -> Client:
    return create_client(st.secrets["supabase"]["url"],
                         st.secrets["supabase"]["key"])

def db() -> Client:
    return _client()

def _now():
    return datetime.now(timezone.utc).isoformat()


# ── Proposals (read existing) ─────────────────────────────────────────────────

def get_all_proposals() -> list:
    try:
        return db().table("proposals").select(
            "proposal_id,acronym,proposal_title,coordinator,partners_list,status,lifecycle_status"
        ).order("proposal_id", desc=True).execute().data or []
    except Exception:
        return []


def get_proposal(proposal_id: str) -> dict | None:
    try:
        r = db().table("proposals").select("*") \
                .eq("proposal_id", proposal_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


# ── Partners ──────────────────────────────────────────────────────────────────

def get_proposal_partners_full(proposal_id: str) -> list:
    """Get full partner records for all partners in a proposal."""
    try:
        prop = get_proposal(proposal_id)
        if not prop:
            return []
        names = []
        coord = (prop.get("coordinator") or "").strip()
        if coord:
            names.append(coord)
        plist = prop.get("partners_list") or []
        if isinstance(plist, str):
            try:    plist = json.loads(plist)
            except: plist = [plist]
        names.extend([str(n).strip() for n in plist if n])
        if not names:
            return []
        all_p = db().table("partners").select(
            "id,full_name,short_name,country,partner_type,website"
        ).order("full_name").execute().data or []
        result = []; seen = set()
        for name in names:
            nl = name.lower()
            for p in all_p:
                if p["id"] in seen: continue
                fn = (p.get("full_name") or "").lower()
                sn = (p.get("short_name") or "").lower()
                if nl in fn or fn in nl or (sn and (nl in sn or sn in nl)):
                    result.append({**p, "is_coordinator": name == coord})
                    seen.add(p["id"]); break
        return result
    except Exception:
        return []


# ── Policy Documents ──────────────────────────────────────────────────────────

def get_policy_documents(tier: str = None, category: str = None,
                          programme: str = None) -> list:
    try:
        q = db().table("policy_documents").select("*").eq("is_active", True)
        if tier:      q = q.eq("tier", tier)
        if category:  q = q.eq("category", category)
        if programme and programme != "All":
            q = q.or_(f"programme.eq.{programme},programme.eq.All")
        return q.order("tier").order("category").order("title").execute().data or []
    except Exception:
        return []


def get_policy_document(doc_id: int) -> dict | None:
    try:
        r = db().table("policy_documents").select("*").eq("id", doc_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def create_policy_document(data: dict) -> tuple:
    try:
        data["created_at"] = _now()
        data["updated_at"] = _now()
        r = db().table("policy_documents").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


def delete_policy_document(doc_id: int) -> bool:
    try:
        db().table("policy_documents").update(
            {"is_active": False, "updated_at": _now()}
        ).eq("id", doc_id).execute()
        return True
    except Exception:
        return False


def increment_doc_usage(doc_ids: list) -> bool:
    try:
        for did in doc_ids:
            doc = get_policy_document(did)
            if doc:
                db().table("policy_documents").update({
                    "used_in_analyses_count": (doc.get("used_in_analyses_count",0) or 0) + 1,
                    "updated_at": _now()
                }).eq("id", did).execute()
        return True
    except Exception:
        return False


# ── Call Setup ────────────────────────────────────────────────────────────────

def get_call_setup(proposal_id: str) -> dict | None:
    try:
        r = db().table("call_setups").select("*") \
                .eq("proposal_id", proposal_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def save_call_setup(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        existing = get_call_setup(data["proposal_id"])
        if existing:
            db().table("call_setups").update(data) \
                .eq("proposal_id", data["proposal_id"]).execute()
            return True, existing["id"]
        data["created_at"] = _now()
        r = db().table("call_setups").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


# ── Consortium Briefing ───────────────────────────────────────────────────────

def get_consortium_briefing(proposal_id: str) -> dict | None:
    try:
        r = db().table("consortium_briefings").select("*") \
                .eq("proposal_id", proposal_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def save_consortium_briefing(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        existing = get_consortium_briefing(data["proposal_id"])
        if existing:
            db().table("consortium_briefings").update(data) \
                .eq("proposal_id", data["proposal_id"]).execute()
            return True, existing["id"]
        data["created_at"] = _now()
        r = db().table("consortium_briefings").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


# ── Call Analyses ─────────────────────────────────────────────────────────────

def get_call_analyses(proposal_id: str) -> list:
    try:
        return db().table("call_analyses").select("*") \
                   .eq("proposal_id", proposal_id) \
                   .order("created_at", desc=True).execute().data or []
    except Exception:
        return []


def get_call_analysis(analysis_id: int) -> dict | None:
    try:
        r = db().table("call_analyses").select("*").eq("id", analysis_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def create_call_analysis(data: dict) -> tuple:
    try:
        data["created_at"] = _now()
        r = db().table("call_analyses").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


def update_call_analysis(analysis_id: int, data: dict) -> bool:
    try:
        db().table("call_analyses").update(data) \
            .eq("id", analysis_id).execute()
        return True
    except Exception:
        return False


# ── Concept Evaluations ───────────────────────────────────────────────────────

def get_concept_evaluations(proposal_id: str) -> list:
    try:
        return db().table("concept_evaluations").select("*") \
                   .eq("proposal_id", proposal_id) \
                   .order("created_at", desc=True).execute().data or []
    except Exception:
        return []


def create_concept_evaluation(data: dict) -> tuple:
    try:
        data["created_at"] = _now()
        r = db().table("concept_evaluations").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


# ── Proposal Architectures ────────────────────────────────────────────────────

def get_proposal_architectures(proposal_id: str) -> list:
    try:
        return db().table("proposal_architectures").select("*") \
                   .eq("proposal_id", proposal_id) \
                   .order("created_at", desc=True).execute().data or []
    except Exception:
        return []


def get_proposal_architecture(arch_id: int) -> dict | None:
    try:
        r = db().table("proposal_architectures").select("*") \
                .eq("id", arch_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def create_proposal_architecture(data: dict) -> tuple:
    try:
        data["created_at"] = _now()
        r = db().table("proposal_architectures").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


def update_proposal_architecture(arch_id: int, data: dict) -> bool:
    try:
        db().table("proposal_architectures").update(data) \
            .eq("id", arch_id).execute()
        return True
    except Exception:
        return False


# ── Architecture Reviews ──────────────────────────────────────────────────────

def create_architecture_review(data: dict) -> tuple:
    try:
        data["created_at"] = _now()
        r = db().table("architecture_reviews").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


def get_architecture_review(arch_id: int) -> dict | None:
    try:
        r = db().table("architecture_reviews").select("*") \
                .eq("architecture_id", arch_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


# ── Users ─────────────────────────────────────────────────────────────────────

def get_all_users() -> list:
    try:
        return db().table("octa_users").select(
            "id,username,first_name,last_name,organisation"
        ).eq("status","approved").order("first_name").execute().data or []
    except Exception:
        return []
