from analysis_engine import analyze_company


def run_company_scoring(company: str, website: str) -> dict:
    result = analyze_company(company=company, website=website)

    scores = {
        "governance": float(result.get("governance_final_score", 0)),
        "system_integration": float(result.get("system_integration_final_score", 0)),
        "operational_readiness": float(result.get("operational_readiness_final_score", 0)),
        "performance_validation": float(result.get("performance_validation_final_score", 0)),
        "outcome_delivery": float(result.get("outcome_delivery_final_score", 0)),
        "oai_score": float(result.get("oai_score", 0)),
        "confidence_score": float(result.get("confidence_score", 0)),
    }

    insights = result.get("insights", [])
    evidence = result.get("evidence", {})

    return {
        "scores": scores,
        "insights": insights,
        "evidence": evidence,
    }
