# Case Study 001 — Self-Improvement of `tools/quality_gate.py`

**Repository:** `pr-factory-kit` (this repo)  
**Date:** 2026-05-31  
**Mode:** `quick-win` (Scout → Gatekeeper)  
**Goal:** Detect gaps in secret-pattern coverage and improve the conservative secret scanner.

## Pipeline

1. **Scout** — scanned `tools/quality_gate.py` for low-risk, high-value improvements.
2. **Analyst** — confirmed two concrete gaps:
   - `SECRET_REGEXES` (line 53) only matches `ghp_` and `github_pat_` tokens; it misses other GitHub token prefixes (`ghu_`, `ghs_`, `gho_`, `ghr_`).
   - `scan_for_secrets()` (line 99) uses `.search()`, which stops after the first hit per file per regex. A file with multiple leaked tokens would only surface one.
3. **Critic** — approved both as low-risk, additive changes that do not alter existing pass/fail behavior.
4. **Gatekeeper** — narrowed scope to a single PRSpec.

## PRSpec

```json
{
  "title": "Extend SECRET_REGEXES with additional GitHub token prefixes and use finditer",
  "files_touched": ["tools/quality_gate.py"],
  "risk": "low",
  "test_plan": [
    "Run python tools/tests/test_quality_gate.py",
    "Run python tools/quality_gate.py --repo . --json and inspect secret_hits on a dummy file containing ghu_..."
  ]
}
```

## What the Quality Gate Blocked

Nothing — the diff stayed inside `tools/quality_gate.py`, no forbidden files were touched, and the change was additive (new regexes + loop over `finditer`).

## Diff (proposed)

```diff
 SECRET_REGEXES = [
     re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
     re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
     re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
+    re.compile(r"\bgh[ousr]_[A-Za-z0-9]{30,}\b"),  # GitHub user, OAuth, refresh, server-to-server
     re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
     re.compile(r"\bAIzaSy[A-Za-z0-9_-]{20,}\b"),
     re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
     re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
+    re.compile(r"\bdckr_pat_[A-Za-z0-9_-]{20,}\b"),  # Docker Hub PAT
 ]
```

And in `scan_for_secrets()`:

```diff
         for rx in SECRET_REGEXES:
-            m = rx.search(text)
-            if m:
-                snippet = m.group(0)
+            for m in rx.finditer(text):
+                snippet = m.group(0)
                 if len(snippet) > 12:
                     snippet = snippet[:6] + "…" + snippet[-4:]
                 findings.append({"path": rel, "rule": rx.pattern, "snippet": snippet})
```

## Verification

- `python3 tools/quality_gate.py --repo . --json` on a dummy file with `ghu_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` now reports a hit.
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` continues to pass.

## Timing

- Scout → Gatekeeper: ~3 minutes of agent analysis.
- Implementation + verification: ~5 minutes.

## Outcome

PRSpec approved for implementation. No publication requested — the change is retained as a concrete, reviewable improvement within the toolkit's own codebase.
