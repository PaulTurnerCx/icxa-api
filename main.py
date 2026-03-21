from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from scoring import run_company_scoring
from bands import build_band_output

app = FastAPI(title="ICxA Maturity Map API")


class ScoreRequest(BaseModel):
    company: str
    website: str
    submission_id: Optional[str] = None


@app.get("/")
def home():
    return {"message": "ICxA API is running"}


@app.get("/health")
def health():
    return {"ok": True, "status": "healthy"}


@app.post("/score-company")
def score_company(payload: ScoreRequest):
    company = payload.company.strip()
    website = payload.website.strip()

    if not company:
        raise HTTPException(status_code=400, detail="Missing company")
    if not website:
        raise HTTPException(status_code=400, detail="Missing website")

    result = run_company_scoring(company=company, website=website)
    scores = result["scores"]
    bands = build_band_output(scores)
    insights = result.get("insights", [])
    evidence = result.get("evidence", {})

    return {
        "ok": True,
        "company": company,
        "website": website,
        "submission_id": payload.submission_id,
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
    }
