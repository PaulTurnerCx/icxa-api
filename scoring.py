from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def run_company_scoring(company: str, website: str) -> dict:
    website = normalize_url(website)

    # TEMPORARY PLACEHOLDER
    # Replace this section with your real pipeline next
    scores = {
        "governance": 50,
        "system_integration": 30,
        "operational_readiness": 40,
        "performance_validation": 45,
        "outcome_delivery": 60,
        "oai_score": 45,
        "confidence_score": 70,
    }

    insights = [
        f"Scoring run completed for {company}.",
        "This is currently using placeholder scoring logic."
    ]

    return {
        "scores": scores,
        "insights": insights,
    }
