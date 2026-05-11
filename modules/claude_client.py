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

ROUND1_SYSTEM = """You are a senior EU research funding strategist with 20 years of experience winning competitive grants. You analyse funding calls and produce strategic intelligence reports that help consortia craft winning proposals.

CRITICAL INSTRUCTION: Your entire response must be a single valid JSON object. Do NOT include any text before or after the JSON. Do NOT use markdown code blocks. Do NOT include ```json or ```. Start your response with { and end with }. Nothing else."""

def build_round1_prompt(call_text: str, policy_texts: dict,
                         guide_text: str, briefing: dict) -> str:
    """
    Build the Round 1 analysis prompt.
    policy_texts: {title: text}
    briefing: consortium briefing dict
    """
    policy_section = ""
    for title, text in policy_texts.items():
        policy_section += f"\n\n=== POLICY DOCUMENT: {title} ===\n{text[:30000]}"

    guide_section = f"\n\n=== REVIEWER GUIDELINES ===\n{guide_text}" if guide_text else ""

    briefing_section = f"""
=== CONSORTIUM BRIEFING ===
Coordinator: {briefing.get('coordinator_name','')} ({briefing.get('coordinator_type','')})
Consortium strategy: {briefing.get('consortium_strategy','')}
Unique selling point: {briefing.get('unique_selling_point','')}
Competitive advantage: {briefing.get('competitive_advantage','')}
Geographic coverage: {briefing.get('geographic_rationale','')}
Innovation type: {briefing.get('innovation_type','')}
Partner profiles: {json.dumps(briefing.get('partner_profiles',[]), indent=2)[:3000]}
Additional notes: {briefing.get('additional_notes','')}
"""

    return f"""Analyse the following funding call and related documents. 
Produce a comprehensive strategic intelligence report as a JSON object.

=== CALL TEXT ===
{call_text[:80000]}
{policy_section}
{guide_section}
{briefing_section}

Your response must be ONLY a JSON object — no markdown, no explanation, no code fences.
Start directly with {{ and end with }}. 

Return a JSON object with exactly these keys:

{{
  "call_objectives": [
    {{"id": 1, "title": "...", "description": "...", "priority": "primary|secondary", "evidence": "quote from call"}}
  ],
  "expected_outcomes": [
    {{"id": 1, "outcome": "...", "timeframe": "...", "measurability": "high|medium|low"}}
  ],
  "expected_impacts": [
    {{"id": 1, "impact": "...", "level": "scientific|economic|social|policy", "timeframe": "short|medium|long"}}
  ],
  "expected_outputs": [
    {{"id": 1, "output": "...", "type": "tool|report|platform|dataset|methodology|guidelines|other"}}
  ],
  "recommended_kpis": [
    {{"id": 1, "kpi": "...", "unit": "...", "source": "explicit|implied", "target_type": "quantitative|qualitative"}}
  ],
  "policy_framing": {{
    "primary_policies": [
      {{"policy": "...", "relevance_score": 1-10, "how_call_references": "...", "key_targets_to_mention": ["..."]}}
    ],
    "secondary_policies": [
      {{"policy": "...", "relevance_score": 1-10, "connection": "..."}}
    ],
    "policy_narrative": "3-5 sentence explanation of how the call sits within the EU policy landscape"
  }},
  "master_keywords": [
    {{"keyword": "...", "frequency": 0, "importance": "critical|high|medium", "source": "call|guide|policy|all"}}
  ],
  "synergy_initiatives": [
    {{"name": "...", "type": "project|programme|initiative|platform", "description": "...", "how_to_build_synergy": "..."}}
  ],
  "hidden_messages": "Free text — what is implicitly expected but not explicitly stated in the call",
  "expected_partner_profiles": [
    {{"profile_type": "...", "description": "...", "role": "coordinator|partner|associate", "is_mandatory": true}}
  ],
  "consortium_positioning": "Specific assessment of how THIS consortium (from the briefing) is positioned. What are their strengths, gaps, and strategic recommendations given the call requirements.",
  "strategic_recommendations": [
    {{"priority": 1, "recommendation": "...", "rationale": "...", "action": "..."}}
  ]
}}"""


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

def run_round2a(concept_text: str, call_analysis: dict) -> dict | None:
    """Evaluate a concept note against Round 1 findings. Returns JSON dict."""
    system = """You are a senior EU proposal evaluator with expertise in Horizon Europe, 
Erasmus+ and other EU programmes. You provide honest, constructive assessments of 
proposal concepts. Output only valid JSON."""

    analysis_summary = json.dumps({
        k: call_analysis.get(k, [])
        for k in ["call_objectives","expected_outcomes","expected_impacts",
                  "master_keywords","strategic_recommendations"]
    }, indent=2)[:15000]

    prompt = f"""Evaluate this concept note against the call intelligence analysis.

=== CALL INTELLIGENCE SUMMARY ===
{analysis_summary}

=== CONCEPT NOTE ===
{concept_text[:20000]}

Return ONLY a JSON object:
{{
  "overall_alignment_score": 0-100,
  "scores_by_dimension": {{
    "objectives":  {{"score": 0-100, "comment": "..."}},
    "impact":      {{"score": 0-100, "comment": "..."}},
    "innovation":  {{"score": 0-100, "comment": "..."}},
    "partners":    {{"score": 0-100, "comment": "..."}},
    "policy":      {{"score": 0-100, "comment": "..."}}
  }},
  "strengths": [
    {{"dimension": "...", "description": "...", "evidence": "quote from concept"}}
  ],
  "gaps": [
    {{"dimension": "...", "description": "...", "severity": "high|medium|low", "suggestion": "..."}}
  ],
  "missing_keywords": ["keyword not in concept but critical for call"],
  "recommendations": [
    {{"priority": 1, "action": "...", "rationale": "..."}}
  ],
  "readiness_verdict": "strong|promising|needs_work|significant_revision_needed",
  "overall_comment": "2-3 paragraph honest assessment"
}}"""

    response = _call_realtime(system, prompt, max_tokens=4000)
    if not response:
        return None
    return _parse_json_response(response)


# ════════════════════════════════════════════════════════════════════════════════
# ROUND 2b — PROPOSAL ARCHITECTURE
# ════════════════════════════════════════════════════════════════════════════════

def run_round2b(structure_template: list, call_analysis: dict,
                concept_evaluation: dict | None,
                programme: str, user_custom_titles: dict = None) -> dict | None:
    """
    Generate annotated proposal architecture.
    structure_template: list of section dicts from PROGRAMMES config
    user_custom_titles: {section_id: user_title} optional overrides
    Returns JSON with enriched sections.
    """
    system = """You are a master EU proposal writer and strategic consultant. 
You create detailed, actionable proposal writing guides that help researchers 
win competitive EU funding. You know exactly what reviewers look for in each 
section of every EU programme. Output only valid JSON."""

    call_summary = json.dumps({
        k: call_analysis.get(k, [])
        for k in ["call_objectives","expected_outcomes","expected_impacts",
                  "master_keywords","policy_framing","strategic_recommendations",
                  "hidden_messages","recommended_kpis"]
    }, indent=2)[:12000]

    gaps_summary = ""
    if concept_evaluation:
        gaps_summary = f"""
=== CONCEPT GAPS TO ADDRESS ===
{json.dumps(concept_evaluation.get('gaps',[]), indent=2)[:3000]}
"""

    custom_titles_note = ""
    if user_custom_titles:
        custom_titles_note = f"""
=== USER'S SECTION TITLES (enhance these, don't replace without good reason) ===
{json.dumps(user_custom_titles, indent=2)}
"""

    structure_str = json.dumps(structure_template, indent=2)

    prompt = f"""Generate a fully annotated proposal architecture for a {programme} proposal.

=== CALL INTELLIGENCE ===
{call_summary}
{gaps_summary}
{custom_titles_note}

=== BASE STRUCTURE TO ANNOTATE ===
{structure_str}

For EACH section in the structure, return an enriched version with:
- ai_title: improved title (aligned with call language and evaluation criteria)
- title_rationale: why this title works (1 sentence)
- reviewer_guidance: exactly what a reviewer expects to find here (3-5 specific points)
- policy_connections: list of policies to reference in this section
- keywords_to_include: list of 3-8 specific keywords from the call
- measures_and_evidence: what quantitative evidence, KPIs or baselines to include
- common_mistakes: what proposers typically get wrong in this section
- word_count_guidance: recommended length for this section

Return ONLY a JSON object:
{{
  "sections": [
    {{
      "id": "section id from template",
      "level": 1-3,
      "original_title": "from template",
      "ai_title": "enhanced title",
      "title_rationale": "...",
      "reviewer_guidance": ["point 1", "point 2", "point 3"],
      "policy_connections": [{{"policy": "...", "how": "...", "where_in_section": "..."}}],
      "keywords_to_include": ["kw1", "kw2"],
      "measures_and_evidence": "specific guidance on numbers, KPIs, baselines",
      "common_mistakes": ["mistake 1", "mistake 2"],
      "word_count_guidance": "e.g. 400-600 words",
      "order": integer
    }}
  ],
  "general_advice": "3-5 paragraphs of strategic advice for writing this proposal",
  "top_5_priorities": ["The 5 most important things this proposal must achieve"]
}}"""

    response = _call_realtime(system, prompt, max_tokens=8000)
    if not response:
        return None
    return _parse_json_response(response)


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
