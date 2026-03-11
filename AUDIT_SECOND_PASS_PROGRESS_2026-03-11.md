# Second Pass Progress

## Verified On Current Tree

Commands run from repo root on 2026-03-11:
- `python3 tools/validate_skills.py`
- `python3 -m unittest tools.tests.test_contracts`
- `python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_default_artifact_dir_is_repo_relative`
- `python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_expand_template_accepts_artifact_dir_placeholder`
- `. .venv/bin/activate && python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_architecture_mode_surfaces_single_candidate_in_top_improvements`
- `. .venv/bin/activate && python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_pipeline_summary_payload_is_validated`
- `. .venv/bin/activate && python3 -m unittest tools.tests.test_run_pipeline.RunPipelineTests.test_default_summary_output_uses_stable_artifact_dir`
- `python3 -m unittest tools.tests.test_contracts.ContractRegistryTests.test_root_docs_are_scanned_for_unknown_placeholders`
- `. .venv/bin/activate && python -m unittest discover -s tools/tests -p 'test_*.py'`
- `python3 -m unittest tools.tests.test_run_pipeline`
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'`
- `rg -n "/Users/Apple/Developer/pr-factory-kit/analysis_report/" skills prompts README.md AGENTS.md tools specs FRAMEWORK_IMPROVEMENTS_2026-03-11.md`
- `rg -n "low-risk|approve|scope minimization|strategic" prompts/agent-critic.md skills/pr-factory-critic/SKILL.md prompts/gatekeeper.md skills/pr-factory-gatekeeper/SKILL.md`
- targeted source checks against `tools/run_pipeline.py`, `tools/contract_registry.py`, `README.md`

Note:
- `jsonschema` is now installed for the current system `python3`, so the exact runner verification commands pass both bare and in `.venv`.

Confirmed done:
- Repository-level skill validation is green on the current checkout.
- Contract registry tests pass on the current checkout.
- Metadata `*_JSON` path-vs-object contract drift is no longer present in scanned PR Factory skills.
- Editable-install packaging metadata is now present via `pyproject.toml` with minimal setuptools config for `tools/pr_factory_lib`.
- Pipeline runs now emit a first-class `run_id` and persist machine-readable lineage for stage payloads and extracted PRSpecs.
- Pipeline mode analysis graphs now load from `config/pipeline_modes.json` with early validation for missing or invalid config.

Confirmed still open:
- Optional packaging follow-up: broader editable-install follow-through and repo packaging cleanup beyond the minimal `pyproject.toml`.

## Done

- Fixed all scanned `metadata.json` `*_JSON` inputs to use `type: "string"`.
- Replaced scanned legacy alias placeholders with canonical names.
- Added `requirements.txt` with `jsonschema>=4.0`.
- Fixed the duplicate `How tested` condition in `tools/quality_gate.py`.
- Added regression coverage for lowercase `how tested`.
- Added a repository smoke test that expects zero contract issues.
- Updated CI and `tools/README.md` to remove stale `pyyaml`, switch examples to `python3`, and document the current Critic `ExecutionResult` format.
- Tightened gatekeeper semantics so PR fan-out now requires both `decision="pr"` and top-level `status="success"`.
- Added regression coverage to block fan-out when `gatekeeper` returns `needs_human` alongside otherwise valid `pr_spec` / `data.pr_specs`.
- Added root `README.md` and `AGENTS.md` to static contract scans, replaced dead `{{CONTEXT}}` in `README.md`, and added regression coverage for unknown placeholders in root docs.
- Replaced hardcoded analysis artifact paths in prompts/skills/docs with portable `{{ARTIFACT_DIR}}` guidance and documented the repo-relative `analysis_report/` default.
- Added runner support for `ARTIFACT_DIR` placeholder expansion with a deterministic repo-relative default.
- Rebalanced Critic/Gatekeeper prompt policy so narrow docs/tests/DX/bugfix work has an explicit fast-approve path and Gatekeeper focuses on post-approval scope shaping.
- Preserved architect-mode `data.candidate` payloads in `top_improvements` and added an architecture-mode regression test.
- Added runtime `PipelineSummary` validation before write and moved the default summary artifact path into the stable repo-owned `analysis_report/` directory.
- Added minimal `pyproject.toml` packaging metadata so `python3 -m pip install -e .` works without restructuring the repo, while keeping `requirements.txt` in place.
- Documented editable-install setup in the root `README.md`.
- Added config-backed pipeline mode loading from `config/pipeline_modes.json`, with early validation for required modes and stage names.
- Added per-run `run_id`, stable run artifact directories, and lineage fields connecting pipeline summaries to persisted analysis payloads, PR specs, and per-PR stage outputs.
- Extended the pipeline summary schema and runner regression coverage for config loading and shared `run_id` lineage.

## Remaining

- Optional packaging follow-up: broader editable-install follow-through and repo packaging cleanup beyond the minimal `pyproject.toml`.

## GitHub Actions

- Checked failed push run `22938078456` on branch `codex/publisher-stage-and-user-prompts`.
- Failure was in `Validate skills and contracts` and matched the audit findings: alias warnings plus 8 metadata type errors.
- Local state after fixes:
  - `python3 tools/validate_skills.py` passes
  - full `tools/tests` passes in a fresh venv after `pip install -r requirements.txt`
