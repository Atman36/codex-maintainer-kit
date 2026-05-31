# Security Policy

## Supported versions

Codex Maintainer Kit is pre-1.0. Security fixes are applied to the default branch and included in the next tagged release.

| Version | Supported |
| --- | --- |
| `main` | Yes |
| `v0.1.x` | Yes |

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub Security Advisories for this repository when available. If advisories are unavailable, contact the maintainer through the GitHub profile linked from the repository owner.

Do not open a public issue for a vulnerability until a fix or mitigation is available.

Please include:

- A short description of the issue.
- Steps to reproduce or a minimal proof of concept.
- Affected files, commands, or maintainer workflows.
- Whether secrets, tokens, repository write access, or generated artifacts may be exposed.

## Project security model

Codex Maintainer Kit is advisory by default. The Publisher stage is optional and must run only after an explicit maintainer request.

Security-sensitive areas include:

- repository publishing, pushing, and pull request creation;
- secret detection and redaction in `tools/quality_gate.py`;
- file-scope enforcement through PRSpec `files_touched`;
- command execution guidance in prompts and skills;
- generated analysis artifacts that may contain repository context.

## Disclosure timeline

The maintainer will aim to acknowledge a valid report within 7 days and provide an expected remediation path when enough information is available.
