# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/satyaidk/Action-Graph/security/advisories/new)
("Security" tab → "Report a vulnerability"). Include:

- a description of the issue and its impact;
- steps to reproduce (a minimal transcript or request, with any personal data removed);
- the affected version or commit.

You can expect an acknowledgement within 7 days. Confirmed issues are fixed on the default
branch and noted in [CHANGELOG.md](CHANGELOG.md).

## Security model and known limitations

ActionGraph v0.1 is designed for **local, single-user** use.

| Area | Current behaviour |
|------|-------------------|
| Authentication | None. The server binds to `127.0.0.1`; do not expose it to a network without adding authentication. |
| Secrets | API keys are read from the environment / `.env` (git-ignored) and held as `SecretStr`, so they are never logged. |
| Untrusted input | Transcripts are treated as untrusted: the system prompt instructs the model to ignore embedded instructions, status updates may only reference ids the system supplied, and every item is grounded against the transcript. |
| Web UI | All API-provided text is HTML-escaped before rendering (XSS protection). |
| Uploads | File types are allow-listed and processed in a temporary directory that is deleted afterwards. No size limit is enforced yet. |
| Data | Transcripts and extracted data are stored in a local SQLite file and sent only to the configured LLM provider. Audio is transcribed locally. |

See the [design document](docs/design/DESIGN.md#7-cross-cutting-concerns) for the full threat discussion.
