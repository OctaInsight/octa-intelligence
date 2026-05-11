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
    """
    Build a compact intelligence dict to pass into each section annotation call.
    Called once, reused for every section.
    """
    objectives = "; ".join(
        o.get("title","") for o in call_analysis.get("call_objectives",[])[:6]
    )
    keywords = [
        k.get("keyword","")
        for k in call_analysis.get("master_keywords",[])
        if k.get("importance") in ("critical","high")
    ][:12]

    pf = call_analysis.get("policy_framing",{})
    policies = []
    if isinstance(pf, dict):
        policies = [p.get("policy","") for p in pf.get("primary_policies",[])[:5]]

    gaps = []
    if concept_evaluation:
        gaps = [g.get("description","") for g in concept_evaluation.get("gaps",[])[:4]
                if g.get("description")]

    recs = [r.get("recommendation","") for r in
            call_analysis.get("strategic_recommendations",[])[:3]]

    return {
        "objectives": objectives,
        "keywords":   keywords,
        "policies":   policies,
        "gaps":       "; ".join(gaps),
        "recommendations": "; ".join(recs),
        "hidden":     str(call_analysis.get("hidden_messages",""))[:400],
    }


def annotate_one_section(sec: dict, intel: dict, programme: str) -> dict:
    """
    Annotate a SINGLE section with tailored reviewer guidance.
    Returns annotated dict. Never raises — falls back to minimal if parse fails.
    """
    system = (
        "You are a senior EU proposal writing expert. "
        "Return ONLY a JSON object starting with { and ending with }. "
        "No markdown. No code fences. No text before or after the JSON."
    )

    sid   = sec.get("id","")
    title = sec.get("title","")
    level = sec.get("level",1)
    kws   = ", ".join(intel.get("keywords",[])[:8])
    pols  = "; ".join(intel.get("policies",[])[:4])
    obj   = intel.get("objectives","")[:300]
    gaps  = intel.get("gaps","")[:200]
    recs  = intel.get("recommendations","")[:200]

    prompt = f"""Write detailed reviewer guidance for this section of a {programme} proposal.

SECTION: [{sid}] {title} (heading level {level})

CALL INTELLIGENCE:
- Objectives: {obj}
- Critical keywords: {kws}
- Key policies to cite: {pols}
- Gaps identified in concept: {gaps}
- Strategic recommendations: {recs}

Return ONLY this JSON object:
{{
  "id": "{sid}",
  "level": {level},
  "original_title": "{title}",
  "ai_title": "improved version of the section title, aligned with call language",
  "reviewer_guidance": [
    "Specific thing 1 that reviewers check in this exact section",
    "Specific thing 2",
    "Specific thing 3"
  ],
  "policy_connections": [
    "Policy name - exactly how to reference it in this section"
  ],
  "keywords_to_include": ["keyword1", "keyword2", "keyword3", "keyword4"],
  "measures_and_evidence": "Specific KPIs, baselines or data the reviewer expects here",
  "word_count_guidance": "recommended word count, e.g. 400-600 words",
  "common_mistakes": ["Common mistake proposers make in this section"]
}}"""

    raw    = _call_realtime(system, prompt, max_tokens=1000)
    parsed = _parse_json_response(raw) if raw else None

    if isinstance(parsed, dict) and parsed.get("reviewer_guidance"):
        parsed["_parse_failed"] = False
        parsed["order"] = sec.get("order", 0)
        return parsed

    # Minimal fallback — still better than nothing
    return {
        "id": sid, "level": level, "order": sec.get("order",0),
        "original_title": title, "ai_title": title,
        "reviewer_guidance": [
            f"Address the call objectives related to {title}",
            "Demonstrate clear innovation and scientific rigour",
            "Show alignment with EU policy priorities"
        ],
        "policy_connections": intel.get("policies",[])[:2],
        "keywords_to_include": intel.get("keywords",[])[:4],
        "measures_and_evidence": "Include relevant KPIs, baselines and impact evidence",
        "word_count_guidance": "400-600 words",
        "common_mistakes": ["Being too generic", "Missing call-specific terminology"],
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
    prompt = f"""Give strategic advice for writing a {programme} proposal.

Sections: {titles_str}
Objectives: {intel.get("objectives","")[:250]}
Key recommendations: {intel.get("recommendations","")[:250]}

Return ONLY:
{{
  "general_advice": "3-4 sentences of overall strategic writing advice",
  "top_5_priorities": [
    "Most important priority 1",
    "Priority 2",
    "Priority 3",
    "Priority 4",
    "Priority 5"
  ]
}}"""

    raw    = _call_realtime(system, prompt, max_tokens=600)
    parsed = _parse_json_response(raw) if raw else None
    if isinstance(parsed, dict):
        return parsed
    return {"general_advice": "", "top_5_priorities": []}




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
