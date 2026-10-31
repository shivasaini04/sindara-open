# Security

Please report vulnerabilities privately through [GitHub's private vulnerability reporting](https://github.com/shivasaini04/sindara-open/security/advisories/new). Do not post live credentials, exploitable private details or sensitive media in a public issue.

Keep Studio on a trusted local machine. Do not expose a development preview server publicly or render untrusted code without isolation. A composition and production script execute code with your user's permissions.

Only the optional review command reads `.env` and sends user-selected media to Google. Rendering and the offline tools do not require service credentials. Keep `.env`, private assets, output files and spend ledgers ignored. Review media upload permissions and provider terms before using remote review with sensitive material.

Run `npm audit` when updating dependencies. The release guard checks common credential patterns and accidental local files; it is not a complete security audit. If a key was committed, revoke it rather than relying only on deleting the file.
