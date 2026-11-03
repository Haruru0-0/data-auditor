from dataauditor.findings import Finding
from dataauditor.score import quality_score


def f(severity, check="missing"):
    return Finding(check, severity, "x", "msg", 1)


def test_clean_file_scores_100():
    assert quality_score([]) == 100


def test_weights_per_severity():
    assert quality_score([f("error")]) == 80
    assert quality_score([f("warning")]) == 93
    assert quality_score([f("info")]) == 99
    assert quality_score([f("error"), f("warning"), f("info")]) == 72


def test_each_severity_has_a_cap():
    assert quality_score([f("error")] * 3) == 40
    assert quality_score([f("error")] * 30) == 40  # errors cost at most 60
    assert quality_score([f("warning")] * 5) == 65
    assert quality_score([f("warning")] * 100) == 65  # warnings cost at most 35
    assert quality_score([f("info")] * 5) == 95
    assert quality_score([f("info")] * 100) == 95  # infos cost at most 5


def test_worst_readable_file_scores_zero_but_not_below():
    assert quality_score([f("error")] * 9 + [f("warning")] * 9 + [f("info")] * 9) == 0


def test_read_error_scores_zero():
    assert quality_score([Finding("read", "error", None, "bad file", 1)]) == 0
