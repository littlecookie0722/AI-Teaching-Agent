# Security Policy

## Supported Scope

The supported scope is the current default local workflow: DSL validation,
review-state transitions, candidate-answer redaction, local persistence, MCP
stdio tools, and the controlled grading execution path.

This project is not a production cloud-control plane or an automatic publishing
service. Real provider calls and controlled grading execution require explicit
local opt-in.

## Reporting a Vulnerability

Do not include credentials, private learner submissions, or exploit details in
a public issue. When this repository is published on GitHub, use GitHub's
private vulnerability reporting feature if it is enabled by the maintainer.
Otherwise, open a minimal issue requesting a private contact channel without
disclosing the vulnerability details.

Useful reports include the affected component, a sanitized reproduction, the
expected and observed behavior, and the potential impact. The maintainer will
acknowledge a valid report, assess scope, and coordinate a fix before public
disclosure where practical.

## Secret Handling

API keys, access tokens, passwords, private keys, and connection strings with
credentials must remain outside the repository. If a secret is committed,
revoke or rotate it first; removing it from the current working tree alone does
not remove it from Git history.
