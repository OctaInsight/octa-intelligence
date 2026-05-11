"""Octa Intelligence — Call Setup + Consortium Briefing."""
import streamlit as st
import json
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, step_badge, DARK)
from modules.database import (get_call_setup, save_call_setup,
                               get_consortium_briefing, save_consortium_briefing,
                               get_policy_documents, get_proposal_partners_full,
                               get_proposal)
from modules.document_processor import (extract_from_pdf, extract_from_docx,
                                         extract_from_url, prepare_text_for_storage)
from config import DARK as D, PROGRAMME_NAMES, PROGRAMMES

st.set_page_config(page_title="Call Setup — Octa", page_icon="⚙️",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_proposal_id","")
if not sel_pid:
    st.warning("No proposal selected. Go to the Dashboard first.")
    if st.button("← Dashboard"): st.switch_page("app.py")
    st.stop()

proj    = get_proposal(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Call Setup",
            f"{acronym} — Configure the call, select policy documents and brief the consortium",
            "⚙️")
if st.button("← Dashboard"): st.switch_page("app.py")

muted   = D["muted"]; acc = D["accent"]
user_id = st.session_state.get("user_id")

existing_setup    = get_call_setup(sel_pid)
existing_briefing = get_consortium_briefing(sel_pid)
all_docs          = get_policy_documents()
partners          = get_proposal_partners_full(sel_pid)

tab1, tab2, tab3 = st.tabs([
    "📋 Step 1 — Programme & Documents",
    "📄 Step 2 — Call Text & Reviewer Guide",
    "🧭 Step 3 — Consortium Briefing",
])


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Programme + Policy Documents
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    step_badge("Step 1 of 3")
    st.markdown(
        f"<p style='color:{muted};font-size:0.85rem'>"
        f"Select the funding programme and the policy documents to include in the analysis.</p>",
        unsafe_allow_html=True)

    with st.form("programme_form"):
        programme = st.selectbox(
            "Funding Programme *",
            PROGRAMME_NAMES,
            index=PROGRAMME_NAMES.index(existing_setup.get("programme","Horizon Europe — RIA"))
                  if existing_setup and existing_setup.get("programme") in PROGRAMME_NAMES else 0
        )

        struct_type = st.radio(
            "Proposal structure",
            ["Use pre-built structure for this programme", "I will define my own structure"],
            index=0 if (not existing_setup or existing_setup.get("structure_type","pre_built")=="pre_built") else 1,
            horizontal=True
        )

        # Programme info
        prog_info = PROGRAMMES.get(programme, {})
        if prog_info.get("max_pages"):
            acc2=D["accent"]
            st.markdown(
                f"<div style='background:{D["bg2"]};border-radius:8px;padding:0.6rem 0.9rem;"
                f"font-size:0.82rem;color:{muted}'>"
                f"<strong style='color:{D["text"]}'>{prog_info['label']}</strong><br>"
                f"Funder: {prog_info['funder']} · Max pages: {prog_info['max_pages']}<br>"
                f"Evaluation criteria: "
                + " | ".join(f"{k} ({v.get('weight',0)}%)" for k,v in prog_info.get("evaluation_criteria",{}).items())
                + "</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"**Select Policy Documents to Include in Analysis**")
        st.caption("Choose which documents the AI should read when analysing this call.")

        # Show docs as checkboxes grouped by tier
        existing_ids = existing_setup.get("selected_policy_doc_ids",[]) if existing_setup else []
        if isinstance(existing_ids, str):
            try:    existing_ids = json.loads(existing_ids)
            except: existing_ids = []

        selected_ids = []
        for tier_key, tier_label in [
            ("core","⭐ Core Policies"),
            ("programme","📋 Programme-level"),
            ("call_specific","📄 Call-specific"),
        ]:
            tier_docs = [d for d in all_docs if d.get("tier")==tier_key]
            if tier_docs:
                st.markdown(f"**{tier_label}**")
                for doc in tier_docs:
                    did     = doc["id"]
                    checked = st.checkbox(
                        f"{doc.get('title','')} ({doc.get('page_count',0)} pages)",
                        value=(did in existing_ids),
                        key=f"sel_{did}"
                    )
                    if checked:
                        selected_ids.append(did)

        if not all_docs:
            warn=D["warning"]
            st.markdown(
                f"<div style='background:{warn}22;border:1px solid {warn};border-radius:8px;"
                f"padding:0.6rem 0.9rem;font-size:0.83rem'>"
                f"⚠ No policy documents in library yet. "
                f"<a href='#' style='color:{D["accent"]}'>Add documents first</a></div>",
                unsafe_allow_html=True)

        if st.form_submit_button("💾 Save Programme & Document Selection",
                                  type="primary", use_container_width=True):
            ok, _ = save_call_setup({
                "proposal_id":           sel_pid,
                "programme":             programme,
                "structure_type":        "pre_built" if "pre-built" in struct_type else "custom",
                "selected_policy_doc_ids": selected_ids,
                "created_by":            user_id,
            })
            if ok:
                st.success(f"✅ Saved! {len(selected_ids)} documents selected.")
                st.rerun()
            else:
                st.error("Save failed.")

    if st.button("→ Go to Policy Library to add more documents"):
        st.session_state["library_selection_mode"] = True
        st.switch_page("pages/policy_library.py")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Call Text + Reviewer Guide
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    step_badge("Step 2 of 3")
    st.markdown(
        f"<p style='color:{muted};font-size:0.85rem'>"
        f"Upload or paste the call text and (optionally) the reviewer evaluation guidelines.</p>",
        unsafe_allow_html=True)

    with st.form("call_text_form"):
        st.markdown("#### Call Text *")
        call_source = st.radio("Source", ["Paste text","PDF","Word","URL"],
                                horizontal=True, key="call_src")

        call_text = ""; call_url = ""; call_fname = ""

        if call_source == "Paste text":
            call_text = st.text_area("Paste call text here", height=300,
                                      value=existing_setup.get("call_text","") if existing_setup else "")
        elif call_source == "PDF":
            call_file = st.file_uploader("Upload call PDF", type=["pdf"], key="call_pdf")
        elif call_source == "Word":
            call_file = st.file_uploader("Upload call DOCX", type=["docx"], key="call_docx")
        else:
            call_url  = st.text_input("Call URL",
                                       value=existing_setup.get("call_url","") if existing_setup else "")

        st.markdown("---")
        st.markdown("#### Reviewer / Evaluation Guidelines *(optional)*")
        has_guide = st.checkbox("This call has a separate reviewer guidelines document",
                                 value=existing_setup.get("has_reviewer_guide",False) if existing_setup else False)

        guide_text = ""; guide_url = ""; guide_fname = ""
        if has_guide:
            guide_source = st.radio("Source", ["Paste text","PDF","Word","URL"],
                                     horizontal=True, key="guide_src")
            if guide_source == "Paste text":
                guide_text = st.text_area("Paste reviewer guidelines", height=200,
                                           value=existing_setup.get("guide_text","") if existing_setup else "")
            elif guide_source == "PDF":
                guide_file = st.file_uploader("Upload guide PDF", type=["pdf"], key="guide_pdf")
            elif guide_source == "Word":
                guide_file = st.file_uploader("Upload guide DOCX", type=["docx"], key="guide_docx")
            else:
                guide_url = st.text_input("Guide URL",
                                           value=existing_setup.get("guide_url","") if existing_setup else "")

        if st.form_submit_button("💾 Save Call Documents", type="primary",
                                  use_container_width=True):
            # Extract text from files if uploaded
            with st.spinner("Extracting text…"):
                if call_source == "PDF" and "call_file" in dir() and call_file:
                    call_text, _ = extract_from_pdf(call_file.read())
                    call_fname   = call_file.name
                elif call_source == "Word" and "call_file" in dir() and call_file:
                    call_text, _ = extract_from_docx(call_file.read())
                    call_fname   = call_file.name
                elif call_source == "URL" and call_url:
                    call_text, _ = extract_from_url(call_url)

                if has_guide:
                    if "guide_source" in dir():
                        if guide_source == "PDF" and "guide_file" in dir() and guide_file:
                            guide_text, _ = extract_from_pdf(guide_file.read())
                        elif guide_source == "Word" and "guide_file" in dir() and guide_file:
                            guide_text, _ = extract_from_docx(guide_file.read())
                        elif guide_source == "URL" and guide_url:
                            guide_text, _ = extract_from_url(guide_url)

            if not call_text.strip():
                st.error("❌ Call text is empty."); st.stop()

            ok, _ = save_call_setup({
                "proposal_id":     sel_pid,
                "call_source_type": call_source.lower().replace(" ","_"),
                "call_text":        call_text[:500000],
                "call_url":         call_url,
                "call_file_name":   call_fname,
                "has_reviewer_guide": has_guide,
                "guide_source_type":  guide_source.lower().replace(" ","_") if has_guide and "guide_source" in dir() else "text",
                "guide_text":        guide_text[:300000] if has_guide else "",
                "guide_url":         guide_url if has_guide else "",
                "created_by":        user_id,
            })
            if ok:
                words = len(call_text.split())
                st.success(f"✅ Call text saved ({words:,} words)!")
                st.rerun()
            else:
                st.error("Save failed.")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Consortium Briefing
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    step_badge("Step 3 of 3")
    st.markdown(
        f"<p style='color:{muted};font-size:0.85rem'>"
        f"Brief the AI about your consortium. This transforms generic call analysis into "
        f"targeted competitive intelligence specific to YOUR team.</p>",
        unsafe_allow_html=True)

    # Step A: auto-pulled partners
    if partners:
        section_label("Part A — Your Consortium Partners (auto-pulled)")
        p_profiles = existing_briefing.get("partner_profiles",[]) if existing_briefing else []
        if isinstance(p_profiles, str):
            try:    p_profiles = json.loads(p_profiles)
            except: p_profiles = []
        p_map = {p.get("partner_id"): p for p in p_profiles}

        new_profiles = []
        for partner in partners:
            pid   = partner["id"]
            pname = partner.get("full_name","") or partner.get("short_name","")
            ptype = partner.get("partner_type","")
            pcountry = partner.get("country","")
            is_coord = partner.get("is_coordinator",False)
            existing_p = p_map.get(pid,{})

            with st.expander(
                f"{'⭐ COORDINATOR — ' if is_coord else ''}{pname} ({pcountry})",
                expanded=is_coord
            ):
                pc1,pc2 = st.columns(2)
                with pc1:
                    role = st.text_input("Role in this proposal",
                        value=existing_p.get("role_in_proposal","Coordinator" if is_coord else "Partner"),
                        key=f"role_{pid}")
                    expertise = st.text_area("Core expertise for this call",
                        value=existing_p.get("expertise",""),
                        height=70, key=f"exp_{pid}",
                        placeholder="What specific expertise does this partner bring?")
                with pc2:
                    strengths = st.text_area("Key strengths to highlight",
                        value=existing_p.get("key_strengths",""),
                        height=70, key=f"str_{pid}",
                        placeholder="Awards, unique infrastructure, track record…")
                    rel_proj = st.text_area("Relevant previous projects",
                        value=existing_p.get("relevant_projects",""),
                        height=70, key=f"rp_{pid}",
                        placeholder="Previous EU projects, publications, tools…")

                notes = st.text_input("Additional notes",
                    value=existing_p.get("notes",""), key=f"note_{pid}")

                new_profiles.append({
                    "partner_id":       pid,
                    "name":             pname,
                    "type":             ptype,
                    "country":          pcountry,
                    "is_coordinator":   is_coord,
                    "role_in_proposal": role,
                    "expertise":        expertise,
                    "key_strengths":    strengths,
                    "relevant_projects":rel_proj,
                    "notes":            notes,
                })

    # Step B: consortium strategy
    section_label("Part B — Consortium Strategy")
    with st.form("briefing_form"):
        bc1,bc2 = st.columns(2)
        with bc1:
            strategy = st.text_area("Consortium Strategy",
                value=existing_briefing.get("consortium_strategy","") if existing_briefing else "",
                height=100,
                placeholder="What is the strategic rationale for this specific combination of partners?")
            usp = st.text_area("Unique Selling Point",
                value=existing_briefing.get("unique_selling_point","") if existing_briefing else "",
                height=80,
                placeholder="What makes this consortium uniquely qualified to win?")
            advantage = st.text_area("Competitive Advantage",
                value=existing_briefing.get("competitive_advantage","") if existing_briefing else "",
                height=80,
                placeholder="What do we have that other consortia probably don't?")
        with bc2:
            geography = st.text_area("Geographic Coverage Rationale",
                value=existing_briefing.get("geographic_rationale","") if existing_briefing else "",
                height=80,
                placeholder="Why this geographic mix? What regions are covered and why relevant?")
            weaknesses = st.text_area("Weaknesses to Manage",
                value=existing_briefing.get("weaknesses_to_manage","") if existing_briefing else "",
                height=80,
                placeholder="What gaps exist in the consortium that reviewers might flag?")
            innovation_type = st.selectbox("Innovation Type",
                ["incremental","radical","disruptive","systemic","not applicable"],
                index=["incremental","radical","disruptive","systemic","not applicable"].index(
                    existing_briefing.get("innovation_type","incremental") if existing_briefing else "incremental"
                ))
            trl = st.text_input("Target TRL (if applicable)",
                value=existing_briefing.get("target_trl","") if existing_briefing else "",
                placeholder="e.g. TRL 4-6 at start, TRL 7-8 at end")

        extra_notes = st.text_area("Additional Strategic Notes",
            value=existing_briefing.get("additional_notes","") if existing_briefing else "",
            height=80,
            placeholder="Anything else the AI should know when positioning this proposal…")

        save_btn = st.form_submit_button("💾 Save Consortium Briefing", type="primary",
                                     use_container_width=True)

    if save_btn:
            ok, _ = save_consortium_briefing({
                "proposal_id":         sel_pid,
                "consortium_strategy": strategy,
                "unique_selling_point":usp,
                "competitive_advantage":advantage,
                "geographic_rationale":geography,
                "weaknesses_to_manage":weaknesses,
                "innovation_type":     innovation_type,
                "target_trl":          trl,
                "additional_notes":    extra_notes,
                "partner_profiles":    new_profiles if partners else [],
                "created_by":          user_id,
            })
            if ok:
                st.success("✅ Consortium briefing saved!")
                st.session_state["briefing_saved"] = True
                st.rerun()
            else:
                st.error("Save failed.")

    # Proceed button outside the form
    if st.session_state.get("briefing_saved"):
        if st.button("→ Proceed to Round 1 Analysis", type="primary",
                     use_container_width=True, key="proceed_r1"):
            st.session_state["briefing_saved"] = False
            st.switch_page("pages/round1_analysis.py")
