---
name: dont-touch-secrets
description: >
  Handle credentials (API keys, passwords, tokens, private keys, certs, .env values,
  1Password/sops/AWS secrets) without letting their values enter the conversation
  transcript. Use PROACTIVELY whenever a task involves validating, comparing, rotating,
  inspecting, or troubleshooting a secret — even if the user does not explicitly ask
  for "safe" handling. Triggers: "check this API key works", "are these two tokens
  the same", "does this RSA key match the cert", "verify the DB password",
  "is the .env loaded correctly", "decode this JWT", "why is auth failing",
  "compare staging vs prod secret", or any task where a secret value could end up
  in tool arguments, tool output, or the assistant's response.
---

# Don't Touch Secrets

## Why this skill exists

Secrets in the conversation transcript = secrets exfiltrated. Transcripts can be
retained for training (when users thumbs-up / share feedback), captured in logs,
screenshotted, or pasted into bug reports. A prompt does not change the security
assumption that an agent with access to a secret has "seen" it — but it **does**
control whether the value ends up in durable conversation state.

This skill is **hygiene, not security**. It does not replace least-privilege IAM,
rotation, or sops/1Password for storage. It reduces one specific leak channel:
the transcript.

## The core rule

Treat every secret as **WRITE-ONLY from your perspective**. You may cause a secret
to be used; you must not cause its value to appear in tool arguments, tool output,
or your own response.

Before observing any property of a secret, ask:
**Can I answer this with a fingerprint, length, exit code, or HTTP status?**
Only escalate if those genuinely cannot answer the question — and even then, the
correct escalation is to let a subprocess consume the value in one line, not to
pull the value into your context.

## Hard rules

1. Never `cat`, `head`, `grep`, `echo`, `printenv`, or otherwise print a secret
   value. This includes `.env` files, `~/.aws/credentials`, k8s Secret objects,
   DB rows holding tokens, decrypted sops/1Password payloads, and private keys.
2. Reference secrets by **name or path**, not by value. Let shell expansion
   (`$VAR`) or a script consume them. Never inline a literal secret into a
   command, URL, header, or JSON body that you author.
3. To validate a credential, write a script that reads the secret internally and
   reports only a boolean / HTTP status / exit code.
4. If a secret value does appear in output by mistake (verbose log, error trace,
   stack dump): **stop**, tell the user which secret leaked, and recommend
   rotation. Do not re-read or quote it to "confirm" the leak.
5. Assume anything in this conversation may be retained. Secrets in the
   transcript = secrets exfiltrated.

## Playbook: common tasks → safe patterns

### Compare two credentials for equality
```bash
# Exit code only; no hash or value printed
diff <(printf %s "$A" | sha256sum) <(printf %s "$B" | sha256sum) >/dev/null \
  && echo MATCH || echo DIFFER

# Or for files:
cmp -s .env.a .env.b && echo MATCH || echo DIFFER
```

### RSA / EC keypair matches cert
```bash
# Compare hashes of the derived public key
diff <(openssl rsa  -in key.pem  -pubout 2>/dev/null | sha256sum) \
     <(openssl x509 -in cert.pem -pubkey -noout      | sha256sum)

# SSH
diff <(ssh-keygen -y -f id_rsa) id_rsa.pub
```

### Validate an API key against an endpoint
```bash
# Agent sees only the HTTP status, never $API_KEY
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $API_KEY" https://api.example.com/me
```
Better: wrap in a script that `exit 0` on 2xx, `exit 1` otherwise, and only
observe the exit code.

### Validate a DB password
```bash
PGPASSWORD="$DB_PASS" psql -h "$HOST" -U "$USER" -c 'select 1' >/dev/null 2>&1
echo "exit=$?"
```
Password flows through env var into the subprocess; never inline in the command
string.

### Check an env var is set / non-empty / right length
```bash
[ -n "$TOKEN" ] && echo set || echo missing
echo "len=${#TOKEN}"                                   # length is safe
printf %s "$TOKEN" | sha256sum | cut -c1-12            # short fingerprint
```

### Identify which environment a key belongs to
Use a short fingerprint (first 8–12 chars of sha256). Not reversible, enough to
distinguish. Store the fingerprint in the 1Password item name or a vault label
so humans can cross-reference without exposing the value.

### JWT inspection
```bash
# Header only — no sensitive claims, no signature
cut -d. -f1 <<<"$JWT" | base64 -d 2>/dev/null | jq .
```
Never decode payload or signature in the transcript. For signature validation,
call a library/CLI that returns valid/invalid only.

### Cert / key properties (expiry, CN, SAN, algorithm)
```bash
openssl x509 -in cert.pem -noout -subject -dates -fingerprint -ext subjectAltName
openssl rsa  -in key.pem  -noout -check            # prints "RSA key ok"
```
`-noout` is the critical flag — omits the PEM body.

### Compare encrypted files (sops / age)
```bash
sha256sum secrets.enc.yaml                          # ciphertext hash is fine
# If plaintext comparison is truly required, consume in one pipeline:
diff <(sops -d a.enc.yaml | sha256sum) <(sops -d b.enc.yaml | sha256sum)
```
Never let `sops -d` output land in tool output or a file.

### Verify `.env` loaded into a container
```bash
# Existence, not value
docker exec "$C" sh -c 'echo "${DB_PASS:+set}${DB_PASS:-missing}"'
docker exec "$C" sh -c 'printenv DB_PASS | wc -c'
```
Never `docker exec ... env` or `docker inspect` on a container — both dump
values.

### Rotate / roll: old vs new validation
1. Fingerprint both (`sha256 | cut -c1-12`) to confirm they differ.
2. Validate new one against the target service (HTTP status / exit code).
3. Revoke old via the provider's API — again, script-driven, exit-code observed.

## When the user asks you to read a secret directly

Push back once, briefly:

> I can verify `<property>` without reading the value — e.g. `<pattern>`. Want
> me to do that instead? If you genuinely need the value printed, run the
> command yourself so it stays out of this transcript.

If they confirm they want the value printed anyway, and it is their own local
secret, comply — but note that the value will be retained in the transcript and
recommend rotation afterward if the conversation is shared or rated.

## Escalation: when none of these patterns fit

If you cannot find a fingerprint / exit-code / status-code formulation:
1. Write a standalone script that reads the secret from env or file.
2. Make the script's only output a structured result (`{"valid": true}`, an
   exit code, a status line).
3. Run the script; observe only the structured result.
4. Delete the script if it was scratch.

The rule is not "never touch secrets." It is "never let their values become
durable conversation state."
