"""Octa Intelligence — Policy Library."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, DARK)
from modules.database import (get_policy_documents, create_policy_document,
                               delete_policy_document)
from modules.document_processor import (extract_from_pdf, extract_from_docx,
                                         extract_from_url, prepare_text_for_storage,
                                         count_words, estimate_tokens)
from modules.claude_client import generate_document_summary
from modules.storage_manager import (upload_policy_document,
                                      test_storage_connection,
                                      delete_policy_document_file)
from modules.database import get_policy_document
from config import (DARK as D, POLICY_CATEGORIES, POLICY_TIERS, PROGRAMMES)

st.set_page_config(page_title="Policy Library — Octa", page_icon="📚",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()
page_header("Policy Library",
            "Your growing knowledge base of EU policy documents — shared across all proposals",
            "📚")

muted = D["muted"]; acc = D["accent"]
user_id = st.session_state.get("user_id")

all_docs = get_policy_documents()

# ── Library stats ──────────────────────────────────────────────────────────────
section_label("📊 Library Overview")
c1,c2,c3,c4 = st.columns(4)
for col, label, val, color in [
    (c1,"Total Documents", len(all_docs),                                          acc),
    (c2,"Core",  sum(1 for d in all_docs if d.get("tier")=="core"),                D["success"]),
    (c3,"Programme", sum(1 for d in all_docs if d.get("tier")=="programme"),       D["accent2"]),
    (c4,"Call-Specific", sum(1 for d in all_docs if d.get("tier")=="call_specific"),D["warning"]),
]:
    bg2=D["bg2"]
    col.markdown(
        f"<div style='background:{bg2};border-top:3px solid {color};"
        f"border:1px solid {color}44;border-radius:10px;"
        f"padding:0.7rem;text-align:center'>"
        f"<div style='font-size:1.5rem;font-weight:700;color:{color}'>{val}</div>"
        f"<div style='font-size:0.75rem;color:{muted}'>{label}</div></div>",
        unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# UPLOAD NEW DOCUMENT
# ═══════════════════════════════════════════════════════════════════════════════
section_label("➕ Add Document to Library")
with st.expander("Upload New Policy Document", expanded=not all_docs):

    uc1, uc2 = st.columns(2)
    with uc1:
        doc_title   = st.text_input("Document Title *",
                                     placeholder="e.g. European Green Deal Communication")
        tier_labels = list(POLICY_TIERS.values())
        tier_sel    = st.selectbox("Tier *", tier_labels)
        tier_key    = list(POLICY_TIERS.keys())[tier_labels.index(tier_sel)]

        category = st.selectbox("Category *", POLICY_CATEGORIES)

    with uc2:
        prog_opts = ["All"] + [p for p in PROGRAMMES.keys() if p != "Custom"]
        programme = st.selectbox("Relevant Programme", prog_opts)

        source_type = st.radio("Document Source", ["PDF upload","Word upload","URL"],
                                horizontal=True)

    # Source-specific input
    if source_type == "PDF upload":
        uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="lib_pdf")
        url_input = ""
    elif source_type == "Word upload":
        uploaded = st.file_uploader("Upload Word (.docx)", type=["docx"], key="lib_docx")
        url_input = ""
    else:
        uploaded  = None
        url_input = st.text_input("Document URL",
                                   placeholder="https://ec.europa.eu/...")

    use_ai_summary = st.checkbox(
        "🤖 Auto-generate summary & keywords with Claude API",
        value=True,
        help="Uses Claude to generate a structured summary. Costs ~$0.01 per document."
    )

    if st.button("📚 Add to Library", type="primary", use_container_width=True):
        if not doc_title.strip():
            st.error("❌ Document title required."); st.stop()

        progress = st.container()

        # Step 1: Extract text
        with progress:
            st.info("📄 Step 1/4 — Extracting text from document…")
        text = ""; page_count = 0; file_bytes = None; file_name = ""
        mime_type = "application/pdf"

        if source_type == "PDF upload" and uploaded:
            file_bytes = uploaded.read()
            file_name  = uploaded.name
            mime_type  = "application/pdf"
            text, page_count = extract_from_pdf(file_bytes)
        elif source_type == "Word upload" and uploaded:
            file_bytes = uploaded.read()
            file_name  = uploaded.name
            mime_type  = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            text, page_count = extract_from_docx(file_bytes)
        elif source_type == "URL" and url_input.strip():
            text, page_count = extract_from_url(url_input.strip())
        else:
            st.error("❌ Please provide a file or URL."); st.stop()

        if not text or text.startswith("["):
            st.error(f"❌ Text extraction failed: {text}"); st.stop()

        with progress:
            st.success(f"✅ Text extracted — {count_words(text):,} words, ~{page_count} pages")

        stored_text, truncated = prepare_text_for_storage(text)

        # Step 2: AI summary
        summary_data = {}
        if use_ai_summary and text:
            with progress:
                st.info("🤖 Step 2/4 — Generating AI summary and keywords…")
            summary_data = generate_document_summary(text[:60000], doc_title) or {}
            if summary_data.get("category_suggestion"):
                if not category or category == "Other":
                    category = summary_data["category_suggestion"]
            with progress:
                st.success(f"✅ AI summary ready — {len(summary_data.get('keywords',[]))} keywords extracted")
        else:
            with progress:
                st.info("⏭ Step 2/4 — Skipping AI summary")

        # Step 3: Upload to Google Drive
        drive_info = {}
        if file_bytes and file_name:
            with progress:
                st.info(f"☁ Step 3/4 — Uploading '{file_name}' to Supabase Storage…")
                st.info("Uploading to Google Drive…")
                drive_info = upload_policy_document(
                    file_bytes, file_name, mime_type, tier_key, category
                ) or {}

            if drive_info:
                with progress:
                    st.success(f"✅ Uploaded to Supabase Storage: {drive_info.get('folder_path','')}")
            else:
                with progress:
                    st.warning("⚠ Storage upload failed — metadata saved to database only")
        else:
            with progress:
                st.info("⏭ Step 3/4 — No file to upload to Drive (URL source)")

        # Step 4: Save to Supabase
        with progress:
            st.info("💾 Step 4/4 — Saving to library database…")
        ok, doc_id = create_policy_document({
                "title":             doc_title.strip(),
                "tier":              tier_key,
                "category":          category,
                "programme":         programme,
                "source_type":       source_type.lower().replace(" ","_"),
                "original_url":      url_input.strip(),
                "file_name":         file_name,
                "page_count":        page_count,
                "text_content":      stored_text,
                "text_summary":      summary_data.get("detailed_summary",""),
                "text_truncated":    truncated,
                "keywords":          summary_data.get("keywords",[]),
                "short_description": summary_data.get("short_description",""),
                "drive_file_id":     drive_info.get("file_id",""),
                "drive_url":         drive_info.get("drive_url",""),
                "drive_folder_path": drive_info.get("folder_path",""),
                "language":          "en",
                "uploaded_by":       user_id,
            })



# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE TREE VIEW
# ═══════════════════════════════════════════════════════════════════════════════
section_label("🌳 Knowledge Tree")

if not all_docs:
    st.info("No documents yet. Add your first policy document above.")
    st.stop()

# Optional selection mode (for call setup)
selection_mode = st.session_state.get("library_selection_mode", False)
if selection_mode:
    acc2=D["accent"]
    st.markdown(
        f"<div style='background:{acc2}22;border:1px solid {acc2};border-radius:8px;"
        f"padding:0.6rem 1rem;margin-bottom:0.8rem'>"
        f"<strong style='color:{acc2}'>✅ Selection Mode Active</strong> — "
        f"tick the documents to include in your analysis, then return to Call Setup.</div>",
        unsafe_allow_html=True)

selected_ids = st.session_state.get("selected_doc_ids", [])

# Group by tier → category
from collections import defaultdict
tree: dict = defaultdict(lambda: defaultdict(list))
for doc in all_docs:
    tree[doc.get("tier","core")][doc.get("category","Other")].append(doc)

TIER_ORDER = ["core","programme","call_specific"]
TIER_ICONS = {"core":"⭐","programme":"📋","call_specific":"📄"}

for tier in TIER_ORDER:
    if tier not in tree:
        continue
    tier_label = POLICY_TIERS.get(tier, tier)
    tier_icon  = TIER_ICONS.get(tier,"📄")
    acc2 = D["accent"]
    st.markdown(
        f"<div style='font-size:1rem;font-weight:700;color:{acc2};"
        f"margin:1rem 0 0.3rem'>{tier_icon} {tier_label}</div>",
        unsafe_allow_html=True)

    for cat, docs in sorted(tree[tier].items()):
        bg2=D["bg2"]; border=D["border"]; txt=D["text"]
        with st.expander(f"📂 {cat} ({len(docs)})", expanded=(tier=="core")):
            for doc in docs:
                did   = doc["id"]
                title = doc.get("title","")
                pages = doc.get("page_count",0)
                drive = doc.get("drive_url","")
                kws   = doc.get("keywords",[])[:5]
                desc  = doc.get("short_description","")
                used  = doc.get("used_in_analyses_count",0)

                col_check, col_info, col_actions = st.columns([0.5, 5, 1.5])

                with col_check:
                    if selection_mode:
                        checked = st.checkbox("",
                            value=(did in selected_ids),
                            key=f"sel_doc_{did}"
                        )
                        if checked and did not in selected_ids:
                            selected_ids.append(did)
                            st.session_state["selected_doc_ids"] = selected_ids
                        elif not checked and did in selected_ids:
                            selected_ids.remove(did)
                            st.session_state["selected_doc_ids"] = selected_ids

                with col_info:
                    st.markdown(
                        f"<div style='padding:0.3rem 0'>"
                        f"<strong style='color:{txt}'>{title}</strong>"
                        f"<span style='color:{muted};font-size:0.75rem;margin-left:0.5rem'>"
                        f"{pages} pages · Used {used}×</span>"
                        + (f"<br><span style='color:{muted};font-size:0.78rem'>{desc}</span>" if desc else "")
                        + (f"<br><span style='color:{D["accent2"]};font-size:0.72rem'>"
                           f"🏷 {' · '.join(str(k) for k in kws)}</span>" if kws else "")
                        + "</div>", unsafe_allow_html=True)

                with col_actions:
                    if drive:
                        st.markdown(
                            f"<a href='{drive}' target='_blank' style='color:{acc};"
                            f"font-size:0.78rem;text-decoration:none'>🔗 Drive</a>",
                            unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_doc_{did}",
                                  help="Remove from library"):
                        _d = get_policy_document(did)
                        if _d and _d.get("drive_file_id"):
                            delete_policy_document_file(_d["drive_file_id"])
                        delete_policy_document(did)
                        st.rerun()

if selection_mode and selected_ids:
    suc=D["success"]
    st.markdown(
        f"<div style='background:{suc}22;border:1px solid {suc};border-radius:8px;"
        f"padding:0.6rem 1rem;margin-top:0.8rem'>"
        f"<strong style='color:{suc}'>✅ {len(selected_ids)} document(s) selected</strong><br>"
        f"<span style='color:{muted};font-size:0.82rem'>Return to Call Setup to continue.</span>"
        f"</div>", unsafe_allow_html=True)
    if st.button("← Back to Call Setup", type="primary"):
        st.session_state["library_selection_mode"] = False
        st.switch_page("pages/call_setup.py")
