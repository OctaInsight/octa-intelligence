"""Octa Intelligence — Configuration."""

APP_NAME    = "Proposal Intelligence"
APP_ICON    = "🧠"
APP_VERSION = "1.0.0"

DARK = {
    "bg":      "#0f1421",
    "bg2":     "#1a2235",
    "bg3":     "#232f45",
    "border":  "rgba(255,255,255,0.09)",
    "text":    "#e2e8f0",
    "muted":   "#8899b0",
    "accent":  "#00BCD4",
    "accent2": "#FF6B35",
    "sidebar": "#1B2A4A",
    "success": "#6fcf97",
    "warning": "#f6cc52",
    "danger":  "#fc8181",
}

# ── Funding programmes with pre-built structures ───────────────────────────────
PROGRAMMES = {
    "Horizon Europe — RIA": {
        "label":       "Horizon Europe — Research & Innovation Action",
        "funder":      "European Commission",
        "max_pages":   70,
        "structure": [
            {"id":"1",   "level":1, "title":"Excellence"},
            {"id":"1.1", "level":2, "title":"Objectives and Ambition"},
            {"id":"1.2", "level":2, "title":"Methodology"},
            {"id":"1.3", "level":2, "title":"Originality and Innovative Aspects"},
            {"id":"2",   "level":1, "title":"Impact"},
            {"id":"2.1", "level":2, "title":"Expected Outcomes and Impacts"},
            {"id":"2.2", "level":2, "title":"Measures to Maximise Impact"},
            {"id":"2.2.1","level":3,"title":"Dissemination, Exploitation and Communication"},
            {"id":"2.2.2","level":3,"title":"Management of Intellectual Property"},
            {"id":"2.3", "level":2, "title":"Summary and Scale of Contribution"},
            {"id":"3",   "level":1, "title":"Implementation"},
            {"id":"3.1", "level":2, "title":"Work Plan and Work Packages"},
            {"id":"3.2", "level":2, "title":"Management Structure and Procedures"},
            {"id":"3.3", "level":2, "title":"Consortium as a Whole"},
            {"id":"3.4", "level":2, "title":"Resources and Cost Overview"},
        ],
        "evaluation_criteria": {
            "Excellence": {"weight": 33, "sub": ["Objectives","Methodology","Innovation"]},
            "Impact":     {"weight": 33, "sub": ["Expected outcomes","Measures to maximise"]},
            "Implementation": {"weight": 33, "sub": ["Work plan","Management","Consortium"]},
        }
    },
    "Horizon Europe — IA": {
        "label":   "Horizon Europe — Innovation Action",
        "funder":  "European Commission",
        "max_pages": 70,
        "structure": [
            {"id":"1",   "level":1, "title":"Excellence"},
            {"id":"1.1", "level":2, "title":"Objectives and Ambition"},
            {"id":"1.2", "level":2, "title":"Methodology"},
            {"id":"1.3", "level":2, "title":"Originality and Innovative Aspects"},
            {"id":"2",   "level":1, "title":"Impact"},
            {"id":"2.1", "level":2, "title":"Expected Outcomes and Impacts"},
            {"id":"2.2", "level":2, "title":"Measures to Maximise Impact"},
            {"id":"3",   "level":1, "title":"Implementation"},
            {"id":"3.1", "level":2, "title":"Work Plan and Work Packages"},
            {"id":"3.2", "level":2, "title":"Management Structure and Procedures"},
            {"id":"3.3", "level":2, "title":"Consortium as a Whole"},
            {"id":"3.4", "level":2, "title":"Resources and Cost Overview"},
        ],
        "evaluation_criteria": {
            "Excellence": {"weight": 33}, "Impact": {"weight": 33}, "Implementation": {"weight": 33}
        }
    },
    "Horizon Europe — CSA": {
        "label":   "Horizon Europe — Coordination & Support Action",
        "funder":  "European Commission",
        "max_pages": 45,
        "structure": [
            {"id":"1",   "level":1, "title":"Excellence"},
            {"id":"1.1", "level":2, "title":"Objectives and Ambition"},
            {"id":"1.2", "level":2, "title":"Methodology and Activities"},
            {"id":"2",   "level":1, "title":"Impact"},
            {"id":"2.1", "level":2, "title":"Expected Outcomes and Impacts"},
            {"id":"2.2", "level":2, "title":"Measures to Maximise Impact"},
            {"id":"3",   "level":1, "title":"Implementation"},
            {"id":"3.1", "level":2, "title":"Work Plan"},
            {"id":"3.2", "level":2, "title":"Management"},
            {"id":"3.3", "level":2, "title":"Consortium"},
        ],
        "evaluation_criteria": {
            "Excellence": {"weight": 33}, "Impact": {"weight": 33}, "Implementation": {"weight": 33}
        }
    },
    "Erasmus+ KA2": {
        "label":   "Erasmus+ — Cooperation Partnerships (KA2)",
        "funder":  "European Commission / National Agencies",
        "max_pages": 40,
        "structure": [
            {"id":"1",   "level":1, "title":"Relevance of the Project"},
            {"id":"1.1", "level":2, "title":"Objectives and Needs"},
            {"id":"1.2", "level":2, "title":"Target Groups and Final Beneficiaries"},
            {"id":"2",   "level":1, "title":"Quality of Project Design"},
            {"id":"2.1", "level":2, "title":"Methodology and Work Plan"},
            {"id":"2.2", "level":2, "title":"Intellectual Outputs and Tangible Deliverables"},
            {"id":"2.3", "level":2, "title":"Quality Assurance and Monitoring"},
            {"id":"3",   "level":1, "title":"Quality of the Project Team"},
            {"id":"3.1", "level":2, "title":"Consortium Composition and Profile"},
            {"id":"3.2", "level":2, "title":"Cooperation and Communication Arrangements"},
            {"id":"4",   "level":1, "title":"Impact"},
            {"id":"4.1", "level":2, "title":"Expected Impact on Participants"},
            {"id":"4.2", "level":2, "title":"Dissemination and Exploitation"},
            {"id":"4.3", "level":2, "title":"Long-term Sustainability"},
        ],
        "evaluation_criteria": {
            "Relevance":   {"weight": 30},
            "Design":      {"weight": 20},
            "Team":        {"weight": 20},
            "Impact":      {"weight": 30},
        }
    },
    "LIFE": {
        "label":   "LIFE Programme",
        "funder":  "European Commission",
        "max_pages": 60,
        "structure": [
            {"id":"1",  "level":1, "title":"Context and Problem Definition"},
            {"id":"1.1","level":2, "title":"Environmental / Climate Problem"},
            {"id":"1.2","level":2, "title":"Baseline Situation"},
            {"id":"2",  "level":1, "title":"Objectives and Expected Results"},
            {"id":"2.1","level":2, "title":"Project Objectives"},
            {"id":"2.2","level":2, "title":"Expected Results and Indicators"},
            {"id":"3",  "level":1, "title":"Technical Description"},
            {"id":"3.1","level":2, "title":"Methodology and Actions"},
            {"id":"3.2","level":2, "title":"Work Plan"},
            {"id":"4",  "level":1, "title":"Project Team and Partners"},
            {"id":"5",  "level":1, "title":"Replicability and Transferability"},
            {"id":"6",  "level":1, "title":"Long-term Sustainability"},
        ],
        "evaluation_criteria": {
            "Technical": {"weight": 40}, "Team": {"weight": 20},
            "Impact":    {"weight": 25}, "Finance": {"weight": 15},
        }
    },
    "Digital Europe": {
        "label":   "Digital Europe Programme",
        "funder":  "European Commission",
        "max_pages": 50,
        "structure": [
            {"id":"1",   "level":1, "title":"Excellence and Innovation"},
            {"id":"1.1", "level":2, "title":"Objectives and Innovation"},
            {"id":"1.2", "level":2, "title":"Technical Approach"},
            {"id":"2",   "level":1, "title":"Impact"},
            {"id":"2.1", "level":2, "title":"Expected Outcomes"},
            {"id":"2.2", "level":2, "title":"Deployment and Uptake Strategy"},
            {"id":"3",   "level":1, "title":"Implementation"},
            {"id":"3.1", "level":2, "title":"Work Plan"},
            {"id":"3.2", "level":2, "title":"Team and Resources"},
        ],
        "evaluation_criteria": {
            "Excellence": {"weight": 35}, "Impact": {"weight": 35}, "Implementation": {"weight": 30}
        }
    },
    "Custom": {
        "label":   "Custom Structure (user-defined)",
        "funder":  "",
        "max_pages": 0,
        "structure": [],
        "evaluation_criteria": {}
    }
}

PROGRAMME_NAMES = list(PROGRAMMES.keys())

# ── Policy document categories ─────────────────────────────────────────────────
POLICY_CATEGORIES = [
    "Green Deal & Sustainability",
    "Digital & AI",
    "Research & Innovation",
    "Education & Skills",
    "Health",
    "Social & Inclusion",
    "Regional Development & Cohesion",
    "International Cooperation",
    "Security & Defence",
    "Space",
    "Energy",
    "Transport & Mobility",
    "Food & Agriculture",
    "Culture & Creative Industries",
    "Other",
]

POLICY_TIERS = {
    "core":          "⭐ Core (applies to all proposals)",
    "programme":     "📋 Programme-level",
    "call_specific": "📄 Call-specific",
}

# ── Claude model settings ──────────────────────────────────────────────────────
CLAUDE_MODEL_REALTIME = "claude-sonnet-4-6"
CLAUDE_MODEL_BATCH    = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS     = 8000

# Text extraction limits
MAX_TEXT_CHARS        = 500_000   # ~125K tokens — store full text below this
CHUNK_OVERLAP         = 200       # chars overlap when chunking

# ── Google Drive settings ──────────────────────────────────────────────────────
DRIVE_ROOT_FOLDER_NAME = "Octa Intelligence"
DRIVE_POLICY_SUBFOLDER = "Policy Library"
DRIVE_TIER_FOLDERS     = {
    "core":          "Core",
    "programme":     "Programme",
    "call_specific": "Call-Specific",
}
