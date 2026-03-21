from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="ICxA API")


class ScoreRequest(BaseModel):
    company: str
    website: str
    submission_id: Optional[str] = None


@app.get("/")
def home():
    return {"message": "ICxA API is running"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/score-company")
def score_company(payload: ScoreRequest):
    return {
        "ok": True,
        "company": payload.company,
        "website": payload.website,
        "submission_id": payload.submission_id,
        "scores": {
            "governance": 50,
            "system_integration": 30,
            "operational_readiness": 40,
            "performance_validation": 45,
            "outcome_delivery": 60,
            "oai_score": 45,
            "confidence_score": 70
        }
    }
