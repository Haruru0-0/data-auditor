# Decisions

Made by Ahmad:
- Project 4 is a data-quality auditor, built after forecast-tracker.
- First version targets normal-sized data, in a new folder and a new repo.
- Auditor first; cleaning is a possible later addition.
- Mirror the GitHub repo to GitLab the way jalter does (`dev-tools/mirror-to-gitlab.sh`).

Made by Claude (marked as calls in the design doc, open to change):
- Name `data-auditor`, package `dataauditor`.
- Outliers use median and MAD; exit code 1 only on error-level findings.

Process rules carried over from forecast-tracker: commits as Ahmad without co-author or generated-with lines, never push without his explicit yes.

See [[architecture]].
