
"""Evidence-aware mock fact checker."""

from typing import Any


def check_claim(
    claim: str,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Check whether evidence was supplied for a claim.

    This mock tool does not independently verify the truth of a claim.
    """
    if not isinstance(claim, str) or not claim.strip():
        raise ValueError("Claim must be a non-empty string.")

    if sources is not None and (
        not isinstance(sources, list)
        or not all(isinstance(source, str) for source in sources)
    ):
        raise ValueError("Sources must be a list of strings.")

    evidence = [
        source.strip()
        for source in (sources or [])
        if source.strip()
    ]

    if evidence:
        status = "evidence_provided_not_independently_verified"
        explanation = (
            "Evidence was supplied, but its accuracy and authority "
            "have not been independently verified."
        )
    else:
        status = "insufficient_evidence"
        explanation = "No supporting sources were supplied."

    return {
        "claim": claim.strip(),
        "status": status,
        "evidence": evidence,
        "explanation": explanation,
        "data_source": "mock",
    }
