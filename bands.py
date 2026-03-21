def score_to_band(score: float) -> str:
    if score >= 70:
        return "Leading"
    if score >= 55:
        return "Above Benchmark"
    if score >= 40:
        return "On Track"
    if score >= 25:
        return "Slightly Below"
    return "Significantly Below"


def build_band_output(scores: dict) -> dict:
    return {
        "governance": score_to_band(scores["governance"]),
        "system_integration": score_to_band(scores["system_integration"]),
        "operational_readiness": score_to_band(scores["operational_readiness"]),
        "performance_validation": score_to_band(scores["performance_validation"]),
        "outcome_delivery": score_to_band(scores["outcome_delivery"]),
        "overall": score_to_band(scores["oai_score"]),
    }
