import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

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
    version="0.8.0",
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
        host = (urlparse(url).hostname or "").lower()

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


def domain_matches(url: str, official_domain: str) -> bool:
    host = hostname_from_url(url)
    official = clean_domain(official_domain)

    if not host or not official:
        return False

    return host == official or host.endswith("." + official)


def canonical_url_key(url: str) -> str:
    try:
        parsed = urlparse((url or "").strip())

        host = (parsed.hostname or "").lower()

        if host.startswith("www."):
            host = host[4:]

        path = parsed.path or "/"

        if path != "/":
            path = path.rstrip("/")

        return f"{host}{path}".lower()

    except Exception:
        return (url or "").strip().lower()


def valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse((url or "").strip())

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def humanize_source_title(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").strip("/")

        if path:
            last = path.split("/")[-1]
            last = (
                last
                .replace("-", " ")
                .replace("_", " ")
                .strip()
            )

            if last and len(last) > 2:
                return last.title()

        host = hostname_from_url(url)

        if host:
            return host

    except Exception:
        pass

    return "Official source"


def useful_title(title: str, url: str) -> bool:
    title = (title or "").strip()

    if not title:
        return False

    host = hostname_from_url(url)

    normalized = (
        title
        .lower()
        .replace("www.", "")
        .strip()
    )

    if normalized in {
        host,
        f"https://{host}",
        f"http://{host}",
    }:
        return False

    return len(title) >= 4


def choose_title(
    model_title: str,
    search_title: str,
    url: str,
) -> str:

    if useful_title(model_title, url):
        return model_title.strip()

    if useful_title(search_title, url):
        return search_title.strip()

    return humanize_source_title(url)


# =========================================================
# OPENAI WEB SOURCE EXTRACTION
# =========================================================

def extract_web_sources(response):
    """
    Extract URLs actually returned by web search and URL citations.
    These are used to reject invented or unsupported source links.
    """

    raw = response.model_dump()
    collected = []

    for item in raw.get("output", []):
        item_type = item.get("type")

        if item_type == "web_search_call":
            action = item.get("action") or {}
            sources = action.get("sources") or []

            for source in sources:
                url = source.get("url")

                if not valid_http_url(url):
                    continue

                collected.append(
                    {
                        "title": source.get("title") or "",
                        "url": url,
                    }
                )

        if item_type == "message":
            for content in item.get("content") or []:
                for annotation in content.get("annotations") or []:
                    if annotation.get("type") != "url_citation":
                        continue

                    url = annotation.get("url")

                    if not valid_http_url(url):
                        continue

                    collected.append(
                        {
                            "title": annotation.get("title") or "",
                            "url": url,
                        }
                    )

    # Deduplicate by host + path, ignoring query strings/fragments.
    unique = {}

    for source in collected:
        key = canonical_url_key(source["url"])

        if not key:
            continue

        current = unique.get(key)

        if current is None:
            unique[key] = source
            continue

        # Prefer the entry with the more useful page title.
        if (
            not useful_title(
                current.get("title", ""),
                current["url"],
            )
            and useful_title(
                source.get("title", ""),
                source["url"],
            )
        ):
            unique[key] = source

    return list(unique.values())


# =========================================================
# STRICT SOURCE VALIDATION
# =========================================================

def validate_report_sources(
    report,
    actual_search_sources,
):
    """
    Public Sources contains only unique official pages that are
    actually used by validated claim evidence.

    A factual claim is downgraded to 'insufficient' when:
    - its cited URL was not actually returned by web research, or
    - the matched page is not on the institution's official domain.
    """

    official_domain = clean_domain(
        report.get("official_domain", "")
    )

    actual_map = {
        canonical_url_key(source["url"]): source
        for source in actual_search_sources
        if valid_http_url(source.get("url", ""))
    }

    validated_sources = {}

    unmatched_claim_sources = 0
    nonofficial_claim_sources = 0
    claims_with_validated_source = 0

    for claim in report.get("claims", []):
        claimed_url = (
            claim.get("source_url")
            or ""
        ).strip()

        model_title = (
            claim.get("source_title")
            or ""
        ).strip()

        key = canonical_url_key(claimed_url)
        matched = actual_map.get(key)

        # URL was not actually found by web research.
        if not matched:
            unmatched_claim_sources += 1

            claim["source_url"] = ""
            claim["source_title"] = (
                "Source link could not be independently confirmed"
            )

            if claim.get("status") in {
                "verified",
                "partial",
                "contradicted",
            }:
                claim["status"] = "insufficient"

                claim["evidence"] = (
                    (
                        claim.get("evidence", "")
                        or ""
                    ).rstrip()
                    + " ScholarProof could not match the cited page "
                      "to a URL actually returned by web research."
                ).strip()

            continue

        actual_url = matched["url"]

        is_official = domain_matches(
            actual_url,
            official_domain,
        )

        claim["source_url"] = actual_url

        claim["source_title"] = choose_title(
            model_title,
            matched.get("title", ""),
            actual_url,
        )

        # Source exists, but it is not official primary evidence.
        if not is_official:
            nonofficial_claim_sources += 1

            if claim.get("status") in {
                "verified",
                "partial",
                "contradicted",
            }:
                claim["status"] = "insufficient"

                claim["evidence"] = (
                    (
                        claim.get("evidence", "")
                        or ""
                    ).rstrip()
                    + " The matched page is not on the institution's "
                      "identified official domain, so ScholarProof does "
                      "not treat it as decisive primary evidence."
                ).strip()

            continue

        claims_with_validated_source += 1

        source_key = canonical_url_key(actual_url)

        if source_key not in validated_sources:
            validated_sources[source_key] = {
                "title": claim["source_title"],
                "url": actual_url,
                "official": True,
            }

        else:
            current = validated_sources[source_key]

            if (
                not useful_title(
                    current["title"],
                    current["url"],
                )
                and useful_title(
                    claim["source_title"],
                    actual_url,
                )
            ):
                current["title"] = claim["source_title"]

    # IMPORTANT:
    # Do not expose every page returned by web search.
    # Only show official pages actually used by validated claims.
    report["sources"] = list(
        validated_sources.values()
    )[:8]

    return report, {
        "search_sources_found":
            len(actual_search_sources),

        "validated_sources_shown":
            len(report["sources"]),

        "claims_with_validated_source":
            claims_with_validated_source,

        "unmatched_claim_sources":
            unmatched_claim_sources,

        "nonofficial_claim_sources":
            nonofficial_claim_sources,

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

You MUST search the web before reaching factual conclusions.

RESEARCH RULES

1. Detect the user's language.

2. Research primarily in English when this gives
   stronger official evidence.

3. Return the final report in the user's language
   whenever possible.

4. Identify the institution and its PRIMARY official domain.

5. Separate every important factual claim.

6. Prioritize PRIMARY SOURCES:
   - official university pages
   - official admissions pages
   - official scholarship pages
   - official FAQs
   - official current-cycle guides/PDFs
   - official government scholarship portals

7. Blogs, consultants, Reddit, social media and
   scholarship aggregators are not decisive evidence.

8. Never mark a claim VERIFIED merely because many
   unofficial websites repeat it.

9. Check whether information belongs to the CURRENT
   admissions or scholarship cycle.

10. Check relevant details including:
    - tuition
    - scholarship amount
    - stipend
    - accommodation
    - insurance
    - airfare
    - eligibility
    - nationality restrictions
    - GPA
    - SAT / ACT
    - IELTS / TOEFL
    - application fee
    - deadlines
    - documents
    - application method
    - scholarship conditions

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

16. source_url MUST be a page that you actually
    encountered during web research.

17. Prefer STABLE PUBLIC INFORMATION PAGES.

18. Prefer:
    - scholarship pages
    - admissions pages
    - FAQ pages
    - official guides
    - official PDFs

19. Avoid using these as evidence unless absolutely necessary:
    - login pages
    - account dashboards
    - application portals
    - search-result pages

20. Prefer a direct information page over a university homepage.

21. One strong official source may support several claims.

22. Do NOT create many duplicate sources for the same page.

23. source_title must describe the PAGE.

Good:
"Undergraduate Scholarships"
"Undergraduate Admissions FAQ"

Bad:
"ku.ac.ae"

24. Prefer the newest official source when official
    sources disagree.

25. Keep explanations concise and evidence-based.

STATUS VALUES

verified
partial
contradicted
insufficient

Your output must follow the supplied JSON schema exactly.
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
            "Potentially misleading information detected",

        "summary":
            "The submission mixes legitimate scholarship "
            "information with claims that should be checked "
            "through official admissions channels.",

        "risk": "high",

        "claims": [
            {
                "claim":
                    "KAIST offers scholarships to international "
                    "undergraduate students.",

                "status": "verified",

                "evidence":
                    "KAIST publishes scholarship information for "
                    "international undergraduate applicants.",

                "source_title":
                    "KAIST Scholarship",

                "source_url":
                    "https://admission.kaist.ac.kr/"
                    "intl-undergraduate/support/"
                    "scholarships/kaist/",
            },

            {
                "claim":
                    "Applications must be submitted through Telegram.",

                "status": "contradicted",

                "evidence":
                    "Official applications use official university "
                    "admissions channels.",

                "source_title":
                    "KAIST International Admissions",

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
                    "Sensitive documents should not be sent to "
                    "unverified messaging accounts.",
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
                    "KAIST Scholarship",

                "url":
                    "https://admission.kaist.ac.kr/"
                    "intl-undergraduate/support/"
                    "scholarships/kaist/",

                "official": True,
            },

            {
                "title":
                    "KAIST International Admissions",

                "url":
                    "https://admission.kaist.ac.kr/",

                "official": True,
            },
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

        "version": "0.8.0",

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
                "search_sources_found": 2,
                "validated_sources_shown": 2,
                "claims_with_validated_source": 2,
                "unmatched_claim_sources": 0,
                "nonofficial_claim_sources": 0,
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