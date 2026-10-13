"""Structured report generator for financial research."""

from typing import Any


def generate_report(
    company_name: str,
    ticker: str,
    findings: list[str],
) -> dict[str, Any]:
    """Generate a report structure from supplied research findings."""

    company = company_name.strip()
    normalized_ticker = ticker.strip().upper()

    if not company:
        raise ValueError("Company name must not be empty.")

    if not normalized_ticker:
        raise ValueError("Ticker must not be empty.")

    if not isinstance(findings, list):
        raise ValueError("Findings must be a list of strings.")

    if not all(isinstance(item, str) for item in findings):
        raise ValueError("Every finding must be a string.")

    cleaned_findings = [item.strip() for item in findings if item.strip()]

    return {
        "title": f"Financial Research Report: {company} ({normalized_ticker})",
        "company_name": company,
        "ticker": normalized_ticker,
        "sections": {
            "summary": "No independently verified summary generated.",
            "findings": cleaned_findings,
            "limitations": [
                "Findings are supplied inputs and have not been independently verified.",
                "Sources and citations must be checked before publication.",
                "This report does not provide investment advice.",
            ],
        },
        "finding_count": len(cleaned_findings),
        "data_source": "user_supplied_findings",
        "verified": False,
    }
