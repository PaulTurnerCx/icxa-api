import os
import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from scoring import run_company_scoring
from bands import build_band_output

app = FastAPI(title="ICxA Maturity Map API")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read secret from environment variable, not from code
ZAPIER_CATCH_HOOK_URL = os.getenv("ZAPIER_CATCH_HOOK_URL")

# Simple in-memory job store
jobs: Dict[str, Dict[str, Any]] = {}


class ScoreRequest(BaseModel):
    company: str
    website: str
    submission_id: Optional[str] = None


@app.get("/")
def home():
    return {"message": "ICxA API is running"}


@app.get("/health")
def health():
    return {
        "ok": True,
        "status": "healthy",
        "zapier_hook_configured": bool(ZAPIER_CATCH_HOOK_URL),
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/test-hook")
async def test_hook():
    if not ZAPIER_CATCH_HOOK_URL:
        raise HTTPException(
            status_code=500,
            detail="ZAPIER_CATCH_HOOK_URL is not configured on the server.",
        )

    payload = {
        "ok": True,
        "status": "test",
        "email_subject": "ICxA test hook",
        "email_body": "This is a test from the API.",
    }

    try:
        await send_callback(payload)
        return {"ok": True, "message": "Hook sent"}
    except Exception as e:
        logger.exception("Test hook failed")
        raise HTTPException(status_code=500, detail=f"Hook failed: {str(e)}")


@app.post("/score-company", status_code=202)
async def score_company(payload: ScoreRequest):
    if not ZAPIER_CATCH_HOOK_URL:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured: missing ZAPIER_CATCH_HOOK_URL.",
        )

    company = payload.company.strip()
    website = payload.website.strip()

    if not company:
        raise HTTPException(status_code=400, detail="Missing company")
    if not website:
        raise HTTPException(status_code=400, detail="Missing website")

    job_id = str(uuid4())

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "company": company,
        "website": website,
        "submission_id": payload.submission_id,
        "created_at": utc_now(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "callback_sent": None,
        "callback_error": None,
    }

    logger.info("Queued job %s for %s", job_id, company)

    asyncio.create_task(
        process_scoring_job(
            job_id=job_id,
            company=company,
            website=website,
            submission_id=payload.submission_id,
        )
    )

    return {
        "ok": True,
        "accepted": True,
        "job_id": job_id,
        "status": "queued",
        "company": company,
        "website": website,
        "submission_id": payload.submission_id,
        "message": "Scoring job accepted and processing asynchronously.",
        "status_url": f"/jobs/{job_id}",
    }


async def process_scoring_job(
    job_id: str,
    company: str,
    website: str,
    submission_id: Optional[str],
):
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at"] = utc_now()

    logger.info("Starting job %s for %s", job_id, company)

    try:
        result = await asyncio.to_thread(
            run_company_scoring,
            company=company,
            website=website,
        )

        scores = result["scores"]
        bands = build_band_output(scores)
        insights = result.get("insights", [])
        evidence = result.get("evidence", {})

        email_subject = f"ICxA Maturity Map – {company}"
        email_body = f"""
ICxA Maturity Map Results

Status: SUCCESS
Company: {company}
Website: {website}
Submission ID: {submission_id or ""}
Job ID: {job_id}

OAI Score: {scores['oai_score']}
Confidence Score: {scores['confidence_score']}

Pillar Scores
Governance: {scores['governance']}
System Integration: {scores['system_integration']}
Operational Readiness: {scores['operational_readiness']}
Performance Validation: {scores['performance_validation']}
Outcome Delivery: {scores['outcome_delivery']}

Insights
- {insights[0] if len(insights) > 0 else ""}
- {insights[1] if len(insights) > 1 else ""}
- {insights[2] if len(insights) > 2 else ""}

— ICxA Automation
""".strip()

        completed_at = utc_now()

        response_payload = {
            "ok": True,
            "job_id": job_id,
            "status": "completed",
            "company": company,
            "website": website,
            "submission_id": submission_id,
            "scores": scores,
            "bands": bands,
            "insights": insights,
            "evidence": evidence,
            "governance_score": scores["governance"],
            "system_integration_score": scores["system_integration"],
            "operational_readiness_score": scores["operational_readiness"],
            "performance_validation_score": scores["performance_validation"],
            "outcome_delivery_score": scores["outcome_delivery"],
            "oai_score": scores["oai_score"],
            "confidence_score": scores["confidence_score"],
            "governance_band": bands["governance"],
            "system_integration_band": bands["system_integration"],
            "operational_readiness_band": bands["operational_readiness"],
            "performance_validation_band": bands["performance_validation"],
            "outcome_delivery_band": bands["outcome_delivery"],
            "overall_band": bands["overall"],
            "insight_1": insights[0] if len(insights) > 0 else "",
            "insight_2": insights[1] if len(insights) > 1 else "",
            "insight_3": insights[2] if len(insights) > 2 else "",
            "email_subject": email_subject,
            "email_body": email_body,
            "started_at": jobs[job_id]["started_at"],
            "completed_at": completed_at,
        }

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["completed_at"] = completed_at
        jobs[job_id]["result"] = response_payload

        await send_callback(response_payload)
        jobs[job_id]["callback_sent"] = True

        logger.info("Completed job %s for %s", job_id, company)

    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        completed_at = utc_now()

        logger.exception("Job %s failed for %s", job_id, company)

        email_subject = f"ICxA Maturity Map FAILED – {company}"
        email_body = f"""
ICxA Maturity Map Results

Status: FAILED
Company: {company}
Website: {website}
Submission ID: {submission_id or ""}
Job ID: {job_id}

Error
{error_message}

Traceback
{error_traceback}

— ICxA Automation
""".strip()

        error_payload = {
            "ok": False,
            "job_id": job_id,
            "status": "failed",
            "company": company,
            "website": website,
            "submission_id": submission_id,
            "error": error_message,
            "traceback": error_traceback,
            "scores": {},
            "bands": {},
            "insights": [],
            "evidence": {},
            "governance_score": "",
            "system_integration_score": "",
            "operational_readiness_score": "",
            "performance_validation_score": "",
            "outcome_delivery_score": "",
            "oai_score": "",
            "confidence_score": "",
            "governance_band": "",
            "system_integration_band": "",
            "operational_readiness_band": "",
            "performance_validation_band": "",
            "outcome_delivery_band": "",
            "overall_band": "Failed",
            "insight_1": f"Scoring failed for {company}.",
            "insight_2": error_message,
            "insight_3": "Review traceback for technical details.",
            "email_subject": email_subject,
            "email_body": email_body,
            "started_at": jobs[job_id]["started_at"],
            "completed_at": completed_at,
        }

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["completed_at"] = completed_at
        jobs[job_id]["error"] = error_payload

        try:
            if ZAPIER_CATCH_HOOK_URL:
                await send_callback(error_payload)
                jobs[job_id]["callback_sent"] = True
            else:
                jobs[job_id]["callback_sent"] = False
                jobs[job_id]["callback_error"] = "Missing ZAPIER_CATCH_HOOK_URL"
        except Exception as callback_error:
            jobs[job_id]["callback_sent"] = False
            jobs[job_id]["callback_error"] = str(callback_error)
            logger.exception("Failed to send callback for job %s", job_id)


async def send_callback(payload: Dict[str, Any]) -> None:
    if not ZAPIER_CATCH_HOOK_URL:
        raise RuntimeError("ZAPIER_CATCH_HOOK_URL is not configured.")

    timeout = httpx.Timeout(30.0, connect=10.0)

    logger.info(
        "Sending callback | status=%s | company=%s",
        payload.get("status"),
        payload.get("company"),
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(ZAPIER_CATCH_HOOK_URL, json=payload)
        logger.info("Callback response status: %s", resp.status_code)
        logger.info("Callback response text: %s", resp.text[:1000])
        resp.raise_for_status()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
