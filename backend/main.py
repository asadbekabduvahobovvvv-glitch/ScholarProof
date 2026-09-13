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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
OPENAI_REASONING = os.getenv("OPENAI_REASONING", "medium")


# IMPORTANT:
# In demo mode we do NOT even create the OpenAI client.
# This makes accidental API spending much harder.
client = None

if not DEMO_MODE:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=OPENAI_API_KEY)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="ScholarProof API",
    version="0.5.0",
    description="AI-powered scholarship and admission verification.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODEL
# =========================================================

class VerifyRequest(BaseModel):
    mode: str
    text: str | None = None
    url: str | None = None
    image_data_url: str | None = None


# =========================================================
# RESPONSE SCHEMA FOR REAL AI MODE
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
                "unknown"
            ]
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
                            "insufficient"
                        ]
                    },
                    "evidence": {
                        "type": "string"
                    },
                    "source_title": {
                        "type": "string"
                    },
                    "source_url": {
                        "type": "string"
                    }
                },
                "required": [
                    "claim",
                    "status",
                    "evidence",
                    "source_title",
                    "source_url"
                ]
            }
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
                            "high"
                        ]
                    },
                    "title": {
                        "type": "string"
                    },
                    "detail": {
                        "type": "string"
                    }
                },
                "required": [
                    "severity",
                    "title",
                    "detail"
                ]
            }
        },
        "next_steps": {
            "type": "array",
            "items": {
                "type": "string"
            }
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
                    }
                },
                "required": [
                    "title",
                    "url",
                    "official"
                ]
            }
        }
    },
    "required": [
        "language",
        "institution",
        "verdict",
        "summary",
        "risk",
        "claims",
        "security_signals",
        "next_steps",
        "sources"
    ]
}


# =========================================================
# DEMO REPORT — COSTS $0
# =========================================================

def get_demo_report(request: VerifyRequest):
    submitted = (
        request.text
        or request.url
        or "Uploaded screenshot"
    )

    return {
        "success": True,
        "demo": True,
        "submitted": submitted,
        "research_date": datetime.now(timezone.utc).isoformat(),

        "report": {
            "language": "English",

            "institution": "KAIST",

            "verdict":
                "Potentially misleading information detected",

            "summary":
                "The submission mixes legitimate scholarship information "
                "with claims that should not be trusted without checking "
                "official admissions sources.",

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
                        "KAIST Office of Admissions",

                    "source_url":
                        "https://admission.kaist.ac.kr/"
                },

                {
                    "claim":
                        "The scholarship covers every possible living cost.",

                    "status": "partial",

                    "evidence":
                        "Scholarship support may include tuition and a "
                        "living stipend, but that does not automatically mean "
                        "every personal expense is fully covered.",

                    "source_title":
                        "KAIST Scholarship Information",

                    "source_url":
                        "https://admission.kaist.ac.kr/"
                },

                {
                    "claim":
                        "Applications must be submitted through Telegram.",

                    "status": "contradicted",

                    "evidence":
                        "Official university applications should use the "
                        "institution's official admissions channels, not an "
                        "unverified Telegram account.",

                    "source_title":
                        "KAIST International Admissions",

                    "source_url":
                        "https://admission.kaist.ac.kr/"
                },

                {
                    "claim":
                        "SAT is mandatory for the current admissions cycle.",

                    "status": "insufficient",

                    "evidence":
                        "A current official admissions guide would need to "
                        "be checked before this claim can be stated as fact.",

                    "source_title":
                        "Current admissions guide required",

                    "source_url":
                        "https://admission.kaist.ac.kr/"
                }
            ],

            "security_signals": [
                {
                    "severity": "high",

                    "title":
                        "Unofficial application channel",

                    "detail":
                        "Submitting identity documents or payments through "
                        "an unofficial messaging account can expose students "
                        "to impersonation or fraud."
                },

                {
                    "severity": "medium",

                    "title":
                        "True and false claims mixed together",

                    "detail":
                        "Using correct scholarship information alongside an "
                        "incorrect application method can make a suspicious "
                        "message appear trustworthy."
                }
            ],

            "next_steps": [
                "Open the university's official admissions website.",
                "Confirm the current admissions cycle and scholarship rules.",
                "Use only official application and payment channels.",
                "Do not send passwords or sensitive documents to unofficial accounts."
            ],

            "sources": [
                {
                    "title":
                        "KAIST Office of Admissions",

                    "url":
                        "https://admission.kaist.ac.kr/",

                    "official": True
                }
            ]
        }
    }


# =========================================================
# HELPERS
# =========================================================

def validate_request(request: VerifyRequest):
    if request.mode not in {"text", "url", "image"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification mode."
        )

    if request.mode == "text":
        if not request.text or len(request.text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Please provide more text to verify."
            )

        if len(request.text) > 15_000:
            raise HTTPException(
                status_code=413,
                detail="Text is too long."
            )

    if request.mode == "url":
        if not request.url:
            raise HTTPException(
                status_code=400,
                detail="Please provide a URL."
            )

        parsed = urlparse(request.url)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(
                status_code=400,
                detail="Please provide a valid http/https URL."
            )

    if request.mode == "image":
        if not request.image_data_url:
            raise HTTPException(
                status_code=400,
                detail="Please upload a screenshot."
            )

        if not request.image_data_url.startswith("data:image/"):
            raise HTTPException(
                status_code=400,
                detail="Invalid image format."
            )

        # Rough safety limit for V1.
        if len(request.image_data_url) > 10_000_000:
            raise HTTPException(
                status_code=413,
                detail="Image is too large. Use an image under about 7 MB."
            )


def build_research_instructions():
    return """
You are ScholarProof, an evidence-first verification system for
international students.

Your job is to verify scholarship, admission, university and
education-related claims using CURRENT WEB RESEARCH.

CORE RULES:

1. Do not answer only from model memory.

2. Research in English when that improves source quality.

3. Return the final explanation in the same language as the
   submitted content whenever that language is identifiable.

4. Break the submission into separate factual claims.

5. Strongly prioritize PRIMARY OFFICIAL SOURCES:
   - official university domains
   - official scholarship pages
   - official admissions offices
   - official government scholarship portals
   - official application guides
   - official policy documents

6. Blogs, Reddit, social media, consultants and scholarship
   aggregator websites are not sufficient evidence when an
   official source should exist.

7. Use only these claim statuses:

   verified
   partial
   contradicted
   insufficient

8. If you cannot confirm something from reliable current
   evidence, use "insufficient". DO NOT GUESS.

9. Pay special attention to:
   - current admission cycle
   - deadlines
   - tuition coverage
   - stipend
   - accommodation
   - application fees
   - IELTS / TOEFL
   - SAT / ACT
   - eligibility
   - nationality rules
   - separate scholarship applications

10. Perform a defensive security review for:
    - domain impersonation
    - unofficial application channels
    - Telegram / WhatsApp payment requests
    - personal bank transfer requests
    - crypto payment requests
    - guaranteed admission
    - guaranteed scholarship
    - credential requests
    - urgency pressure
    - suspicious payment instructions

11. A suspicious message is NOT automatically proven fraud.
    State uncertainty accurately.

12. Never invent URLs.

13. Every source URL included in the report must be a source
    actually used or found during research.

14. Prefer the newest official information if sources conflict.

15. Keep evidence concise but specific.

Your output MUST follow the supplied JSON schema exactly.
"""


def build_text_content(request: VerifyRequest):
    if request.mode == "text":
        return f"""
Verify this submitted text:

--- BEGIN SUBMISSION ---
{request.text}
--- END SUBMISSION ---
"""

    if request.mode == "url":
        return f"""
Verify the scholarship/admission claims on or associated with this URL:

{request.url}

Research the current web.
Determine whether the domain appears official.
Find official primary sources for all important claims.
"""

    return """
Analyze the attached screenshot.

Extract all visible scholarship, university, admissions, deadline,
requirement, payment and application-channel claims from it.

Then research those claims on the current web and verify them
against official sources.
"""


# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def home():
    return {
        "message": "ScholarProof backend is running",
        "version": "0.5.0",
        "demo_mode": DEMO_MODE,
        "model": OPENAI_MODEL if not DEMO_MODE else "disabled"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "demo_mode": DEMO_MODE,
        "api_spending_enabled": not DEMO_MODE
    }


@app.post("/verify")
def verify(request: VerifyRequest):
    validate_request(request)

    # =====================================================
    # SAFE DEVELOPMENT MODE — ZERO OPENAI API CALLS
    # =====================================================

    if DEMO_MODE:
        return get_demo_report(request)

    # =====================================================
    # REAL AI MODE
    # =====================================================

    try:
        prompt = build_text_content(request)

        content = [
            {
                "type": "input_text",
                "text": prompt
            }
        ]

        if request.mode == "image":
            content.append(
                {
                    "type": "input_image",
                    "image_url": request.image_data_url,
                    "detail": "high"
                }
            )

        response = client.responses.create(
            model=OPENAI_MODEL,

            reasoning={
                "effort": OPENAI_REASONING
            },

            tools=[
                {
                    "type": "web_search"
                }
            ],

            instructions=build_research_instructions(),

            input=[
                {
                    "role": "user",
                    "content": content
                }
            ],

            text={
                "format": {
                    "type": "json_schema",
                    "name": "scholarproof_report",
                    "strict": True,
                    "schema": REPORT_SCHEMA
                }
            }
        )

        report = json.loads(response.output_text)

        return {
            "success": True,
            "demo": False,
            "research_date": datetime.now(timezone.utc).isoformat(),
            "report": report
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="AI returned an invalid structured response."
        )

    except Exception as error:
        print("ScholarProof error:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Verification failed. Check the backend terminal."
        )