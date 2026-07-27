from app.models.finding import ExposureCategory

# Base sensitivity by category (1 = low, 5 = high)
CATEGORY_SENSITIVITY = {
    ExposureCategory.PERSONAL_IDENTIFIER: 2,
    ExposureCategory.CONTACT_DETAIL: 3,
    ExposureCategory.CREDENTIAL: 5,
    ExposureCategory.BEHAVIORAL_PATTERN: 3,
    ExposureCategory.ORGANIZATIONAL_LINK: 4,
}

# Base exploitability by category
CATEGORY_EXPLOITABILITY = {
    ExposureCategory.PERSONAL_IDENTIFIER: 1,
    ExposureCategory.CONTACT_DETAIL: 3,
    ExposureCategory.CREDENTIAL: 5,
    ExposureCategory.BEHAVIORAL_PATTERN: 2,
    ExposureCategory.ORGANIZATIONAL_LINK: 3,
}


def correlation_score(platform_count: int) -> int:
    """More platforms a username appears on = stronger identity correlation."""
    if platform_count >= 20:
        return 5
    elif platform_count >= 10:
        return 4
    elif platform_count >= 5:
        return 3
    elif platform_count >= 2:
        return 2
    return 1


def recency_score() -> int:
    """
    Placeholder: Sherlock doesn't give last-active dates, so a fresh
    scan is treated as fully recent/visible for now.
    """
    return 5


def compute_scores(category: ExposureCategory, platform_count: int) -> dict:
    sensitivity = CATEGORY_SENSITIVITY.get(category, 2)
    exploitability = CATEGORY_EXPLOITABILITY.get(category, 2)
    correlation = correlation_score(platform_count)
    recency = recency_score()

    # Weighted average -> 1-5 scale
    weighted = (
        sensitivity * 0.35
        + correlation * 0.30
        + exploitability * 0.25
        + recency * 0.10
    )

    if weighted >= 4:
        severity = "critical"
    elif weighted >= 3:
        severity = "high"
    elif weighted >= 2:
        severity = "medium"
    else:
        severity = "low"

    return {
        "sensitivity_score": sensitivity,
        "correlation_score": correlation,
        "exploitability_score": exploitability,
        "recency_score": recency,
        "risk_severity": severity,
    }