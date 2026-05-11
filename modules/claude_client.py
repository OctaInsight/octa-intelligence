"""
Octa Intelligence — Claude API Client
Handles real-time and batch API calls for all analysis rounds.
All prompts are centralised here.
"""
import json
import streamlit as st
import anthropic
from config import CLAUDE_MODEL_REALTIME, CLAUDE_MODEL_BATCH, CLAUDE_MAX_TOKENS


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=st.secrets["anthropic"]["api_key"]
    )


def _call_realtime(system: str, user: str,
                   max_tokens: int = CLAUDE_MAX_TOKENS) -> str | None:
    """Single real-time API call. Returns text response or None on error."""
    try:
        client = _client()
        msg    = client.messages.create(
            model      = CLAUDE_MODEL_REALTIME,
            max_tokens = max_tokens,
            system     = system,
            messages   = [{"role": "user", "content": user}],
        )
        return msg.content[0].text
    except Exception as e:
        st.error(f"Claude API error: {e}")
        return None


def _parse_json_response(text: str) -> dict | list | None:
    """
    Robustly extract JSON from Claude response.
    Handles: plain JSON, ```json blocks, JSON with surrounding text.
    """
    import re
    if not text:
        return None
    clean = text.strip()

    # Remove markdown code fences (```json ... ``` or ``` ... ```)
    fence = re.sub(r'^```(?:json)?\s*', '', clean, flags=re.MULTILINE)
    fence = re.sub(r'```\s*$', '', fence, flags=re.MULTILINE).strip()

    # Try direct parse first
    try:
        return json.loads(fence)
    except Exception:
        pass

    # Try original text
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Find the largest JSON object or array in the text
    for pattern in [r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # nested objects
                    r'\{.*?\}',                               # simple objects
                    r'\[.*?\]']:                              # arrays
        matches = re.findall(pattern, fence, re.DOTALL)
        # Try from largest to smallest
        for m in sorted(matches, key=len, reverse=True):
            try:
                return json.loads(m)
            except Exception:
                continue

    # Last resort: find first { and last } and try that
    start = fence.find('{')
    end   = fence.rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(fence[start:end+1])
        except Exception:
            pass

    return None


# ════════════════════════════════════════════════════════════════════════════════
# ROUND 1 — CALL INTELLIGENCE ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════

ROUND1_SYSTEM = (
    "You are an EU research funding strategist. "
    "Analyse the funding call and return ONLY a JSON object. "
    "No markdown. No code fences. No explanation. "
    "Start with { and end with }. Nothing else."
)

def build_round1_prompt(call_text: str, policy_texts: dict,
                         guide_text: str, briefing: dict) -> str:
    """Build the Round 1 analysis prompt — kept concise to ensure valid JSON output."""

    # Truncate inputs to stay well within token limits
    call_snippet   = call_text[:25000]
    guide_snippet  = guide_text[:8000] if guide_text else ""
    policy_snippet = ""
    for title, text in list(policy_texts.items())[:4]:   # max 4 policy docs
        policy_snippet += f"\n\n### {title}\n{text[:6000]}"

    briefing_snippet = (
        f"Coordinator: {briefing.get('coordinator_name','')}\n"
        f"Strategy: {briefing.get('consortium_strategy','')}\n"
        f"Strengths: {briefing.get('unique_selling_point','')}\n"
        f"Advantage: {briefing.get('competitive_advantage','')}\n"
        f"Notes: {briefing.get('additional_notes','')}"
    )

    prompt = f"""Analyse this EU funding call and return a JSON intelligence report.

=== CALL TEXT ===
{call_snippet}
"""
    if guide_snippet:
        prompt += f"""
=== REVIEWER GUIDELINES ===
{guide_snippet}
"""
    if policy_snippet:
        prompt += f"""
=== POLICY DOCUMENTS ===
{policy_snippet}
"""
    prompt += f"""
=== OUR CONSORTIUM ===
{briefing_snippet}

Return ONLY this JSON object (no markdown, no code fences, start with {{):
{{
  "call_objectives": [
    {{"title": "Objective 1", "description": "...", "priority": "primary"}}
  ],
  "expected_outcomes": [
    {{"outcome": "...", "timeframe": "short-term"}}
  ],
  "expected_impacts": [
    {{"impact": "...", "level": "scientific|economic|social|policy"}}
  ],
  "expected_outputs": [
    {{"output": "...", "type": "tool|report|platform|dataset|other"}}
  ],
  "recommended_kpis": [
    {{"kpi": "...", "unit": "..."}}
  ],
  "policy_framing": {{
    "primary_policies": [{{"policy": "...", "relevance_score": 8, "how_call_references": "..."}}],
    "policy_narrative": "How this call fits within EU policy..."
  }},
  "master_keywords": [
    {{"keyword": "...", "importance": "critical|high|medium"}}
  ],
  "synergy_initiatives": [
    {{"name": "...", "description": "...", "how_to_build_synergy": "..."}}
  ],
  "hidden_messages": "What is implicitly expected but not stated in the call...",
  "expected_partner_profiles": [
    {{"profile_type": "...", "description": "...", "role": "coordinator|partner"}}
  ],
  "consortium_positioning": "How our consortium is positioned relative to this call...",
  "strategic_recommendations": [
    {{"priority": 1, "recommendation": "...", "action": "..."}}
  ]
}}"""
    return prompt



def run_round1_realtime(call_text: str, policy_texts: dict,
                         guide_text: str, briefing: dict) -> dict | None:
    """Run Round 1 analysis in real-time. Returns parsed JSON dict."""
    prompt   = build_round1_prompt(call_text, policy_texts, guide_text, briefing)
    response = _call_realtime(ROUND1_SYSTEM, prompt, max_tokens=8000)
    if not response:
        return None
    parsed = _parse_json_response(response)
    if not parsed:
        st.error("Round 1: Could not parse Claude's response as JSON.")
        st.text_area("Raw response (for debugging)", response[:2000])
    return parsed


def generate_document_summary(text: str, title: str) -> dict | None:
    """
    Generate a summary + keywords for a policy document.
    Used when uploading to the library.
    Returns {summary, keywords, short_description, category_suggestion}
    """
    system = """You are an expert EU policy analyst. 
Summarise policy documents concisely for a research funding intelligence system. 
Output only valid JSON."""

    prompt = f"""Analyse this EU policy document titled "{title}" and return JSON:

{text[:60000]}

Return ONLY:
{{
  "short_description": "3-5 sentence overview of what this document is and why it matters for EU research proposals",
  "detailed_summary": "Comprehensive 10-15 sentence summary covering: purpose, key targets, main priorities, implications for proposals",
  "keywords": ["keyword1", "keyword2", ...],
  "category_suggestion": "one of: Green Deal & Sustainability | Digital & AI | Research & Innovation | Education & Skills | Health | Social & Inclusion | Regional Development & Cohesion | International Cooperation | Security & Defence | Space | Energy | Transport & Mobility | Food & Agriculture | Culture & Creative Industries | Other",
  "key_targets": ["specific measurable target 1", "target 2", ...],
  "relevant_programmes": ["Horizon Europe", "Erasmus+", "LIFE", ...]
}}"""

    response = _call_realtime(system, prompt, max_tokens=2000)
    if not response:
        return None
    return _parse_json_response(response)


# ════════════════════════════════════════════════════════════════════════════════
# ROUND 2a — CONCEPT NOTE EVALUATION
# ════════════════════════════════════════════════════════════════════════════════

def run_round2a(concept_text: str, call_analysis: dict) -> tuple:
    """
    Evaluate concept note against Round 1 findings.
    Returns (parsed_dict, raw_text) — raw_text always set, parsed_dict may be None.
    """
    system = (
        "You are an EU proposal evaluator. "
        "Evaluate the concept note against the call intelligence. "
        "Return ONLY a JSON object. No markdown. No code fences. "
        "Start with { and end with }. Nothing else."
    )

    # Compact call summary
    objectives = [o.get("title","") for o in call_analysis.get("call_objectives",[])[:5]]
    keywords   = [k.get("keyword","") for k in call_analysis.get("master_keywords",[])
                  if k.get("importance") in ("critical","high")][:15]
    recs       = [r.get("recommendation","") for r in
                  call_analysis.get("strategic_recommendations",[])[:4]]
    outcomes   = [o.get("outcome","") for o in call_analysis.get("expected_outcomes",[])[:4]]

    prompt = f"""Evaluate this concept note against the call intelligence.

=== CALL OBJECTIVES ===
{chr(10).join(f"- {o}" for o in objectives)}

=== EXPECTED OUTCOMES ===
{chr(10).join(f"- {o}" for o in outcomes)}

=== CRITICAL KEYWORDS (must appear in proposal) ===
{", ".join(keywords)}

=== STRATEGIC RECOMMENDATIONS ===
{chr(10).join(f"- {r}" for r in recs)}

=== CONSORTIUM POSITIONING ===
{call_analysis.get("consortium_positioning","")[:1000]}

=== CONCEPT NOTE ===
{concept_text[:15000]}

Return ONLY this JSON (no markdown, start with {{):
{{
  "overall_alignment_score": 65,
  "scores_by_dimension": {{
    "objectives":  {{"score": 70, "comment": "..."}},
    "impact":      {{"score": 60, "comment": "..."}},
    "innovation":  {{"score": 75, "comment": "..."}},
    "partners":    {{"score": 65, "comment": "..."}},
    "policy":      {{"score": 60, "comment": "..."}}
  }},
  "strengths": [
    {{"dimension": "innovation", "description": "...", "evidence": "quote from concept"}}
  ],
  "gaps": [
    {{"dimension": "impact", "description": "...", "severity": "high", "suggestion": "..."}}
  ],
  "missing_keywords": ["keyword1", "keyword2"],
  "recommendations": [
    {{"priority": 1, "action": "...", "rationale": "..."}}
  ],
  "readiness_verdict": "promising",
  "overall_comment": "2-3 paragraph honest assessment of this concept note."
}}"""

    raw_text = _call_realtime(system, prompt, max_tokens=4000)
    if not raw_text:
        return None, None
    parsed = _parse_json_response(raw_text)
    return parsed, raw_text



# ════════════════════════════════════════════════════════════════════════════════
# ROUND 2b — PROPOSAL ARCHITECTURE
# ════════════════════════════════════════════════════════════════════════════════

def build_section_intelligence(call_analysis: dict,
                               concept_evaluation: dict | None) -> dict:
    """Build compact intelligence dict reused across all section annotation calls."""
    objectives = "; ".join(
        o.get("title","") for o in call_analysis.get("call_objectives",[])[:5]
    )
    keywords = [
        k.get("keyword","")
        for k in call_analysis.get("master_keywords",[])
        if k.get("importance") in ("critical","high")
    ][:12]
    pf       = call_analysis.get("policy_framing",{})
    policies = [p.get("policy","") for p in
                (pf.get("primary_policies",[]) if isinstance(pf,dict) else [])[:5]]
    hidden   = str(call_analysis.get("hidden_messages",""))[:300]

    # From concept evaluation
    concept_text   = ""
    concept_strengths = []
    concept_gaps   = []
    concept_missing_kws = []
    if concept_evaluation:
        concept_text = str(concept_evaluation.get("concept_text",""))[:3000]
        concept_strengths = [
            s.get("description","") for s in concept_evaluation.get("strengths",[])[:4]
        ]
        concept_gaps = [
            {"dim": g.get("dimension",""), "desc": g.get("description",""),
             "sug": g.get("suggestion","")}
            for g in concept_evaluation.get("gaps",[])[:5]
        ]
        concept_missing_kws = concept_evaluation.get("missing_keywords",[])[:8]

    return {
        "objectives":          objectives,
        "keywords":            keywords,
        "policies":            policies,
        "hidden":              hidden,
        "concept_text":        concept_text,
        "concept_strengths":   concept_strengths,
        "concept_gaps":        concept_gaps,
        "missing_keywords":    concept_missing_kws,
    }


def annotate_section_batch(sections_batch: list, intel: dict,
                            programme: str) -> list:
    """
    Annotate 3-5 sections in one API call.
    Returns list of annotated dicts. Falls back to minimal if parse fails.
    """
    system = (
        "You are a senior EU proposal strategist. "
        "Return ONLY a JSON array starting with [ and ending with ]. "
        "No markdown. No text before [ or after ]."
    )

    n    = len(sections_batch)
    kws  = ", ".join(intel.get("keywords",[])[:10])
    pols = "; ".join(intel.get("policies",[])[:4])
    obj  = intel.get("objectives","")[:250]
    hid  = intel.get("hidden","")[:200]

    # Concept note summary
    concept_summary = ""
    if intel.get("concept_text"):
        concept_summary  = "CONCEPT NOTE (what the team plans to write):\n"
        concept_summary += intel["concept_text"][:1500] + "\n"
        if intel.get("concept_strengths"):
            concept_summary += "Strengths in concept: " + "; ".join(intel["concept_strengths"][:3]) + "\n"
        if intel.get("concept_gaps"):
            gaps_str = "; ".join(g["desc"] for g in intel["concept_gaps"][:3] if g.get("desc"))
            concept_summary += f"Gaps to address: {gaps_str}\n"
        if intel.get("missing_keywords"):
            concept_summary += "Missing keywords: " + ", ".join(intel["missing_keywords"][:6])

    # Section list
    sec_list = "\n".join(
        f"{i+1}. [{s.get('id','')}] {s.get('title','')} (level {s.get('level',1)})"
        for i, s in enumerate(sections_batch)
    )

    prompt = f"""Annotate these {n} sections of a {programme} proposal.

CALL CONTEXT:
- Objectives: {obj}
- Critical keywords: {kws}
- Key policies: {pols}
- Hidden expectations: {hid}

{concept_summary}

SECTIONS TO ANNOTATE:
{sec_list}

For EACH section write guidance that:
1. Tells the writer exactly what to include FROM THEIR CONCEPT NOTE
2. Identifies what the REVIEWER will specifically check here
3. Lists keywords and policies to mention IN THIS SECTION
4. Flags any GAPS from the concept that must be addressed here

Keep guidance concise and specific — 2-3 focused sentences per field, not generic text.

Return a JSON ARRAY with exactly {n} objects:
[
  {{
    "id": "exact id",
    "level": 1,
    "original_title": "exact title",
    "ai_title": "improved title aligned with call language",
    "guidance_paragraph": "2-3 sentences telling the writer SPECIFICALLY what to write in this section based on their concept note and call requirements. Reference their actual content.",
    "reviewer_guidance": ["Specific thing reviewer checks in THIS section - not generic", "Point 2", "Point 3"],
    "policy_connections": ["Specific policy - how to cite it here"],
    "keywords_to_include": ["kw1", "kw2", "kw3"],
    "gaps_to_address": "Specific gap from concept note that must be fixed in this section",
    "word_count_guidance": "400-600 words"
  }}
]"""

    raw    = _call_realtime(system, prompt, max_tokens=4000)
    parsed = _parse_json_response(raw) if raw else None

    # Validate result
    if isinstance(parsed, list) and len(parsed) >= len(sections_batch) - 1:
        for p in parsed:
            if isinstance(p, dict): p["_parse_failed"] = False
        # Pad if short
        while len(parsed) < len(sections_batch):
            sec = sections_batch[len(parsed)]
            parsed.append(_minimal_section(sec, intel))
        return parsed

    if isinstance(parsed, dict) and parsed.get("sections"):
        return parsed["sections"]

    # Batch failed — return minimal for all
    return [_minimal_section(s, intel) for s in sections_batch]


def _minimal_section(sec: dict, intel: dict) -> dict:
    """Minimal but non-generic fallback using actual intel data."""
    title = sec.get("title","")
    return {
        "id":            sec.get("id",""),
        "level":         sec.get("level",1),
        "order":         sec.get("order",0),
        "original_title":title,
        "ai_title":      title,
        "guidance_paragraph": (
            f"In this section ({title}), present your approach clearly linking to "
            f"the call objectives: {intel.get('objectives','')[:150]}. "
            f"Ensure the following keywords appear: {', '.join(intel.get('keywords',[])[:4])}."
        ),
        "reviewer_guidance": [
            f"Check alignment with call objective: {intel.get('objectives','')[:80]}",
            "Verify clear methodology and innovation claim",
            f"Look for policy references: {', '.join(intel.get('policies',[])[:2])}",
        ],
        "policy_connections": intel.get("policies",[])[:2],
        "keywords_to_include": intel.get("keywords",[])[:5],
        "gaps_to_address": "; ".join(
            g["desc"] for g in intel.get("concept_gaps",[])[:2] if g.get("desc")
        ) or "Address all call requirements explicitly.",
        "word_count_guidance": "400-600 words",
        "_parse_failed": True,
    }


def generate_overall_advice(intel: dict, programme: str,
                             section_titles: list) -> dict:
    """Generate overall strategic advice + top 5 priorities."""
    system = (
        "You are an EU proposal expert. "
        "Return ONLY a JSON object starting with {. No markdown."
    )
    titles_str = "; ".join(section_titles[:8])
    concept_note = intel.get("concept_text","")[:800]
    gaps_str     = "; ".join(g["desc"] for g in intel.get("concept_gaps",[])[:3] if g.get("desc"))

    prompt = f"""Strategic advice for writing a {programme} proposal.

Sections: {titles_str}
Objectives: {intel.get("objectives","")[:200]}
Concept note summary: {concept_note}
Key gaps to address: {gaps_str}

Return ONLY:
{{
  "general_advice": "3-4 sentences of strategic writing advice specific to this concept and call",
  "top_5_priorities": [
    "Most critical priority based on call + concept analysis",
    "Priority 2",
    "Priority 3",
    "Priority 4",
    "Priority 5"
  ]
}}"""

    raw    = _call_realtime(system, prompt, max_tokens=600)
    parsed = _parse_json_response(raw) if raw else None
    return parsed if isinstance(parsed, dict) else {"general_advice":"","top_5_priorities":[]}




# ════════════════════════════════════════════════════════════════════════════════
# MINI ROUND 3 — ARCHITECTURE REVIEW
# ════════════════════════════════════════════════════════════════════════════════

def run_mini_review(architecture_sections: list,
                    reviewer_reference: str,
                    has_guide: bool) -> dict | None:
    """
    Quick review of the architecture against reviewer guide or call text.
    Returns scorecard JSON.
    """
    system = """You are an EU proposal evaluator. 
Review a proposed writing architecture and score each section's alignment 
with the evaluation criteria. Be honest and specific. Output only valid JSON."""

    reference_label = "REVIEWER GUIDELINES" if has_guide else "CALL TEXT (no reviewer guide available)"

    sections_str = json.dumps([
        {k: s.get(k) for k in ["id","ai_title","reviewer_guidance","keywords_to_include"]}
        for s in architecture_sections
    ], indent=2)[:8000]

    prompt = f"""Review this proposal architecture against the evaluation reference.

=== {reference_label} ===
{reviewer_reference[:30000]}

=== PROPOSED ARCHITECTURE (sections with guidance) ===
{sections_str}

Return ONLY a JSON object:
{{
  "overall_score": 0-100,
  "section_scores": [
    {{
      "section_id": "...",
      "title": "...",
      "rating": "strong|needs_work|weak|missing",
      "score": 0-100,
      "note": "specific, actionable comment",
      "quick_fix": "what to add/change to improve this section"
    }}
  ],
  "critical_gaps": [
    {{"gap": "...", "impact": "will lose points on: ...", "fix": "..."}}
  ],
  "quick_wins": [
    {{"action": "...", "expected_gain": "..."}}
  ],
  "readiness_score_breakdown": {{
    "Excellence": 0-100,
    "Impact":     0-100,
    "Implementation": 0-100
  }},
  "overall_verdict": "ready|mostly_ready|needs_work|significant_gaps",
  "key_message": "One paragraph summary of the most important things to address"
}}"""

    response = _call_realtime(system, prompt, max_tokens=4000)
    if not response:
        return None
    return _parse_json_response(response)
