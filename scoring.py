from pathlib import Path
from urllib.parse import urlparse
import pandas as pd

# IMPORT YOUR EXISTING FUNCTIONS
# (adjust names based on your actual files)
from signals import build_company_signals
from scoring_engine import compute_all_pillars, compute_oai_score


def normalize_url(url: str) -> str:
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def run_company_scoring(company: str, website: str) -> dict:
    website = normalize_url(website)

    try:
        # -----------------------------
        # STEP 1 — BUILD INPUT ROW
        # -----------------------------
        row = {
            "company": company,
            "homepage": website
        }

        df = pd.DataFrame([row])

        # -----------------------------
        # STEP 2 — EXTRACT SIGNALS
        # -----------------------------
        signals = df.apply(
            lambda r: pd.Series(build_company_signals(r)),
            axis=1
        )

        df = pd.concat([df, signals], axis=1)

        # -----------------------------
        # STEP 3 — SCORE PILLARS
        # -----------------------------
        scores = df.apply(
            lambda r: pd.Series(compute_all_pillars(r)),
            axis=1
        )

        df = pd.concat([df, scores], axis=1)

        # -----------------------------
        # STEP 4 — OAI SCORE
        # -----------------------------
        df["oai_score"] = df.apply(compute_oai_score, axis=1)

        # -----------------------------
        # STEP 5 — EXTRACT VALUES
        # -----------------------------
        result = df.iloc[0]

        scores_output = {
            "governance": float(result.get("governance", 0)),
            "system_integration": float(result.get("system_integration", 0)),
            "operational_readiness": float(result.get("operational_readiness", 0)),
            "performance_validation": float(result.get("performance_validation", 0)),
            "outcome_delivery": float(result.get("outcome_delivery", 0)),
            "oai_score": float(result.get("oai_score", 0)),
            "confidence_score": float(result.get("confidence_score", 70))
        }

        # -----------------------------
        # STEP 6 — INSIGHTS
        # -----------------------------
        strongest = max(scores_output, key=scores_output.get)
        weakest = min(scores_output, key=scores_output.get)

        insights = [
            f"Strongest capability observed in {strongest.replace('_', ' ')}.",
            f"Weakest capability observed in {weakest.replace('_', ' ')}."
        ]

        return {
            "scores": scores_output,
            "insights": insights
        }

    except Exception as e:
        return {
            "scores": {
                "governance": 0,
                "system_integration": 0,
                "operational_readiness": 0,
                "performance_validation": 0,
                "outcome_delivery": 0,
                "oai_score": 0,
                "confidence_score": 0
            },
            "insights": [
                "Scoring failed due to processing error.",
                str(e)
            ]
        }
