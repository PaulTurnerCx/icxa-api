from __future__ import annotations

from urllib.parse import urljoin, urlparse
from typing import Any
import re

import requests
from bs4 import BeautifulSoup


PILLAR_WEIGHTS = {
    "governance": 0.25,
    "system_integration": 0.20,
    "operational_readiness": 0.20,
    "performance_validation": 0.20,
    "outcome_delivery": 0.15,
}

PILLARS = list(PILLAR_WEIGHTS.keys())

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 20

PILLAR_PHRASES = {
    "governance": [
        "governance",
        "assurance",
        "risk management",
        "project controls",
        "stage gate",
        "stage-gate",
        "delivery assurance",
        "quality management",
        "framework",
        "standards",
        "capital project governance",
        "program governance",
    ],
    "system_integration": [
        "system integration",
        "systems integration",
        "integrated systems",
        "interface management",
        "cross-functional",
        "multi-discipline",
        "multidiscipline",
        "end-to-end",
        "integrated delivery",
        "systems engineering",
    ],
    "operational_readiness": [
        "operational readiness",
        "readiness",
        "startup",
        "start-up",
        "commissioning",
        "turnover",
        "handover",
        "completions",
        "ready for startup",
        "ready for start-up",
        "asset readiness",
    ],
    "performance_validation": [
        "performance validation",
        "performance testing",
        "validation",
        "verification",
        "acceptance testing",
        "functional testing",
        "reliability testing",
        "proof of performance",
        "performance guarantee",
    ],
    "outcome_delivery": [
        "outcome",
        "project delivery",
        "successful delivery",
        "operational performance",
        "business value",
        "asset performance",
        "value delivery",
        "project outcomes",
        "performance outcomes",
    ],
}

PILLAR_FULL_AT = {
    "governance": 12,
    "system_integration": 10,
    "operational_readiness": 12,
    "performance_validation": 10,
    "outcome_delivery": 10,
}


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, round(value, 2)))


def normalize_url(url: str) -> str:
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except Exception:
        return 0


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def strip_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    return normalize_spaces(text)


def same_domain(a: str, b: str) -> bool:
    try:
        ah = urlparse(a).netloc.lower().replace("www.", "")
        bh = urlparse(b).netloc.lower().replace("www.", "")
        return ah == bh
    except Exception:
        return False


def fetch_page(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        content_type = (r.headers.get("content-type") or "").lower()

        if r.status_code >= 400:
            return {"ok": False, "url": url, "status": r.status_code, "text": ""}

        if "text/html" not in content_type:
            return {"ok": False, "url": url, "status": r.status_code, "text": ""}

        text = strip_html(r.text)
        return {
            "ok": True,
            "url": r.url,
            "status": r.status_code,
            "text": text,
            "html": r.text,
        }
    except Exception:
        return {"ok": False, "url": url, "status": None, "text": ""}


def extract_candidate_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html or "", "lxml")
    links = []

    preferred_tokens = [
        "about",
        "services",
        "solutions",
        "capabilities",
        "projects",
        "markets",
        "industries",
        "expertise",
        "careers",
        "jobs",
        "commissioning",
        "startup",
        "readiness",
        "integration",
        "performance",
        "validation",
    ]

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href:
            continue
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        abs_url = urljoin(base_url, href).split("#")[0].rstrip("/")
        if not same_domain(base_url, abs_url):
            continue

        lower = abs_url.lower()
        if any(token in lower for token in preferred_tokens):
            links.append(abs_url)

    deduped = []
    seen = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            deduped.append(link)

    return deduped[:8]


def gather_site_text(website: str) -> dict:
    website = normalize_url(website)

    homepage = fetch_page(website)
    pages = []

    if homepage["ok"]:
        pages.append(homepage)

        candidate_links = extract_candidate_links(website, homepage.get("html", ""))
        for link in candidate_links:
            page = fetch_page(link)
            if page["ok"]:
                pages.append(page)

    homepage_text = homepage.get("text", "") if homepage["ok"] else ""
    all_text = "\n\n".join(p["text"] for p in pages if p.get("text"))

    page_urls = [p["url"] for p in pages]
    page_urls_lower = [u.lower() for u in page_urls]

    services_pages_found = sum(1 for u in page_urls_lower if any(x in u for x in ["/services", "/solutions", "/capabilities", "/expertise"]))
    projects_pages_found = sum(1 for u in page_urls_lower if "/project" in u)
    about_pages_found = sum(1 for u in page_urls_lower if "/about" in u or "/company" in u)
    careers_pages_found = sum(1 for u in page_urls_lower if any(x in u for x in ["/careers", "/career", "/jobs"]))

    career_text = "\n\n".join(
        p["text"] for p in pages
        if any(x in p["url"].lower() for x in ["/careers", "/career", "/jobs"])
    )

    return {
        "homepage_text": homepage_text,
        "career_text": career_text,
        "all_text": all_text,
        "page_urls": page_urls,
        "homepage_text_len": len(homepage_text),
        "career_text_len": len(career_text),
        "subpages_scraped": max(len(pages) - 1, 0),
        "services_pages_found": services_pages_found,
        "projects_pages_found": projects_pages_found,
        "about_pages_found": about_pages_found,
        "careers_pages_found": careers_pages_found,
        "matched_sources_count": len(pages),
        "source_text_length": len(all_text),
    }


def count_matches(text: str, phrases: list[str]) -> int:
    text = (text or "").lower()
    total = 0
    for phrase in phrases:
        total += len(re.findall(re.escape(phrase.lower()), text))
    return total


def best_snippets(text: str, phrases: list[str], max_snippets: int = 2) -> list[str]:
    text = normalize_spaces(text)
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    ranked = []

    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        hits = sum(1 for p in phrases if p.lower() in s_clean.lower())
        if hits > 0:
            ranked.append((hits, s_clean))

    ranked.sort(key=lambda x: (-x[0], len(x[1])))

    out = []
    seen = set()
    for _, s in ranked:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
        if len(out) >= max_snippets:
            break

    return out


def score_count(count: int, full_at: int) -> float:
    if full_at <= 0:
        return 0.0
    return round(min(count / full_at, 1.0) * 100.0, 2)


def evaluate_evidence(metrics: dict) -> dict:
    homepage_text_len = safe_int(metrics.get("homepage_text_len", 0))
    career_text_len = safe_int(metrics.get("career_text_len", 0))
    subpages_scraped = safe_int(metrics.get("subpages_scraped", 0))
    services_pages_found = safe_int(metrics.get("services_pages_found", 0))
    projects_pages_found = safe_int(metrics.get("projects_pages_found", 0))
    about_pages_found = safe_int(metrics.get("about_pages_found", 0))
    careers_pages_found = safe_int(metrics.get("careers_pages_found", 0))
    matched_sources_count = safe_int(metrics.get("matched_sources_count", 0))
    source_text_length = safe_int(metrics.get("source_text_length", 0))

    sources = set()
    primary_count = 0
    secondary_count = 0
    weak_count = 0

    if homepage_text_len >= 300:
        sources.add("website")
        if homepage_text_len >= 1500:
            primary_count += 1
        else:
            secondary_count += 1

    if subpages_scraped > 0:
        sources.add("subpages")
        if services_pages_found + projects_pages_found + about_pages_found + careers_pages_found >= 2:
            primary_count += 1
        else:
            secondary_count += 1

    if career_text_len >= 100 or careers_pages_found > 0:
        sources.add("careers")
        if career_text_len >= 500:
            primary_count += 1
        else:
            secondary_count += 1

    if primary_count == 0 and secondary_count == 0 and matched_sources_count > 0:
        weak_count = 1

    total_evidence = primary_count + secondary_count + weak_count
    evidence_strength = (primary_count * 1.0) + (secondary_count * 0.6) + (weak_count * 0.2)
    evidence_strength_index = int(round((evidence_strength / max(1, total_evidence)) * 100))
    source_diversity_index = len(sources)

    freshness_index = 35 if matched_sources_count > 0 else 0
    if homepage_text_len > 0:
        freshness_index += 25
    if career_text_len > 0:
        freshness_index += 20
    if subpages_scraped > 0:
        freshness_index += 20
    freshness_index = min(100, freshness_index)

    context_quality_index = 0
    if homepage_text_len >= 500:
        context_quality_index += 25
    if homepage_text_len >= 2000:
        context_quality_index += 20
    if subpages_scraped >= 2:
        context_quality_index += 15
    if services_pages_found > 0:
        context_quality_index += 10
    if projects_pages_found > 0:
        context_quality_index += 10
    if about_pages_found > 0:
        context_quality_index += 5
    if career_text_len >= 100:
        context_quality_index += 5
    if career_text_len >= 500:
        context_quality_index += 5
    context_quality_index = min(100, context_quality_index)

    low_evidence_flag = int((primary_count == 0) and (secondary_count <= 1))
    low_context_flag = int(context_quality_index < 30)
    low_diversity_flag = int(source_diversity_index <= 1)

    return {
        "primary_evidence_count": primary_count,
        "secondary_evidence_count": secondary_count,
        "weak_evidence_count": weak_count,
        "evidence_strength_index": evidence_strength_index,
        "source_diversity_index": source_diversity_index,
        "freshness_index": freshness_index,
        "context_quality_index": context_quality_index,
        "low_evidence_flag": low_evidence_flag,
        "low_context_flag": low_context_flag,
        "low_diversity_flag": low_diversity_flag,
        "matched_sources_count": matched_sources_count,
        "source_text_length": source_text_length,
    }


def normalize_index(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return clamp((value / max_value) * 100.0)


def score_confidence(row: dict) -> dict[str, float | str]:
    evidence_strength = float(row.get("evidence_strength_index", 0))
    source_diversity = float(row.get("source_diversity_index", 0))
    freshness = float(row.get("freshness_index", 0))
    context_quality = float(row.get("context_quality_index", 0))
    source_text_length = float(row.get("source_text_length", 0))
    matched_sources_count = float(row.get("matched_sources_count", 0))

    source_diversity_norm = normalize_index(source_diversity, 3.0)
    matched_sources_norm = normalize_index(matched_sources_count, 6.0)
    text_depth_norm = normalize_index(min(source_text_length, 25000), 25000)

    low_evidence_flag = float(row.get("low_evidence_flag", 0))
    low_context_flag = float(row.get("low_context_flag", 0))
    low_diversity_flag = float(row.get("low_diversity_flag", 0))

    confidence_score = (
        evidence_strength * 0.30
        + source_diversity_norm * 0.15
        + freshness * 0.10
        + context_quality * 0.15
        + text_depth_norm * 0.15
        + matched_sources_norm * 0.15
    )

    if low_evidence_flag:
        confidence_score -= 10
    if low_context_flag:
        confidence_score -= 7
    if low_diversity_flag:
        confidence_score -= 7

    confidence_score = clamp(confidence_score)

    if confidence_score >= 80:
        evidence_class = "High confidence"
    elif confidence_score >= 60:
        evidence_class = "Moderate confidence"
    elif confidence_score >= 40:
        evidence_class = "Limited confidence"
    else:
        evidence_class = "Low confidence"

    return {
        "confidence_score": confidence_score,
        "evidence_class": evidence_class,
        "source_diversity_norm": source_diversity_norm,
        "matched_sources_norm": matched_sources_norm,
        "text_depth_norm": text_depth_norm,
    }


def calibrate_pillar_score(raw_signal: float, confidence_score: float, pillar_name: str) -> float:
    adjusted = raw_signal * (0.85 + (confidence_score / 100.0) * 0.15)

    if pillar_name == "outcome_delivery":
        adjusted *= 1.15

    return clamp(adjusted)


def assign_oai_tier(oai_score: float) -> str:
    if oai_score >= 80:
        return "Tier A"
    if oai_score >= 65:
        return "Tier B"
    if oai_score >= 50:
        return "Tier C"
    if oai_score >= 35:
        return "Tier D"
    return "Tier E"


def assign_maturity_band(oai_score: float) -> str:
    if oai_score >= 80:
        return "Leading"
    if oai_score >= 65:
        return "Advanced"
    if oai_score >= 50:
        return "Established"
    if oai_score >= 35:
        return "Emerging"
    return "Nascent"


def analyze_company(company: str, website: str) -> dict:
    website = normalize_url(website)

    site = gather_site_text(website)
    full_text = site["all_text"]

    evidence = evaluate_evidence(site)
    confidence = score_confidence({**site, **evidence})
    confidence_score = float(confidence["confidence_score"])

    pillar_scores_raw = {}
    pillar_snippets = {}

    for pillar, phrases in PILLAR_PHRASES.items():
        count = count_matches(full_text, phrases)
        raw_signal = score_count(count, PILLAR_FULL_AT[pillar])
        pillar_scores_raw[pillar] = raw_signal
        pillar_snippets[pillar] = best_snippets(full_text, phrases)

    governance_final_score = calibrate_pillar_score(
        pillar_scores_raw["governance"], confidence_score, "governance"
    )
    system_integration_final_score = calibrate_pillar_score(
        pillar_scores_raw["system_integration"], confidence_score, "system_integration"
    )
    operational_readiness_final_score = calibrate_pillar_score(
        pillar_scores_raw["operational_readiness"], confidence_score, "operational_readiness"
    )
    performance_validation_final_score = calibrate_pillar_score(
        pillar_scores_raw["performance_validation"], confidence_score, "performance_validation"
    )
    outcome_delivery_final_score = calibrate_pillar_score(
        pillar_scores_raw["outcome_delivery"], confidence_score, "outcome_delivery"
    )

    final_scores = {
        "governance": governance_final_score,
        "system_integration": system_integration_final_score,
        "operational_readiness": operational_readiness_final_score,
        "performance_validation": performance_validation_final_score,
        "outcome_delivery": outcome_delivery_final_score,
    }

    oai_score = clamp(
        sum(final_scores[pillar] * PILLAR_WEIGHTS[pillar] for pillar in PILLARS)
    )

    strongest = max(final_scores, key=final_scores.get)
    weakest = min(final_scores, key=final_scores.get)

    strongest_label = strongest.replace("_", " ")
    weakest_label = weakest.replace("_", " ")

    insights = [
        f"Strongest visible public evidence is in {strongest_label}.",
        f"Weakest visible public evidence is in {weakest_label}.",
    ]

    if confidence_score < 40:
        insights.append("Confidence is low because the publicly accessible website evidence is limited.")
    elif confidence_score < 60:
        insights.append("Confidence is moderate because public evidence is present but not especially deep.")
    else:
        insights.append("Confidence is relatively strong based on accessible website depth and source diversity.")

    return {
        "governance_final_score": governance_final_score,
        "system_integration_final_score": system_integration_final_score,
        "operational_readiness_final_score": operational_readiness_final_score,
        "performance_validation_final_score": performance_validation_final_score,
        "outcome_delivery_final_score": outcome_delivery_final_score,
        "oai_score": oai_score,
        "oai_tier": assign_oai_tier(oai_score),
        "maturity_band": assign_maturity_band(oai_score),
        "confidence_score": confidence_score,
        "evidence_class": confidence["evidence_class"],
        "insights": insights,
        "evidence": {
            "matched_sources_count": site["matched_sources_count"],
            "source_text_length": site["source_text_length"],
            "page_urls": site["page_urls"],
            "primary_evidence_count": evidence["primary_evidence_count"],
            "secondary_evidence_count": evidence["secondary_evidence_count"],
            "weak_evidence_count": evidence["weak_evidence_count"],
            "evidence_strength_index": evidence["evidence_strength_index"],
            "source_diversity_index": evidence["source_diversity_index"],
            "freshness_index": evidence["freshness_index"],
            "context_quality_index": evidence["context_quality_index"],
            "pillar_signal_scores": pillar_scores_raw,
            "pillar_snippets": pillar_snippets,
        },
    }
