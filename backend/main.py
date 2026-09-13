import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

DEMO_MODE = os.getenv("SCHOLARPROOF_DEMO", "true").lower() == "true"

DEEP_AUDIT = (
    os.getenv("SCHOLARPROOF_DEEP_AUDIT", "false").lower() == "true"
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna",
)

OPENAI_REASONING = os.getenv(
    "OPENAI_REASONING",
    "medium",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# OpenAI client is NOT created in demo mode.
# This makes accidental spending much harder.
client = None

if not DEMO_MODE:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing."
        )

    client = OpenAI(
        api_key=OPENAI_API_KEY
    )


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="ScholarProof API",
    version="0.7.0",
    description=(
        "Evidence-first scholarship and "
        "admissions verification API."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://scholar-proof.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# INPUT
# =========================================================

class VerifyRequest(BaseModel):
    mode: str

    text: str | None = None
    url: str | None = None
    image_data_url: str | None = None


# =========================================================
# STRUCTURED OUTPUT SCHEMA
# =========================================================

REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,

    "properties": {

        "language": {
            "type": "string"
        },

        "institution": {
            "type": "string"
        },

        "official_domain": {
            "type": "string"
        },

        "verdict": {
            "type": "string"
        },

        "summary": {
            "type": "string"
        },

        "risk": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
                "unknown",
            ],
        },

        "claims": {
            "type": "array",

            "items": {
                "type": "object",
                "additionalProperties": False,

                "properties": {

                    "claim": {
                        "type": "string"
                    },

                    "status": {
                        "type": "string",
                        "enum": [
                            "verified",
                            "partial",
                            "contradicted",
                            "insufficient",
                        ],
                    },

                    "evidence": {
                        "type": "string"
                    },

                    "source_title": {
                        "type": "string"
                    },

                    "source_url": {
                        "type": "string"
                    },
                },

                "required": [
                    "claim",
                    "status",
                    "evidence",
                    "source_title",
                    "source_url",
                ],
            },
        },

        "security_signals": {
            "type": "array",

            "items": {
                "type": "object",
                "additionalProperties": False,

                "properties": {

                    "severity": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                        ],
                    },

                    "title": {
                        "type": "string"
                    },

                    "detail": {
                        "type": "string"
                    },
                },

                "required": [
                    "severity",
                    "title",
                    "detail",
                ],
            },
        },

        "next_steps": {
            "type": "array",
            "items": {
                "type": "string"
            },
        },

        "sources": {
            "type": "array",

            "items": {
                "type": "object",
                "additionalProperties": False,

                "properties": {

                    "title": {
                        "type": "string"
                    },

                    "url": {
                        "type": "string"
                    },

                    "official": {
                        "type": "boolean"
                    },
                },

                "required": [
                    "title",
                    "url",
                    "official",
                ],
            },
        },
    },

    "required": [
        "language",
        "institution",
        "official_domain",
        "verdict",
        "summary",
        "risk",
        "claims",
        "security_signals",
        "next_steps",
        "sources",
    ],
}


# =========================================================
# URL HELPERS
# =========================================================

def hostname_from_url(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""

        host = host.lower()

        if host.startswith("www."):
            host = host[4:]

        return host

    except Exception:
        return ""


def clean_domain(value: str) -> str:
    value = (value or "").strip().lower()

    if not value:
        return ""

    if "://" in value:
        return hostname_from_url(value)

    value = value.split("/")[0]

    if value.startswith("www."):
        value = value[4:]

    return value


def domain_matches(
    url: str,
    official_domain: str,
) -> bool:

    host = hostname_from_url(url)

    official = clean_domain(
        official_domain
    )

    if not host or not official:
        return False

    return (
        host == official
        or host.endswith("." + official)
    )


def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)

        host = parsed.hostname or ""

        host = host.lower()

        if host.startswith("www."):
            host = host[4:]

        path = parsed.path.rstrip("/")

        return urlunparse(
            (
                parsed.scheme.lower() or "https",
                host,
                path,
                "",
                "",
                "",
            )
        )

    except Exception:
        return url


# =========================================================
# OPENAI WEB SOURCE EXTRACTION
# =========================================================

def extract_web_sources(response):
    """
    Gets the URLs actually returned by OpenAI web search.

    These are later used to reject source links
    that were generated in text but were not
    actually returned by web search.
    """

    collected = []

    try:
        raw = response.model_dump()

        for item in raw.get("output", []):

            if item.get("type") != "web_search_call":
                continue

            action = item.get("action") or {}

            sources = action.get(
                "sources"
            ) or []

            for source in sources:

                url = source.get("url")

                if not url:
                    continue

                title = (
                    source.get("title")
                    or hostname_from_url(url)
                    or "Web source"
                )

                collected.append(
                    {
                        "title": title,
                        "url": url,
                    }
                )

    except Exception as error:
        print(
            "Could not extract web sources:",
            repr(error),
        )

    # Remove duplicates
    unique = {}

    for source in collected:

        key = normalize_url(
            source["url"]
        )

        if key not in unique:
            unique[key] = source

    return list(
        unique.values()
    )


# =========================================================
# STRICT SOURCE VALIDATION
# =========================================================

def validate_report_sources(
    report,
    actual_search_sources,
):

    official_domain = clean_domain(
        report.get(
            "official_domain",
            "",
        )
    )

    actual_map = {}

    for source in actual_search_sources:

        normalized = normalize_url(
            source["url"]
        )

        actual_map[
            normalized
        ] = source


    official_sources = []

    all_sources = []

    for source in actual_search_sources:

        is_official = domain_matches(
            source["url"],
            official_domain,
        )

        validated_source = {
            "title": source["title"],
            "url": source["url"],
            "official": is_official,
        }

        all_sources.append(
            validated_source
        )

        if is_official:
            official_sources.append(
                validated_source
            )


    unsupported_claims = 0

    for claim in report.get(
        "claims",
        [],
    ):

        claimed_url = (
            claim.get(
                "source_url",
                "",
            )
            or ""
        )

        normalized = normalize_url(
            claimed_url
        )

        actual_source = actual_map.get(
            normalized
        )


        # Good:
        # exact source URL was actually returned
        # by the web search tool.
        if actual_source:

            claim["source_url"] = (
                actual_source["url"]
            )

            claim["source_title"] = (
                actual_source["title"]
            )

            continue


        # Otherwise do NOT silently trust
        # an AI-generated URL.
        unsupported_claims += 1

        claim["source_url"] = ""

        claim["source_title"] = (
            "Exact evidence link "
            "was not independently confirmed"
        )


        # ScholarProof is intentionally strict:
        # a factual verdict without a verifiable
        # source link is downgraded.
        if claim.get("status") in {
            "verified",
            "partial",
            "contradicted",
        }:

            claim["status"] = (
                "insufficient"
            )

            claim["evidence"] = (
                claim.get(
                    "evidence",
                    ""
                )
                + " ScholarProof could not "
                  "independently match the "
                  "cited page to the URLs "
                  "returned by web research."
            )


    # Replace model-created source list with
    # the source list actually returned by
    # the web search tool.
    report["sources"] = (
        official_sources
        + [
            source
            for source in all_sources
            if not source["official"]
        ]
    )[:12]


    return report, {
        "search_sources_found":
            len(actual_search_sources),

        "official_sources_found":
            len(official_sources),

        "unmatched_claim_sources":
            unsupported_claims,

        "official_domain":
            official_domain,
    }


# =========================================================
# INPUT VALIDATION
# =========================================================

def validate_request(
    request: VerifyRequest,
):

    if request.mode not in {
        "text",
        "url",
        "image",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid verification mode."
            ),
        )


    if request.mode == "text":

        if (
            not request.text
            or len(
                request.text.strip()
            ) < 10
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Please provide "
                    "more information."
                ),
            )


        if len(request.text) > 15000:

            raise HTTPException(
                status_code=413,
                detail="Text is too long.",
            )


    if request.mode == "url":

        if not request.url:

            raise HTTPException(
                status_code=400,
                detail="URL is required.",
            )

        parsed = urlparse(
            request.url
        )

        if (
            parsed.scheme
            not in {
                "http",
                "https",
            }
            or not parsed.netloc
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Enter a valid "
                    "http/https URL."
                ),
            )


    if request.mode == "image":

        image = (
            request.image_data_url
            or ""
        )

        if not image.startswith(
            "data:image/"
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Please upload "
                    "a valid image."
                ),
            )

        if len(image) > 10_000_000:

            raise HTTPException(
                status_code=413,
                detail=(
                    "Image is too large."
                ),
            )


# =========================================================
# PROMPT
# =========================================================

def research_instructions():

    return """
You are ScholarProof.

ScholarProof is an evidence-first verification system
for international students.

Your job is to verify university, scholarship,
admissions, funding, eligibility, deadline and
application claims using CURRENT WEB RESEARCH.

You MUST search the web before reaching factual
conclusions.

RESEARCH PROCESS

1. Detect the user's language.

2. Research primarily in English when this produces
   stronger official evidence.

3. Return the final report in the user's language
   whenever possible.

4. Identify the institution and its official domain.

5. Separate every important factual claim.

6. Prioritize PRIMARY SOURCES:
   - official university websites
   - official admissions offices
   - official scholarship pages
   - official application guides
   - official government scholarship portals
   - official policy documents

7. Blogs, Reddit, social media, consultants,
   scholarship aggregators and reposted information
   are secondary evidence.

8. Never mark a claim VERIFIED merely because many
   unofficial websites repeat it.

9. Check whether information belongs to the CURRENT
   admissions cycle.

10. Check:
    - tuition
    - scholarship amount
    - living stipend
    - accommodation
    - health insurance
    - eligibility
    - nationality restrictions
    - GPA
    - SAT / ACT
    - IELTS / TOEFL
    - application fee
    - application deadline
    - scholarship deadline
    - required documents
    - application method

11. Perform a DEFENSIVE SECURITY REVIEW for:
    - unofficial domains
    - university impersonation
    - Telegram-only application
    - WhatsApp-only application
    - personal payment requests
    - cryptocurrency payment
    - guaranteed admission
    - guaranteed scholarship
    - urgency pressure
    - password requests
    - suspicious document requests
    - domain mismatch

12. Suspicious does NOT automatically mean proven fraud.

13. When evidence is incomplete, use:
    insufficient

14. Never guess.

15. Never invent a URL.

16. For every claim, source_url MUST be a URL that
    you actually found during web research.

17. Prefer the newest official source when two
    sources disagree.

18. Keep explanations concise but specific.

STATUS VALUES

verified
partial
contradicted
insufficient

Your output must follow the supplied JSON schema.
"""


# =========================================================
# USER CONTENT
# =========================================================

def build_input_content(
    request: VerifyRequest,
):

    if request.mode == "text":

        text_prompt = f"""
Verify this submission.

--- USER SUBMISSION ---
{request.text}
--- END SUBMISSION ---

Research every meaningful factual claim.
"""

        return [
            {
                "type": "input_text",
                "text": text_prompt,
            }
        ]


    if request.mode == "url":

        text_prompt = f"""
Verify the scholarship or admissions information
associated with this URL:

{request.url}

Check whether the domain appears to belong to the
institution it claims to represent.

Then find current primary official sources and
compare the claims.
"""

        return [
            {
                "type": "input_text",
                "text": text_prompt,
            }
        ]


    return [
        {
            "type": "input_text",
            "text": """
Analyze the attached screenshot.

Extract visible university, scholarship, funding,
deadline, eligibility, test requirement, payment
and application-method claims.

Then verify those claims using current official
sources on the web.
""",
        },

        {
            "type": "input_image",
            "image_url":
                request.image_data_url,
            "detail": "high",
        },
    ]


# =========================================================
# DEMO REPORT
# =========================================================

def demo_report():

    return {
        "language": "English",

        "institution": "KAIST",

        "official_domain":
            "admission.kaist.ac.kr",

        "verdict":
            "Potentially misleading "
            "information detected",

        "summary":
            "The submission mixes legitimate "
            "scholarship information with claims "
            "that should be checked through "
            "official admissions channels.",

        "risk": "high",

        "claims": [

            {
                "claim":
                    "KAIST offers scholarships "
                    "to international "
                    "undergraduate students.",

                "status": "verified",

                "evidence":
                    "KAIST publishes scholarship "
                    "information for international "
                    "undergraduate applicants.",

                "source_title":
                    "KAIST Scholarship",

                "source_url":
                    "https://admission.kaist.ac.kr/"
                    "intl-undergraduate/support/"
                    "scholarships/kaist/",
            },

            {
                "claim":
                    "Applications must be "
                    "submitted through Telegram.",

                "status":
                    "contradicted",

                "evidence":
                    "Official university "
                    "applications use official "
                    "admissions channels.",

                "source_title":
                    "KAIST Admissions",

                "source_url":
                    "https://admission.kaist.ac.kr/",
            },
        ],

        "security_signals": [

            {
                "severity": "high",

                "title":
                    "Unofficial application channel",

                "detail":
                    "Sensitive documents should "
                    "not be sent to unverified "
                    "messaging accounts.",
            }
        ],

        "next_steps": [
            "Open the institution's official admissions website.",
            "Confirm the current admissions cycle.",
            "Use only official application and payment channels.",
        ],

        "sources": [

            {
                "title":
                    "KAIST Office of Admissions",

                "url":
                    "https://admission.kaist.ac.kr/",

                "official": True,
            }
        ],
    }


# =========================================================
# REAL AI RESEARCH
# =========================================================

def run_research(
    request: VerifyRequest,
):

    response = client.responses.create(

        model=OPENAI_MODEL,

        reasoning={
            "effort":
                OPENAI_REASONING
        },

        instructions=
            research_instructions(),

        tools=[
            {
                "type": "web_search",
                "search_context_size":
                    "medium",
            }
        ],

        # Real ScholarProof verification
        # MUST perform web research.
        tool_choice="required",

        include=[
            "web_search_call.action.sources"
        ],

        input=[
            {
                "role": "user",
                "content":
                    build_input_content(
                        request
                    ),
            }
        ],

        text={
            "format": {
                "type": "json_schema",

                "name":
                    "scholarproof_report",

                "strict": True,

                "schema":
                    REPORT_SCHEMA,
            }
        },
    )


    try:
        report = json.loads(
            response.output_text
        )

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI returned an invalid "
                "structured response."
            ),
        )


    actual_sources = (
        extract_web_sources(
            response
        )
    )


    report, validation = (
        validate_report_sources(
            report,
            actual_sources,
        )
    )


    return (
        report,
        validation,
        response.id,
    )


# =========================================================
# OPTIONAL SECOND PASS
# =========================================================

def run_deep_audit(
    original_response_id,
):

    """
    OFF by default.

    When enabled for final accuracy testing,
    the model reviews the previous research
    and is allowed to search again if needed.

    This costs additional API usage.
    """

    response = client.responses.create(

        model=OPENAI_MODEL,

        previous_response_id=
            original_response_id,

        reasoning={
            "effort": "medium"
        },

        tools=[
            {
                "type": "web_search",
                "search_context_size":
                    "medium",
            }
        ],

        tool_choice="auto",

        include=[
            "web_search_call.action.sources"
        ],

        instructions=
            research_instructions(),

        input="""
Audit the ScholarProof report you just produced.

Re-check weak or uncertain claims.

Look especially for:
- outdated admission cycles
- official-domain mismatches
- scholarship coverage being overstated
- test requirements being overstated
- deadlines that may be old
- unsafe application or payment channels

If the evidence does not justify a verdict,
downgrade the claim to insufficient.

Return the full corrected report.
""",

        text={
            "format": {
                "type": "json_schema",

                "name":
                    "scholarproof_report",

                "strict": True,

                "schema":
                    REPORT_SCHEMA,
            }
        },
    )


    report = json.loads(
        response.output_text
    )

    sources = extract_web_sources(
        response
    )

    report, validation = (
        validate_report_sources(
            report,
            sources,
        )
    )

    return report, validation


# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def home():

    return {
        "message":
            "ScholarProof backend is running",

        "version": "0.7.0",

        "demo_mode":
            DEMO_MODE,

        "deep_audit":
            DEEP_AUDIT,

        "model":
            (
                "disabled"
                if DEMO_MODE
                else OPENAI_MODEL
            ),
    }


@app.get("/health")
def health():

    return {
        "status": "ok",

        "demo_mode":
            DEMO_MODE,

        "api_spending_enabled":
            not DEMO_MODE,

        "deep_audit_enabled":
            (
                DEEP_AUDIT
                and not DEMO_MODE
            ),
    }


@app.post("/verify")
def verify(
    request: VerifyRequest,
):

    validate_request(
        request
    )


    # =====================================================
    # DEMO MODE — $0 OPENAI COST
    # =====================================================

    if DEMO_MODE:

        return {
            "success": True,

            "demo": True,

            "research_date":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "source_validation": {
                "search_sources_found": 1,
                "official_sources_found": 1,
                "unmatched_claim_sources": 0,
                "official_domain":
                    "admission.kaist.ac.kr",
            },

            "report":
                demo_report(),
        }


    # =====================================================
    # REAL MODE
    # =====================================================

    try:

        (
            report,
            validation,
            response_id,
        ) = run_research(
            request
        )


        audit_used = False


        if DEEP_AUDIT:

            (
                report,
                validation,
            ) = run_deep_audit(
                response_id
            )

            audit_used = True


        return {
            "success": True,

            "demo": False,

            "deep_audit_used":
                audit_used,

            "research_date":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "source_validation":
                validation,

            "report":
                report,
        }


    except HTTPException:
        raise


    except Exception as error:

        print(
            "ScholarProof error:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "ScholarProof verification failed. "
                "Check the backend logs."
            ),
        )