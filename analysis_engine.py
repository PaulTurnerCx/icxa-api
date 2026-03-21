from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def analyze_company(company: str, website: str) -> dict:
    website = normalize_url(website)

    # ==========================================================
    # REPLACE THIS PLACEHOLDER SECTION WITH YOUR REAL ANALYSIS
    # ==========================================================
    #
    # Your real code should:
    # 1. gather evidence from the website / public sources
    # 2. compute the five pillar scores
    # 3. compute the OAI score
    # 4. compute a confidence score
    # 5. generate 1–3 insights
    #
    # IMPORTANT:
    # Return a plain Python dict with the keys below.
    # ==========================================================

    governance = 50.0
    system_integration = 30.0
    operational_readiness = 40.0
    performance_validation = 45.0
    outcome_delivery = 60.0
    oai_score = round(
        (
            governance
            + system_integration
            + operational_readiness
            + performance_validation
            + outcome_delivery
        )
        / 5,
        1,
    )
    confidence_score = 70.0

    insights = [
        f"Strongest visible capability for {company} appears to be outcome delivery.",
        "System integration appears weaker than the other visible capabilities.",
    ]

    return {
        "governance": governance,
        "system_integration": system_integration,
        "operational_readiness": operational_readiness,
        "performance_validation": performance_validation,
        "outcome_delivery": outcome_delivery,
        "oai_score": oai_score,
        "confidence_score": confidence_score,
        "insights": insights,
    }
