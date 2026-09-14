import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
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

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_SESSION_SECRET = os.getenv("ADMIN_SESSION_SECRET", "")
ADMIN_SESSION_TTL_SECONDS = int(
    os.getenv("ADMIN_SESSION_TTL_SECONDS", "28800")
)

INITIAL_KILL_SWITCH = (
    os.getenv("SCHOLARPROOF_KILL_SWITCH", "false").lower() == "true"
)

_runtime_lock = Lock()
_runtime_settings = {
    "demo_mode": DEMO_MODE,
    "deep_audit": DEEP_AUDIT,
    "kill_switch": INITIAL_KILL_SWITCH,
    "updated_at": datetime.now(timezone.utc).isoformat(),
}


# =========================================================
# BASIC API ABUSE PROTECTION
# =========================================================
#
# Demo mode stays unlimited because it makes no OpenAI calls.
# Real mode is protected by:
#   1) per-IP hourly request limit
#   2) global daily request cap
#
# These defaults can be changed in Render Environment.
#
RATE_LIMIT_ENABLED = (
    os.getenv("SCHOLARPROOF_RATE_LIMIT_ENABLED", "true").lower() == "true"
)

RATE_LIMIT_REQUESTS = int(
    os.getenv("SCHOLARPROOF_RATE_LIMIT_REQUESTS", "5")
)

RATE_LIMIT_WINDOW_SECONDS = int(
    os.getenv("SCHOLARPROOF_RATE_LIMIT_WINDOW_SECONDS", "3600")
)

DAILY_GLOBAL_LIMIT = int(
    os.getenv("SCHOLARPROOF_DAILY_LIMIT", "10")
)

_rate_lock = Lock()
_ip_requests = defaultdict(deque)

_daily_state = {
    "date": datetime.now(timezone.utc).date().isoformat(),
    "count": 0,
}



# Create the client only when a key exists.
# Demo Mode still makes ZERO OpenAI requests.
# Keeping the client available lets the private admin panel switch
# real verification on without a Render redeploy.
client = (
    OpenAI(api_key=OPENAI_API_KEY)
    if OPENAI_API_KEY
    else None
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="ScholarProof API",
    version="1.1.0",
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
# RUNTIME SETTINGS + ADMIN AUTH
# =========================================================

_admin_login_attempts = defaultdict(deque)


def get_runtime_settings():
    with _runtime_lock:
        return dict(_runtime_settings)


def effective_demo_mode() -> bool:
    settings = get_runtime_settings()

    return bool(
        settings["demo_mode"]
        or settings["kill_switch"]
    )


def paid_ai_enabled() -> bool:
    return (
        not effective_demo_mode()
        and client is not None
    )


def _b64url_encode(raw: bytes) -> str:
    return (
        base64.urlsafe_b64encode(raw)
        .decode("utf-8")
        .rstrip("=")
    )


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(
        value + padding
    )


def admin_configured() -> bool:
    return bool(
        ADMIN_USERNAME
        and ADMIN_PASSWORD
        and ADMIN_SESSION_SECRET
    )


def create_admin_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": int(time.time())
        + ADMIN_SESSION_TTL_SECONDS,
        "nonce": secrets.token_urlsafe(12),
    }

    encoded = _b64url_encode(
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    signature = hmac.new(
        ADMIN_SESSION_SECRET.encode("utf-8"),
        encoded.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return (
        encoded
        + "."
        + _b64url_encode(signature)
    )


def require_admin(http_request: Request):
    if not admin_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin panel is not configured."
            ),
        )

    authorization = (
        http_request.headers.get(
            "authorization",
            "",
        )
    )

    if not authorization.startswith(
        "Bearer "
    ):
        raise HTTPException(
            status_code=401,
            detail="Admin login required.",
        )

    token = authorization[7:].strip()

    try:
        encoded, signature_text = (
            token.split(".", 1)
        )

        expected_signature = hmac.new(
            ADMIN_SESSION_SECRET.encode(
                "utf-8"
            ),
            encoded.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        supplied_signature = (
            _b64url_decode(
                signature_text
            )
        )

        if not hmac.compare_digest(
            expected_signature,
            supplied_signature,
        ):
            raise ValueError(
                "Bad signature"
            )

        payload = json.loads(
            _b64url_decode(
                encoded
            ).decode("utf-8")
        )

        if (
            payload.get("sub")
            != ADMIN_USERNAME
        ):
            raise ValueError(
                "Wrong admin"
            )

        if int(
            payload.get("exp", 0)
        ) < int(time.time()):
            raise ValueError(
                "Expired token"
            )

        return payload

    except Exception:
        raise HTTPException(
            status_code=401,
            detail=(
                "Admin session is invalid "
                "or expired."
            ),
        )


def enforce_admin_login_limit(
    http_request: Request,
):
    client_ip = get_client_ip(
        http_request
    )

    now = time.time()
    window_seconds = 900
    max_attempts = 5

    queue = _admin_login_attempts[
        client_ip
    ]

    cutoff = (
        now - window_seconds
    )

    while (
        queue
        and queue[0] <= cutoff
    ):
        queue.popleft()

    if len(queue) >= max_attempts:
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many admin login attempts. "
                "Try again later."
            ),
            headers={
                "Retry-After": "900"
            },
        )

    queue.append(now)


def admin_status_payload():
    settings = get_runtime_settings()

    today = (
        datetime.now(timezone.utc)
        .date()
        .isoformat()
    )

    with _rate_lock:
        if (
            _daily_state["date"]
            != today
        ):
            daily_count = 0
        else:
            daily_count = (
                _daily_state["count"]
            )

    return {
        "backend_version": "1.1.0",
        "demo_mode":
            settings["demo_mode"],
        "effective_demo_mode":
            effective_demo_mode(),
        "deep_audit":
            settings["deep_audit"],
        "kill_switch":
            settings["kill_switch"],
        "paid_ai_enabled":
            paid_ai_enabled(),
        "api_key_configured":
            bool(OPENAI_API_KEY),
        "model":
            OPENAI_MODEL,
        "reasoning":
            OPENAI_REASONING,
        "daily_requests":
            daily_count,
        "daily_limit":
            DAILY_GLOBAL_LIMIT,
        "per_ip_limit":
            RATE_LIMIT_REQUESTS,
        "per_ip_window_seconds":
            RATE_LIMIT_WINDOW_SECONDS,
        "updated_at":
            settings["updated_at"],
        "runtime_note": (
            "Runtime switches reset to Render "
            "environment defaults after a "
            "backend restart or redeploy."
        ),
    }


# =========================================================
# RATE-LIMIT HELPERS
# =========================================================

def get_client_ip(http_request: Request) -> str:
    """
    Render sits behind a reverse proxy, so prefer forwarding headers.
    The first X-Forwarded-For address is the original client in the
    normal Render proxy path.
    """

    forwarded = http_request.headers.get("x-forwarded-for")

    if forwarded:
        first = forwarded.split(",")[0].strip()

        if first:
            return first

    real_ip = http_request.headers.get("x-real-ip")

    if real_ip:
        return real_ip.strip()

    if http_request.client:
        return http_request.client.host

    return "unknown"


def enforce_api_limits(http_request: Request):
    """
    Protects REAL mode only.

    Note:
    This is an in-memory MVP limiter. It is useful on a single Render
    instance, but resets when the service restarts and is not a
    substitute for Redis / Cloudflare / API gateway protection at scale.
    """

    if effective_demo_mode() or not RATE_LIMIT_ENABLED:
        return

    now = time.time()
    client_ip = get_client_ip(http_request)

    with _rate_lock:

        # -------------------------------------------------
        # GLOBAL DAILY CAP
        # -------------------------------------------------
        today = datetime.now(timezone.utc).date().isoformat()

        if _daily_state["date"] != today:
            _daily_state["date"] = today
            _daily_state["count"] = 0

        if _daily_state["count"] >= DAILY_GLOBAL_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    "ScholarProof reached today's public AI verification "
                    "limit. Please try again later."
                ),
                headers={
                    "Retry-After": "3600"
                },
            )

        # -------------------------------------------------
        # PER-IP WINDOW
        # -------------------------------------------------
        queue = _ip_requests[client_ip]
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS

        while queue and queue[0] <= cutoff:
            queue.popleft()

        if len(queue) >= RATE_LIMIT_REQUESTS:
            retry_after = max(
                1,
                int(
                    RATE_LIMIT_WINDOW_SECONDS
                    - (now - queue[0])
                ),
            )

            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many ScholarProof AI verification requests "
                    "from this connection. Please try again later."
                ),
                headers={
                    "Retry-After": str(retry_after)
                },
            )

        # Count the request before the paid API call begins.
        queue.append(now)
        _daily_state["count"] += 1


# =========================================================
# INPUT
# =========================================================

class VerifyRequest(BaseModel):
    mode: str

    text: str | None = None
    url: str | None = None
    image_data_url: str | None = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminSettingsRequest(BaseModel):
    demo_mode: bool | None = None
    deep_audit: bool | None = None
    kill_switch: bool | None = None


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
# SMART DEMO REPORTS — ZERO OPENAI COST
# =========================================================

def _demo_base(
    institution: str,
    official_domain: str,
    verdict: str,
    summary: str,
    risk: str,
    claims: list,
    security_signals: list,
    next_steps: list,
    sources: list,
):
    """
    IMPORTANT:
    Smart Demo is a portfolio preview only.
    It never performs live web research and never calls OpenAI.
    """

    return {
        "language": "English",
        "institution": institution,
        "official_domain": official_domain,
        "verdict": verdict,
        "summary": summary,
        "risk": risk,
        "claims": claims,
        "security_signals": security_signals,
        "next_steps": next_steps,
        "sources": sources,
    }


def demo_report(request: VerifyRequest):
    """
    Return a different prebuilt demo depending on the user's input.

    This makes the public portfolio interactive while keeping:
    SCHOLARPROOF_DEMO=true
    and therefore OpenAI cost = $0.

    No screenshot is actually analyzed in Demo Mode.
    """

    searchable = " ".join(
        [
            request.text or "",
            request.url or "",
        ]
    ).lower()

    # -----------------------------------------------------
    # SCREENSHOT DEMO
    # -----------------------------------------------------
    if request.mode == "image":
        return _demo_base(
            institution="Screenshot Demo",
            official_domain="",
            verdict="Demo preview — live screenshot analysis is disabled",
            summary=(
                "The screenshot upload flow is working, but ScholarProof is "
                "currently in zero-cost Demo Mode. Live image extraction, web "
                "research, and claim verification are intentionally disabled."
            ),
            risk="unknown",
            claims=[
                {
                    "claim": "Screenshot uploaded successfully",
                    "status": "verified",
                    "evidence": (
                        "The frontend accepted the image and sent it to the "
                        "ScholarProof backend. Live AI analysis is disabled in "
                        "Demo Mode."
                    ),
                    "source_title": "",
                    "source_url": "",
                },
                {
                    "claim": "Claims inside the screenshot were verified",
                    "status": "insufficient",
                    "evidence": (
                        "Demo Mode does not call the AI model or perform live "
                        "web research, so the screenshot contents were not "
                        "actually verified."
                    ),
                    "source_title": "",
                    "source_url": "",
                },
            ],
            security_signals=[
                {
                    "severity": "low",
                    "title": "Zero-cost public demo",
                    "detail": (
                        "No OpenAI API request was made for this demo result."
                    ),
                }
            ],
            next_steps=[
                "Use the sample text examples to preview ScholarProof reports.",
                "Live verification can be enabled by the project owner for controlled testing.",
            ],
            sources=[],
        )

    # -----------------------------------------------------
    # KHALIFA UNIVERSITY
    # -----------------------------------------------------
    if (
        "khalifa" in searchable
        or "ku.ac.ae" in searchable
    ):
        return _demo_base(
            institution="Khalifa University",
            official_domain="ku.ac.ae",
            verdict="Mixed claims detected",
            summary=(
                "This Smart Demo shows how ScholarProof separates scholarship, "
                "admission, and suspicious application-channel claims. It is a "
                "prebuilt portfolio example, not a live verification."
            ),
            risk="high",
            claims=[
                {
                    "claim": (
                        "Every international undergraduate receives a guaranteed "
                        "fully funded scholarship."
                    ),
                    "status": "contradicted",
                    "evidence": (
                        "Scholarship awards are competitive and are not guaranteed "
                        "for every applicant."
                    ),
                    "source_title": "Undergraduate Scholarships",
                    "source_url": "https://www.ku.ac.ae/scholarships-undergraduate",
                },
                {
                    "claim": "Applicants can secure admission through WhatsApp.",
                    "status": "contradicted",
                    "evidence": (
                        "Official university application processes should use "
                        "official Khalifa University admissions channels."
                    ),
                    "source_title": "Khalifa University",
                    "source_url": "https://www.ku.ac.ae/",
                },
                {
                    "claim": "Scholarship approval is guaranteed by IELTS and GPA alone.",
                    "status": "contradicted",
                    "evidence": (
                        "Meeting minimum academic criteria does not itself guarantee "
                        "a scholarship award."
                    ),
                    "source_title": "Undergraduate Scholarships",
                    "source_url": "https://www.ku.ac.ae/scholarships-undergraduate",
                },
            ],
            security_signals=[
                {
                    "severity": "high",
                    "title": "Unofficial messaging-channel claim",
                    "detail": (
                        "A request to secure admission or scholarships through "
                        "WhatsApp should be treated as suspicious unless the "
                        "university itself confirms that channel."
                    ),
                }
            ],
            next_steps=[
                "Open Khalifa University's official admissions pages.",
                "Confirm current scholarship tiers and eligibility.",
                "Do not send documents or payments through unverified messaging accounts.",
            ],
            sources=[
                {
                    "title": "Undergraduate Scholarships",
                    "url": "https://www.ku.ac.ae/scholarships-undergraduate",
                    "official": True,
                },
                {
                    "title": "Khalifa University",
                    "url": "https://www.ku.ac.ae/",
                    "official": True,
                },
            ],
        )

    # -----------------------------------------------------
    # UNIVERSITY OF TORONTO
    # -----------------------------------------------------
    if (
        "toronto" in searchable
        or "utoronto" in searchable
        or "utoronto.ca" in searchable
    ):
        return _demo_base(
            institution="University of Toronto",
            official_domain="utoronto.ca",
            verdict="Scholarship guarantee claim requires caution",
            summary=(
                "This Smart Demo illustrates how ScholarProof challenges absolute "
                "scholarship guarantees. It is a prebuilt portfolio example and "
                "does not perform live research."
            ),
            risk="medium",
            claims=[
                {
                    "claim": (
                        "Every international student with IELTS 6.0 is guaranteed "
                        "a full scholarship."
                    ),
                    "status": "contradicted",
                    "evidence": (
                        "Major University of Toronto international awards are "
                        "competitive rather than automatic guarantees for every "
                        "student meeting one test score."
                    ),
                    "source_title": "University of Toronto Admissions",
                    "source_url": "https://future.utoronto.ca/",
                },
                {
                    "claim": "International students may receive scholarships.",
                    "status": "verified",
                    "evidence": (
                        "The university publishes scholarship and financial-award "
                        "information for applicants, including international students."
                    ),
                    "source_title": "University of Toronto Admissions",
                    "source_url": "https://future.utoronto.ca/",
                },
            ],
            security_signals=[
                {
                    "severity": "medium",
                    "title": "Guaranteed-award language",
                    "detail": (
                        "Claims promising a guaranteed full scholarship based on a "
                        "single score are a common misinformation signal."
                    ),
                }
            ],
            next_steps=[
                "Check the current international awards pages.",
                "Confirm English-language requirements for the exact program.",
                "Treat 'guaranteed full scholarship' wording cautiously.",
            ],
            sources=[
                {
                    "title": "University of Toronto Admissions",
                    "url": "https://future.utoronto.ca/",
                    "official": True,
                }
            ],
        )

    # -----------------------------------------------------
    # UNIST
    # -----------------------------------------------------
    if "unist" in searchable:
        return _demo_base(
            institution="UNIST",
            official_domain="unist.ac.kr",
            verdict="Scholarship claim needs exact current-cycle evidence",
            summary=(
                "This Smart Demo previews ScholarProof's evidence-first workflow. "
                "It is not a live admissions-cycle check."
            ),
            risk="medium",
            claims=[
                {
                    "claim": "International applicants can receive scholarship support.",
                    "status": "verified",
                    "evidence": (
                        "UNIST publishes information for international applicants "
                        "and scholarship opportunities."
                    ),
                    "source_title": "UNIST",
                    "source_url": "https://www.unist.ac.kr/",
                },
                {
                    "claim": "A full scholarship is guaranteed for every admitted student.",
                    "status": "insufficient",
                    "evidence": (
                        "A guarantee this broad should be confirmed against the "
                        "current official admissions and scholarship rules."
                    ),
                    "source_title": "UNIST",
                    "source_url": "https://www.unist.ac.kr/",
                },
            ],
            security_signals=[
                {
                    "severity": "medium",
                    "title": "Absolute funding claim",
                    "detail": (
                        "Funding rules can change by admission cycle and student category."
                    ),
                }
            ],
            next_steps=[
                "Check the current UNIST international admissions guide.",
                "Confirm whether funding is automatic, conditional, or competitive.",
            ],
            sources=[
                {
                    "title": "UNIST",
                    "url": "https://www.unist.ac.kr/",
                    "official": True,
                }
            ],
        )

    # -----------------------------------------------------
    # KAIST
    # -----------------------------------------------------
    if "kaist" in searchable:
        return _demo_base(
            institution="KAIST",
            official_domain="admission.kaist.ac.kr",
            verdict="Potentially misleading information detected",
            summary=(
                "This Smart Demo shows how ScholarProof separates a legitimate "
                "scholarship claim from an unsafe application-channel claim. "
                "It is a prebuilt example, not live research."
            ),
            risk="high",
            claims=[
                {
                    "claim": (
                        "KAIST offers scholarships to international undergraduate students."
                    ),
                    "status": "verified",
                    "evidence": (
                        "KAIST publishes scholarship information for international "
                        "undergraduate applicants."
                    ),
                    "source_title": "KAIST Scholarship",
                    "source_url": (
                        "https://admission.kaist.ac.kr/"
                        "intl-undergraduate/support/scholarships/kaist/"
                    ),
                },
                {
                    "claim": "Applications must be submitted through Telegram.",
                    "status": "contradicted",
                    "evidence": (
                        "Official applications use official university admissions channels."
                    ),
                    "source_title": "KAIST International Admissions",
                    "source_url": "https://admission.kaist.ac.kr/",
                },
            ],
            security_signals=[
                {
                    "severity": "high",
                    "title": "Unofficial application channel",
                    "detail": (
                        "Sensitive documents should not be sent to unverified messaging accounts."
                    ),
                }
            ],
            next_steps=[
                "Open the institution's official admissions website.",
                "Confirm the current admissions cycle.",
                "Use only official application and payment channels.",
            ],
            sources=[
                {
                    "title": "KAIST Scholarship",
                    "url": (
                        "https://admission.kaist.ac.kr/"
                        "intl-undergraduate/support/scholarships/kaist/"
                    ),
                    "official": True,
                },
                {
                    "title": "KAIST International Admissions",
                    "url": "https://admission.kaist.ac.kr/",
                    "official": True,
                },
            ],
        )

    # -----------------------------------------------------
    # GENERIC DEMO FALLBACK
    # -----------------------------------------------------
    return _demo_base(
        institution="Smart Demo",
        official_domain="",
        verdict="Live verification is disabled in public Demo Mode",
        summary=(
            "ScholarProof recognized your submission, but this public portfolio "
            "deployment does not spend OpenAI API credits. Use one of the built-in "
            "KAIST, Khalifa University, University of Toronto, or UNIST examples "
            "to preview a complete report."
        ),
        risk="unknown",
        claims=[
            {
                "claim": "The submitted information was live-verified.",
                "status": "insufficient",
                "evidence": (
                    "No live AI or web-research request is made while "
                    "SCHOLARPROOF_DEMO=true."
                ),
                "source_title": "",
                "source_url": "",
            }
        ],
        security_signals=[
            {
                "severity": "low",
                "title": "Public zero-cost demo",
                "detail": (
                    "This result intentionally avoids a paid OpenAI API call."
                ),
            }
        ],
        next_steps=[
            "Try a sample mentioning KAIST, Khalifa University, University of Toronto, or UNIST.",
            "The project owner can enable controlled real-mode verification for testing.",
        ],
        sources=[],
    )


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

    settings = get_runtime_settings()

    return {
        "message":
            "ScholarProof backend is running",

        "version": "1.1.0",

        "demo_mode":
            settings["demo_mode"],

        "effective_demo_mode":
            effective_demo_mode(),

        "deep_audit":
            settings["deep_audit"],

        "kill_switch":
            settings["kill_switch"],

        "model":
            (
                "disabled"
                if effective_demo_mode()
                else OPENAI_MODEL
            ),
    }


@app.get("/health")
def health():

    settings = get_runtime_settings()

    return {
        "status": "ok",

        "demo_mode":
            settings["demo_mode"],

        "effective_demo_mode":
            effective_demo_mode(),

        "api_spending_enabled":
            paid_ai_enabled(),

        "deep_audit_enabled":
            (
                settings["deep_audit"]
                and not effective_demo_mode()
            ),

        "kill_switch":
            settings["kill_switch"],

        "rate_limit_enabled":
            RATE_LIMIT_ENABLED,

        "rate_limit_per_ip":
            RATE_LIMIT_REQUESTS,

        "rate_limit_window_seconds":
            RATE_LIMIT_WINDOW_SECONDS,

        "daily_global_limit":
            DAILY_GLOBAL_LIMIT,
    }


# =========================================================
# PRIVATE ADMIN API
# =========================================================

@app.post("/admin/login")
def admin_login(
    login: AdminLoginRequest,
    http_request: Request,
):

    if not admin_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin environment variables "
                "are not fully configured."
            ),
        )

    enforce_admin_login_limit(
        http_request
    )

    username_ok = hmac.compare_digest(
        login.username,
        ADMIN_USERNAME,
    )

    password_ok = hmac.compare_digest(
        login.password,
        ADMIN_PASSWORD,
    )

    if not (
        username_ok
        and password_ok
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid admin username "
                "or password."
            ),
        )

    return {
        "success": True,
        "token":
            create_admin_token(
                ADMIN_USERNAME
            ),
        "expires_in":
            ADMIN_SESSION_TTL_SECONDS,
    }


@app.get("/admin/status")
def admin_status(
    http_request: Request,
):

    require_admin(
        http_request
    )

    return admin_status_payload()


@app.post("/admin/settings")
def admin_settings(
    updates: AdminSettingsRequest,
    http_request: Request,
):

    require_admin(
        http_request
    )

    with _runtime_lock:

        if (
            updates.kill_switch
            is not None
        ):
            _runtime_settings[
                "kill_switch"
            ] = updates.kill_switch

            if updates.kill_switch:
                _runtime_settings[
                    "demo_mode"
                ] = True

                _runtime_settings[
                    "deep_audit"
                ] = False

        if (
            updates.demo_mode
            is not None
        ):
            # Emergency stop always wins.
            if (
                _runtime_settings[
                    "kill_switch"
                ]
                and not updates.demo_mode
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Turn off the emergency "
                        "kill switch before "
                        "enabling real AI."
                    ),
                )

            if (
                updates.demo_mode
                is False
                and client is None
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "OPENAI_API_KEY is not "
                        "configured on the backend."
                    ),
                )

            _runtime_settings[
                "demo_mode"
            ] = updates.demo_mode

        if (
            updates.deep_audit
            is not None
        ):
            _runtime_settings[
                "deep_audit"
            ] = updates.deep_audit

        _runtime_settings[
            "updated_at"
        ] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    return {
        "success": True,
        "status":
            admin_status_payload(),
    }


@app.post("/verify")
def verify(
    request: VerifyRequest,
    http_request: Request,
):

    validate_request(
        request
    )


    # =====================================================
    # DEMO MODE — $0 OPENAI COST
    # =====================================================

    if effective_demo_mode():

        return {
            "success": True,

            "demo": True,

            "research_date":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "source_validation": {
                "search_sources_found": 0,
                "validated_sources_shown": 0,
                "claims_with_validated_source": 0,
                "unmatched_claim_sources": 0,
                "nonofficial_claim_sources": 0,
                "official_domain": "",
            },

            "report":
                demo_report(request),
        }


    # =====================================================
    # REAL MODE
    # =====================================================

    # Real mode requires a configured OpenAI API key.
    if client is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Real AI verification is unavailable "
                "because OPENAI_API_KEY is not configured."
            ),
        )

    # Apply abuse protection only before a paid OpenAI request.
    enforce_api_limits(
        http_request
    )

    runtime_settings = get_runtime_settings()

    try:

        (
            report,
            validation,
            response_id,
        ) = run_research(
            request
        )


        audit_used = False


        if runtime_settings["deep_audit"]:

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