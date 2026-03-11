# Spec 13: Rebalance Critic approvals and reduce Gatekeeper overlap

Источник:
- [Audit Report.md](/Users/Apple/Developer/pr-factory-kit/Audit%20Report.md)

## Why This Spec Exists

The audit notes that Critic is not broken, but it is biased toward false negatives. Small, low-risk, reviewer-friendly changes can still get pushed into unnecessary `revise/reject`, while Gatekeeper text sometimes replays strategic filtering instead of focusing on scope minimization after approval.

This is a prompt-policy adjustment and should be isolated from runtime bugfixes.

## Goal

- Give Critic an explicit fast path to approve narrow, low-risk, high-signal work.
- Make Gatekeeper focus on shaping an executable PRSpec after Critic approval, instead of reopening the same strategic debate.

## Scope

Touch only:
- `prompts/agent-critic.md`
- `skills/pr-factory-critic/SKILL.md`
- `prompts/gatekeeper.md`
- `skills/pr-factory-gatekeeper/SKILL.md`

## Smallest Safe Change

- Add explicit approve-fast-path guidance for:
  - tiny docs fixes
  - test-only additions
  - narrow DX/CI fixes
  - small bugfixes with clear verification
- Keep hard rejects for broad refactors, migrations, new deps, auth/security changes without evidence, and noisy diffs.
- Add a short instruction that Gatekeeper should shape scope after Critic approval instead of replaying broad product strategy review.
- Include a few short positive and negative examples.

## Acceptance Criteria

- Critic text clearly distinguishes fast-approve low-risk work from high-risk rejects.
- Gatekeeper text clearly emphasizes scope shaping over repeated strategic filtering.
- Contract validation still passes after prompt edits.

## Verification

Run exactly:

```bash
python3 tools/validate_skills.py
rg -n "low-risk|approve|scope minimization|strategic" prompts/agent-critic.md skills/pr-factory-critic/SKILL.md prompts/gatekeeper.md skills/pr-factory-gatekeeper/SKILL.md
```

Manual review:
- Run 5 canned cases: docs typo fix, test-only coverage, tiny bugfix, broad refactor, new dependency.
- Confirm the first three lean `approve`, while the last two still lean `revise/reject`.

## Reviewer Concerns To Preempt

- Risk of making Critic too soft: keep hard reject boundaries unchanged.
- Risk of duplicated policy: keep Gatekeeper focused on execution shaping.

## Out Of Scope

- Automated eval harness
- Runner gate semantics
- Stage mapping registry

## Suggested Commit Message

```text
tune(critic): approve narrow low-risk work and reduce gate overlap
```
