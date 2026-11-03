from dataauditor.findings import Finding

# (points per finding, most points that severity can cost)
_COST = {"error": (20, 60), "warning": (7, 35), "info": (1, 5)}


def quality_score(findings: list[Finding]) -> int:
    """0-100 quality indicator: 100 minus a capped penalty per severity.

    Each error costs 20 (at most 60 in total), each warning 7 (at most 35) and
    each info 1 (at most 5), so one noisy check cannot hide the rest. A rough
    indicator for comparing runs, not a standard. A file that could not be
    read (a `read` error) scores 0.
    """
    if any(f.check == "read" for f in findings):
        return 0
    penalty = 0
    for severity, (each, cap) in _COST.items():
        penalty += min(cap, each * sum(1 for f in findings if f.severity == severity))
    return 100 - penalty
