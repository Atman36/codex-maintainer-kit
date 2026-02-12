# PR Factory Skills

Локальные Skills для автоматизации создания качественных Pull Requests в open-source проектах.

## Overview

Этот каталог содержит 10 агентов PR Factory, преобразованных в формат Skills для использования в различных AI IDE (Claude Code, Codex, Opencode, Kimi). Каждый skill представляет собой специализированного агента с четко определенной ролью в pipeline создания PR.

## Available Skills

| Skill | Stage | Purpose | Triggers |
|-------|-------|---------|----------|
| [pr-factory-pipeline](pr-factory-pipeline/) | Orchestrator | End-to-end orchestration with strict stage order | Need full workflow "по порядку", one command for full PR Factory run |
| [pr-factory-scout](pr-factory-scout/) | 1. Triage | Quick repository assessment and 3-7 mergeable candidates | Starting analysis of new repo, need repo maturity assessment |
| [pr-factory-analyst](pr-factory-analyst/) | 2. Deep Analysis | Focused deep analysis producing 5 high-quality candidates | Need targeted analysis in specific area (docs/tests/bugfix/perf) |
| [pr-factory-gatekeeper](pr-factory-gatekeeper/) | 3. Selection | Select best candidates and create minimal PRSpecs | Reviewing candidate list, need to decide approve/issue/skip |
| [pr-factory-implementer](pr-factory-implementer/) | 4. Implementation | Safely implement PRSpec with minimal diff | Have approved PRSpec ready for implementation |
| [pr-factory-reviewer](pr-factory-reviewer/) | 5. Review Gate | Maintainer-style post-implementation diff review | Need to catch scope creep/noise before PR writing |
| [pr-factory-pr-writer](pr-factory-pr-writer/) | 6. PR Message | Write excellent, concise PR messages | Implementation complete, need final PR description |
| [pr-factory-publisher](pr-factory-publisher/) | 7. Publish | Fork/push/open PR from an implemented PRSpec | User explicitly asked to publish a PR |
| [pr-factory-critic](pr-factory-critic/) | Gate | Pre-implementation evaluation | Need to evaluate proposed changes before implementation |
| [pr-factory-architect](pr-factory-architect/) | Alternative | Find small architectural improvements | Looking for refactoring opportunities (<200 LOC) |

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     START: New Repository                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  Scout        │  Quick triage + 3-7 candidates
                   │  (Stage 1)    │
                   └───────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
        ┌───────────────┐     ┌──────────────┐
        │  Analyst      │     │  Architect   │  (Optional)
        │  (Stage 2)    │     │  (Alt.)      │  Small refactor
        └───────┬───────┘     └──────┬───────┘
                │                    │
                └──────────┬─────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  Critic       │  Pre-implementation gate
                   │  (Gate)       │  approve/revise/reject
                   └───────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
          approve                 revise/reject
                │                     │
                ▼                     ▼
        ┌───────────────┐       Back to Analyst
        │  Gatekeeper   │       or Stop
        │  (Stage 3)    │
        └───────┬───────┘
                │
                ▼ PRSpec created
        ┌───────────────┐
        │  Implementer  │  Safe implementation
        │  (Stage 4)    │
        └───────┬───────┘
                │
                ▼ Implementation done
        ┌───────────────┐
        │  Reviewer     │  Post-implementation gate
        │  (Stage 5)    │
        └───────┬───────┘
                │
                ▼ Review passed
        ┌───────────────┐
        │  PR Writer    │  Excellent PR message
        │  (Stage 6)    │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │  Publisher    │
        └───────────────┘
```

## Quick Start

### 1. Using in Claude Code

Skills are automatically discovered from this directory. To invoke:

```bash
# Load skill implicitly by task
"Analyze this repo for PR opportunities"  # → triggers scout

# Or explicitly by name
/pr-factory-scout
```

### 2. Using in Other IDEs

Copy the entire `skills/` directory to your IDE's skills location:

- **Codex**: Copy to project root or `~/.codex/skills/`
- **Opencode**: Copy to `~/.opencode/skills/`
- **Kimi**: Copy to project root or `~/.kimi/skills/`

### 3. Manual Workflow (Non-IDE)

Each skill can be used standalone by reading its SKILL.md and following instructions manually.

## Shared Resources

Skills reference shared resources in the repository root:

### Schemas (../../schemas/)

- **execution_result.schema.json** - Standard output format for all agents
- **prspec.schema.json** - PR specification format

All skills output JSON conforming to `ExecutionResult` schema.

### Tools (../../tools/)

- **quality_gate.py** - Validation tool for PRSpec quality
- **run_pipeline.py** - Deterministic stage orchestrator with hard gates and implement retries
- Used by Implementer and PR Writer for verification

## Placeholders

Skills use placeholders that must be filled by orchestrator:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{REPO_ROOT}}` | Local repository path | `/Users/dev/my-repo` |
| `{{REPO_URL}}` | Repository URL | `https://github.com/owner/repo` |
| `{{BASE_BRANCH}}` | Target branch | `main`, `master` |
| `{{HEAD_BRANCH}}` | Working branch | `fix/null-check` |
| `{{CANDIDATES_JSON}}` | JSON from previous stage | (Scout/Analyst output) |
| `{{CRITIC_JSON}}` | Critic decision JSON | (Critic output) |
| `{{PRSPEC_JSON}}` | PRSpec JSON | (Gatekeeper output) |
| `{{IMPLEMENT_RESULT_JSON}}` | Implementation result | (Implementer output) |
| `{{RELATED_FILES}}` | High-signal files for scoped implementation | (Analyst/Scout output) |
| `{{FOCUS}}` | Analysis focus | `docs`, `tests`, `bugfix` |
| `{{MAX_PRS}}` | Maximum PRs to select | `1`, `3` |
| `{{CONSTRAINTS}}` | Additional constraints | (Custom) |
| `{{ALLOWED_COMMANDS}}` | Allowed verification commands | (Custom) |

## Skill Structure

Each skill follows this structure:

```
pr-factory-{name}/
├── SKILL.md               # Main skill definition
│   ├── Frontmatter (YAML) # name, description, triggers
│   ├── Role & Goal        # What this agent does
│   ├── Inputs             # Placeholders needed
│   ├── Process            # Step-by-step workflow
│   ├── Output Format      # JSON schema + example
│   └── Quality Standards  # What makes good output
└── references/            # Detailed guidance
    └── {topic}.md         # Deep-dive on specific topics
```

**Progressive Disclosure:**
1. **Metadata** (name + description) - Always loaded (~100 words)
2. **SKILL.md body** - Loaded when skill triggers (<5k words)
3. **references/** - Loaded as needed (unlimited)

## Usage Patterns

### Pattern 1: Full Pipeline (Automated)

For fully automated PR creation:

1. Start with `pr-factory-pipeline` (mode: `full`)
2. Internal order: Scout → Analyst → Critic → Gatekeeper → Implementer → Reviewer → PR Writer
3. Each stage outputs JSON consumed by next
4. Critic and Reviewer act as quality gates

### Pattern 2: Manual Selection (Interactive)

For manual review at each stage:

1. Scout → (review candidates) → Gatekeeper → (review PRSpec) → Implementer → Reviewer → PR Writer
2. Human approves at each stage

### Pattern 3: Quick Win (Fast Track)

For obvious improvements:

1. Scout → Gatekeeper → Implementer → Reviewer → PR Writer
2. Skip Analyst and Critic for low-risk changes

### Pattern 4: Architectural Focus

For refactoring opportunities:

1. Architect → Critic → Gatekeeper → Implementer → Reviewer → PR Writer
2. Focus on one small architectural improvement

## Quality Gates

### Scout → Analyst/Gatekeeper
- At least 3 candidates found
- Repo score ≥ 5/10
- No blockers

### Analyst/Architect → Critic
- Clear necessity for each candidate
- Minimal scope (<100 LOC)
- Concrete verification plan

### Critic → Gatekeeper
- Decision: `approve` (not `reject` or `revise`)
- Merge probability ≥ 0.5
- No must-fix items

### Gatekeeper → Implementer
- PRSpec complete (all required fields)
- Decision: `pr` (not `issue` or `skip`)
- Test plan defined

### Implementer → Reviewer
- Status: `success` (not `failed` or `needs_human`)
- All tests passed
- No tool state files committed

### Reviewer → PR Writer
- Status: `success` (not `retryable` or `needs_human`)
- No unexpected files outside `pr_spec.files_touched`
- No debug/noise findings left unresolved

## IDE Integration

### Claude Code

Skills are auto-discovered. Use triggers from SKILL.md descriptions:

```
"Analyze this repo for PR opportunities"
"Review these candidates and create PRSpec"
"Implement this PRSpec safely"
```

### Codex / Opencode / Kimi

Reference skills explicitly:

```
Load pr-factory-scout skill and analyze {{REPO_ROOT}}
```

Or copy SKILL.md content directly into prompt.

## Customization

### Adding Custom Constraints

Edit placeholders in SKILL.md or pass via orchestrator:

```json
{
  "constraints": [
    "Do not modify package.json",
    "Only touch src/ directory",
    "Run tests in Docker"
  ]
}
```

### Customizing Focus Areas

For Analyst:

```
{{FOCUS}} = "docs|tests|bugfix|perf|refactor|ci|dx"
```

### Adjusting Risk Budget

For Critic:

```
{{RISK_BUDGET}} = "low|medium|high"
```

## Troubleshooting

### Skill Not Triggering

1. Check description in SKILL.md frontmatter
2. Verify "Use when:" section is clear
3. Try explicit skill name: `/pr-factory-scout`

### Output Not Valid JSON

1. Skills should output JSON only (no markdown)
2. Check schema: `../../schemas/execution_result.schema.json`
3. Validate with: `python -m jsonschema schemas/execution_result.schema.json < output.json`

### Placeholders Not Filled

1. Orchestrator must fill placeholders before invoking skill
2. Check placeholder list in this README
3. Example: Replace `{{REPO_ROOT}}` with actual path

### Tests Failing

1. Check Implementer output: `data.tests.ok`
2. Review test logs: `data.tests.logs_path`
3. Verify commands in PRSpec `test_plan` work locally

## Contributing

To add new skills or improve existing ones:

1. Follow structure in existing skills
2. Use relative paths (`../../schemas/`, `references/`)
3. Keep SKILL.md concise (<500 lines)
4. Add detailed examples to `references/`
5. Include JSON output examples
6. Test with real repositories

## License

MIT - See LICENSE file in repository root.

## Further Reading

- [WORKFLOW.md](WORKFLOW.md) - Detailed workflow and stage descriptions
- [../schemas/](../schemas/) - JSON schema definitions
- [../tools/](../tools/) - Quality gate and validation tools
- Each skill's `references/` directory for deep-dive guidance
