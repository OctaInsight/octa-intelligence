"""Octa Intelligence - Round 2b: Proposal Architecture Generator."""
import streamlit as st
import re
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, DARK)
from modules.database import (get_call_analyses, get_call_setup,
                               get_concept_evaluations,
                               get_proposal_architectures,
                               create_proposal_architecture,
                               update_proposal_architecture, get_proposal)
from modules.claude_client import (build_section_intelligence,
                                   annotate_section_batch,
                                   generate_overall_advice,
                                   _parse_json_response)
from modules.word_export import export_architecture_docx
from config import DARK as D, PROGRAMMES

st.set_page_config(page_title="Architecture - Octa", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_proposal_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_proposal(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Round 2b — Proposal Architecture",
            f"{acronym} — Section-by-section AI guidance saved live to database",
            "🏗️")
if st.button("← Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]

analyses = get_call_analyses(sel_pid)
complete = [a for a in analyses if a.get("status")=="complete"]
setup    = get_call_setup(sel_pid)
concepts = get_concept_evaluations(sel_pid)
archs    = get_proposal_architectures(sel_pid)

if not complete:
    st.warning("Complete Round 1 analysis first.")
    if st.button("Go to Round 1"): st.switch_page("pages/round1_analysis.py")
    st.stop()

analysis       = complete[0]
latest_concept = concepts[0] if concepts else None
programme      = setup.get("programme","Horizon Europe - RIA") if setup else "Horizon Europe - RIA"
prog_info      = PROGRAMMES.get(programme,{})

# ── Structure definition ───────────────────────────────────────────────────────
section_label("Step 1 — Define Your Proposal Structure")

with st.expander("Structure", expanded=not archs):
    template_sections = prog_info.get("structure",[])
    user_titles = {}

    if template_sections:
        st.markdown(f"<p style='color:{muted};font-size:0.84rem'>Edit titles if needed. AI will annotate each one.</p>",
                    unsafe_allow_html=True)
        for sec in template_sections:
            sid   = sec.get("id","")
            level = sec.get("level",1)
            dflt  = sec.get("title","")
            indent= "   " * (level-1)
            val   = st.text_input(f"{indent}Section {sid}", value=dflt, key=f"ts_{sid}")
            if val != dflt: user_titles[sid] = val
    else:
        st.markdown(
            f"<div style='background:{D["bg2"]};border-left:3px solid {acc};"
            f"border-radius:8px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;"
            f"font-size:0.78rem;color:{muted}'>"
            f"Enter sections one per line. 2 spaces indent = subsection.</div>",
            unsafe_allow_html=True)

        custom_text = st.text_area("Your Structure", height=220, key="cst",
            placeholder=(
                "1. Excellence\n  1.1 Objectives\n  1.2 Methodology\n"
                "2. Impact\n  2.1 Outcomes\n  2.2 Dissemination\n"
                "3. Implementation\n  3.1 Work Plan\n  3.2 Consortium"
            ))

        if custom_text.strip():
            parsed_secs = []
            order = 0
            for line in custom_text.strip().splitlines():
                stripped = line.strip()
                if not stripped: continue
                leading = len(line) - len(line.lstrip(" -"))
                level   = 1 if leading==0 else (2 if leading<=3 else 3)
                m       = re.match(r"^[0-9.]+[.)]\s*", stripped)
                if m:
                    sec_id = m.group().strip().rstrip(".")
                    title  = stripped[m.end():].strip()
                else:
                    sec_id = str(len(parsed_secs)+1)
                    title  = stripped.lstrip("- ").strip()
                order += 1
                parsed_secs.append({"id":sec_id,"level":level,"title":title,"order":order})
            template_sections = parsed_secs
            suc = D["success"]
            st.markdown(f"<span style='color:{suc}'>✅ {len(parsed_secs)} sections ready</span>",
                        unsafe_allow_html=True)

# ── Generate button ────────────────────────────────────────────────────────────
section_label("Step 2 — Generate Architecture (one section at a time)")

st.markdown(
    f"<p style='color:{muted};font-size:0.84rem'>"
    f"Each section is sent to Claude individually and saved to the database immediately. "
    f"Results appear live as they complete. "
    f"Estimated time: ~{max(1,len(template_sections or [])) * 15} seconds.</p>",
    unsafe_allow_html=True)

if st.button("🏗️ Generate Architecture", type="primary", use_container_width=True):
    if not template_sections:
        st.error("No sections defined above."); st.stop()

    # Apply user title overrides
    sections_to_process = []
    for i, sec in enumerate(template_sections):
        sid   = sec.get("id","")
        title = user_titles.get(sid, sec.get("title",""))
        sections_to_process.append({**sec, "title": title, "order": i+1})

    n = len(sections_to_process)

    # Create the architecture record first
    from datetime import datetime, timezone
    ok, arch_id = create_proposal_architecture({
        "proposal_id":           sel_pid,
        "call_analysis_id":      analysis["id"],
        "concept_evaluation_id": latest_concept["id"] if latest_concept else None,
        "api_mode":              "realtime",
        "status":                "processing",
        "programme":             programme,
        "structure_type":        "pre_built" if prog_info.get("structure") else "custom",
        "sections":              [],
        "total_sections":        sum(1 for s in sections_to_process if s.get("level",1)==1),
        "total_subsections":     sum(1 for s in sections_to_process if s.get("level",1)>1),
        "raw_response":          "",
        "completed_at":          None,
    })

    if not ok:
        st.error(f"Database error: {arch_id}"); st.stop()

    # Build intelligence once
    intel = build_section_intelligence(analysis, latest_concept)

    # Process in batches of 4, save after each batch
    BATCH_SIZE   = 4
    batches      = [sections_to_process[i:i+BATCH_SIZE]
                    for i in range(0, n, BATCH_SIZE)]
    n_batches    = len(batches)
    progress_bar = st.progress(0, text=f"Starting... 0/{n_batches} batches")
    status_text  = st.empty()
    completed    = []
    failed_count = 0

    for b_idx, batch in enumerate(batches):
        titles = ", ".join(s.get("title","")[:25] for s in batch)
        status_text.markdown(
            f"<span style='color:{acc}'>⚙ Batch {b_idx+1}/{n_batches}: {titles}…</span>",
            unsafe_allow_html=True)
        progress_bar.progress(b_idx/n_batches,
                              text=f"Batch {b_idx+1}/{n_batches} ({len(batch)} sections)")

        annotated_batch = annotate_section_batch(batch, intel, programme)
        completed.extend(annotated_batch)
        failed_count += sum(1 for s in annotated_batch if s.get("_parse_failed"))

        # Save after EVERY batch
        update_proposal_architecture(arch_id, {"sections": completed})
        progress_bar.progress((b_idx+1)/n_batches,
                              text=f"Saved batch {b_idx+1}/{n_batches}")

    # Generate overall advice
    status_text.markdown(f"<span style='color:{acc}'>💡 Generating strategic advice…</span>",
                         unsafe_allow_html=True)
    titles_list = [s.get("ai_title","") or s.get("title","") for s in completed]
    advice      = generate_overall_advice(intel, programme, titles_list)

    # Final update
    update_proposal_architecture(arch_id, {
        "status":           "complete",
        "sections":         completed,
        "general_advice":   advice.get("general_advice",""),
        "top_5_priorities": advice.get("top_5_priorities",[]),
        "completed_at":     datetime.now(timezone.utc).isoformat(),
    })

    progress_bar.progress(1.0, text=f"✅ Complete — {n} sections saved to database")
    status_text.empty()

    if failed_count:
        st.warning(f"⚠ {failed_count} section(s) used fallback text — use Regenerate below.")
    else:
        st.success(f"✅ All {n} sections annotated and saved!")
    st.rerun()

# ── Display results ────────────────────────────────────────────────────────────
if not archs: st.stop()

arch = archs[0]
if len(archs) > 1:
    idx  = st.selectbox("Version", range(len(archs)),
                        format_func=lambda i: (f"v{len(archs)-i}: "
                                               f"{str(archs[i].get('created_at',''))[:10]} "
                                               f"({archs[i].get('total_sections',0)}s "
                                               f"{archs[i].get('total_subsections',0)}ss) "
                                               f"— {archs[i].get('status','')}"),
                        key="arch_v")
    arch = archs[idx]

sections = arch.get("sections",[])

# Processing badge
if arch.get("status") == "processing":
    warn = D["warning"]
    st.markdown(
        f"<div style='background:{warn}22;border:1px solid {warn};border-radius:8px;"
        f"padding:0.7rem 1rem;margin-bottom:0.8rem'>"
        f"<strong style='color:{warn}'>⏳ Generation in progress…</strong> "
        f"Refresh to see latest sections ({len(sections)} saved so far)."
        f"</div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh"): st.rerun()

if not sections:
    st.info("No sections yet. Click Generate Architecture above."); st.stop()

section_label(f"📋 Architecture — {len(sections)} sections")

# Downloads
dc1, dc2 = st.columns(2)
with dc1:
    doc_bytes = export_architecture_docx(arch, analysis, sel_pid, acronym)
    st.download_button(
        "📥 Download Architecture (Word)",
        data=doc_bytes,
        file_name=f"{acronym}_Proposal_Architecture.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="dl_arch"
    )
with dc2:
    st.markdown(
        f"<div style='background:{D["bg2"]};border-radius:8px;padding:0.6rem 0.9rem;"
        f"font-size:0.8rem;color:{muted}'>"
        f"🔴 Reviewer guidance  🔵 Policy  🟢 Keywords  🟡 Evidence"
        f"</div>", unsafe_allow_html=True)

# Regenerate failed sections
failed = [s for s in sections if s.get("_parse_failed")]
if failed:
    warn = D["warning"]
    st.markdown(
        f"<div style='background:{warn}22;border:1px solid {warn};border-radius:8px;"
        f"padding:0.7rem 1rem;margin-bottom:0.5rem'>"
        f"<strong style='color:{warn}'>⚠ {len(failed)} section(s) need regeneration</strong></div>",
        unsafe_allow_html=True)
    if st.button(f"🔄 Regenerate {len(failed)} Failed Section(s)", key="regen"):
        intel2   = build_section_intelligence(analysis, latest_concept)
        updated  = list(sections)
        to_regen = [s for s in updated if s.get("_parse_failed")]
        batches2 = [to_regen[i:i+4] for i in range(0, len(to_regen), 4)]
        prog2    = st.progress(0)
        for bi, batch in enumerate(batches2):
            prog2.progress((bi+1)/len(batches2), text=f"Batch {bi+1}/{len(batches2)}...")
            new_batch = annotate_section_batch(batch, intel2, programme)
            for new_sec in new_batch:
                for j, s in enumerate(updated):
                    if s.get("id") == new_sec.get("id"):
                        updated[j] = new_sec
            update_proposal_architecture(arch["id"], {"sections": updated})
        prog2.progress(1.0)
        st.success("Done!"); st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# General advice + priorities
if arch.get("general_advice"):
    with st.expander("💡 Strategic Advice", expanded=True):
        st.markdown(
            f"<div style='background:{D["bg2"]};border-left:4px solid {acc};"
            f"border-radius:8px;padding:1rem 1.2rem'>{arch["general_advice"]}</div>",
            unsafe_allow_html=True)

if arch.get("top_5_priorities"):
    with st.expander("⭐ Top 5 Priorities", expanded=True):
        for i, p in enumerate(arch["top_5_priorities"],1):
            suc = D["success"]
            st.markdown(
                f"<div style='background:{D["bg2"]};border-left:3px solid {suc};"
                f"border-radius:6px;padding:0.4rem 0.8rem;margin-bottom:0.3rem'>"
                f"<strong style='color:{suc}'>{i}.</strong> {p}</div>",
                unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
section_label("Section-by-Section Guidance")

for sec in sorted(sections, key=lambda x: x.get("order",0)):
    level = sec.get("level",1)
    orig  = sec.get("original_title","")
    title = sec.get("ai_title","") or orig or sec.get("title","")
    sid   = sec.get("id","")
    failed_sec = sec.get("_parse_failed",False)

    lvl_colors = [acc, D["accent2"], D["muted"]]
    bc = lvl_colors[min(level-1,2)]

    label = f"{'#'*level} {sid} — {title}"
    if failed_sec:
        label += "  ⚠️ (needs regeneration)"

    with st.expander(label, expanded=(level==1 and not failed_sec)):
        if failed_sec:
            warn = D["warning"]
            st.markdown(
                f"<div style='background:{warn}22;border-left:3px solid {warn};"
                f"border-radius:6px;padding:0.4rem 0.8rem;font-size:0.81rem;"
                f"color:{warn};margin-bottom:0.4rem'>"
                f"⚠ This section used generic fallback. Click Regenerate above.</div>",
                unsafe_allow_html=True)

        if title != orig and orig:
            st.caption(f"Enhanced from: {orig}")

        c1, c2 = st.columns([3,2])

        def _safe_list(v):
            if not v: return []
            if isinstance(v,list): return [str(x) for x in v]
            return [str(v)]

        def _safe_pol(p):
            if isinstance(p,dict):
                t = p.get("policy","") or p.get("name","") or str(p)
                h = p.get("how","") or p.get("connection","")
                return f"{t} — {h}" if h else t
            return str(p)

        with c1:
            # Main guidance paragraph (concept note + call integrated)
            gp = sec.get("guidance_paragraph","")
            if gp:
                blue = "#4488CC"
                st.markdown(
                    f"<div style='background:{D["bg2"]};border-left:4px solid {acc};"
                    f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem'>"
                    f"<strong style='color:{acc}'>📝 WHAT TO WRITE HERE:</strong><br>"
                    f"<span style='color:{D["text"]};font-size:0.85rem'>{gp}</span>"
                    f"</div>", unsafe_allow_html=True)

            # Gaps to address
            gap_text = sec.get("gaps_to_address","")
            if gap_text:
                danger = D["danger"]
                st.markdown(
                    f"<div style='background:{danger}11;border-left:3px solid {danger};"
                    f"border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem'>"
                    f"<strong style='color:{danger}'>⚠ GAP TO ADDRESS:</strong> "
                    f"<span style='color:{D["text"]};font-size:0.83rem'>{gap_text}</span>"
                    f"</div>", unsafe_allow_html=True)

            rg = _safe_list(sec.get("reviewer_guidance"))
            if rg:
                danger = D["danger"]
                pts = "".join(f"<div style='margin:2px 0'>&#8226; {p}</div>" for p in rg)
                st.markdown(
                    f"<div style='background:{danger}11;border-left:4px solid {danger};"
                    f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem'>"
                    f"<strong style='color:{danger}'>🔴 REVIEWER EXPECTS:</strong><br>"
                    f"<div style='color:{D["text"]};font-size:0.84rem;margin-top:0.25rem'>"
                    f"{pts}</div></div>", unsafe_allow_html=True)

            pc = sec.get("policy_connections")
            if pc:
                blue  = "#4488CC"
                items = pc if isinstance(pc,list) else [pc]
                pts   = "".join(f"<div style='margin:2px 0'>&#8226; {_safe_pol(p)}</div>"
                                for p in items)
                st.markdown(
                    f"<div style='background:{blue}11;border-left:4px solid {blue};"
                    f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem'>"
                    f"<strong style='color:{blue}'>🔵 POLICY CONNECTIONS:</strong><br>"
                    f"<div style='color:{D["text"]};font-size:0.84rem;margin-top:0.25rem'>"
                    f"{pts}</div></div>", unsafe_allow_html=True)

        with c2:
            kws = _safe_list(sec.get("keywords_to_include"))
            if kws:
                green = D["success"]
                st.markdown(
                    f"<div style='background:{green}11;border-left:4px solid {green};"
                    f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
                    f"<strong style='color:{green}'>🟢 KEYWORDS:</strong><br>"
                    f"<span style='color:{D["text"]};font-size:0.82rem'>"
                    + " &nbsp;&#183;&nbsp; ".join(kws)
                    + "</span></div>", unsafe_allow_html=True)

            ev = sec.get("measures_and_evidence","")
            if ev:
                amber = D["warning"]
                st.markdown(
                    f"<div style='background:{amber}11;border-left:4px solid {amber};"
                    f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
                    f"<strong style='color:{amber}'>🟡 EVIDENCE NEEDED:</strong><br>"
                    f"<span style='color:{D["text"]};font-size:0.82rem'>{ev}</span>"
                    f"</div>", unsafe_allow_html=True)

            wc = sec.get("word_count_guidance","")
            cm = _safe_list(sec.get("common_mistakes"))
            if wc: st.caption(f"📏 {wc}")
            if cm:
                with st.expander("Mistakes to avoid"):
                    for m in cm:
                        st.markdown(
                            f"<span style='color:{D["danger"]};font-size:0.81rem'>&#x2717; {m}</span>",
                            unsafe_allow_html=True)

st.markdown("<br>")
b1, b2 = st.columns(2)
with b1:
    if st.button("🎯 Run Mini Review", type="primary", use_container_width=True):
        st.switch_page("pages/mini_review.py")
with b2:
    if st.button("← Round 2a", use_container_width=True):
        st.switch_page("pages/round2a_concept.py")
