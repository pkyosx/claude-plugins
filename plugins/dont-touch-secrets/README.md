# dont-touch-secrets

A Claude Code plugin that keeps credential values out of the conversation transcript.

## Why

When an AI agent helps you troubleshoot auth, rotate keys, or validate config, it's
tempting to let it `cat .env` or echo a token to "check it's set." The value then
lives in the conversation transcript — which can be retained (via thumbs-up /
feedback sharing), logged, screenshotted, or pasted into a bug report.

This plugin is **hygiene, not security**. It does not replace least-privilege IAM,
rotation, sops, or 1Password. It closes one specific leak channel: the transcript.

## What it does

Installs a skill that triggers whenever a task involves a secret. The skill tells
the agent:

- Treat every secret as **write-only from your perspective**. Reference it by name
  (`$VAR`), never by value.
- Before "looking at" a secret, ask whether a fingerprint, length, exit code, or
  HTTP status can answer the question instead.
- When validation truly requires the value, let a subprocess consume it in one
  pipeline — don't pull it into the transcript.

And provides a playbook of safe patterns for common tasks:

- Compare two credentials for equality (hash + `diff`)
- Check an RSA/EC keypair matches a cert
- Validate an API key against an endpoint (HTTP status only)
- Validate a DB password (exit code only)
- Check a `.env` is loaded into a container (existence, not value)
- JWT header inspection without decoding the payload
- Cert / key property inspection (`openssl -noout`)
- Compare encrypted sops files without decrypting
- Rotation: fingerprint old vs new, validate new, revoke old

## Install

```
/plugin marketplace add pkyosx/claude-plugins
/plugin install dont-touch-secrets@pkyosx-plugins
```

## License

MIT
