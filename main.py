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

    return {
        "ok": True,
        "company": company,
        "website": website,
        "submission_id": payload.submission_id,
        "scores": result["scores"],
        "bands": build_band_output(result["scores"]),
        "insights": result["insights"],
        "evidence": result["evidence"],
    }
