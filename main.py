from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
import asyncio
import traceback

import httpx

from scoring import run_company_scoring
from bands import build_band_output

app = FastAPI(title="ICxA Maturity Map API")

ZAPIER_CATCH_HOOK_URL = "https://hooks.zapier.com/hooks/catch/4562012/upgk2ly/"

# Simple in-memory job store
# Fine for initial deployment on one process.
# For production across multiple workers/instances, move this to Redis/Postgres.
jobs: Dict[str, Dict[str, Any]] = {}


class ScoreRequest(BaseModel):
    company: str
    website: str
    submission_id: Optional[str] = None
    callback_url: Optional[HttpUrl] = ZAPIER_CATCH_HOOK_URL


@app.get("/")
def home():
    return {"message": "ICxA API is running"}


@app.get("/health")
def health():
    return {"ok": True, "status": "healthy"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/score-company", status_code=202)
async def score_company(payload: ScoreRequest):
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
        "callback_url": str(payload.callback_url),
        "created_at": utc_now(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }

    asyncio.create_task(
        process_scoring_job(
            job_id=job_id,
            company=company,
            website=website,
            submission_id=payload.submission_id,
            callback_url=str(payload.callback_url),
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
    callback_url: str,
):
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at"] = utc_now()

    try:
        # run_company_scoring is assumed to be sync/blocking
        result = await asyncio.to_thread(run_company_scoring, company=company, website=website)

        scores = result["scores"]
        bands = build_band_output(scores)
        insights = result.get("insights", [])
        evidence = result.get("evidence", {})

        email_body = f"""
ICxA Maturity Map Results

Company: {company}
Website: {website}
Submission ID: {submission_id or ""}

Overall
- OAI Score: {scores['oai_score']}
- Confidence Score: {scores['confidence_score']}
- Overall Band: {bands['overall']}

Pillar Scores
- Governance: {scores['governance']} ({bands['governance']})
- System Integration: {scores['system_integration']} ({bands['system_integration']})
- Operational Readiness: {scores['operational_readiness']} ({bands['operational_readiness']})
- Performance Validation: {scores['performance_validation']} ({bands['performance_validation']})
- Outcome Delivery: {scores['outcome_delivery']} ({bands['outcome_delivery']})

Insights
- {insights[0] if len(insights) > 0 else ""}
- {insights[1] if len(insights) > 1 else ""}
- {insights[2] if len(insights) > 2 else ""}

— ICxA Automation
""".strip()

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

            "email_subject": f"ICxA Maturity Map – {company}",
            "email_body": email_body,

            "started_at": jobs[job_id]["started_at"],
            "completed_at": utc_now(),
        }

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["completed_at"] = response_payload["completed_at"]
        jobs[job_id]["result"] = response_payload

        await send_callback(callback_url, response_payload)

    except Exception as e:
        error_payload = {
            "ok": False,
            "job_id": job_id,
            "status": "failed",
            "company": company,
            "website": website,
            "submission_id": submission_id,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "started_at": jobs[job_id]["started_at"],
            "completed_at": utc_now(),
        }

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["completed_at"] = error_payload["completed_at"]
        jobs[job_id]["error"] = error_payload

        try:
            await send_callback(callback_url, error_payload)
        except Exception:
            # Avoid crashing the task if callback delivery fails
            pass


async def send_callback(callback_url: str, payload: Dict[str, Any]) -> None:
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(callback_url, json=payload)
        resp.raise_for_status()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
