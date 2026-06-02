# Security Policy

## Supported Versions

Only the latest released version of `sentencesplit` is supported with security
fixes. Please upgrade to the most recent release before reporting an issue.

## Reporting a Vulnerability

Please report security vulnerabilities privately through GitHub's private
security advisories:

> https://github.com/yisding/sentencesplit/security/advisories/new

Do not open a public issue for security reports.

Because `sentencesplit` is a rule-based, regex-heavy library, we are especially
interested in reports of denial-of-service via catastrophic backtracking
(ReDoS) or quadratic-time inputs. The project has a history of promptly fixing
such regex performance issues, and we treat them as security-relevant.

When you report, please include a minimal reproducing input and, where
possible, the language profile and segmentation options involved. We will
acknowledge your report, work on a fix, and coordinate disclosure through the
advisory once a fixed release is available.
