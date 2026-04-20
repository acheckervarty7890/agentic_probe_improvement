# Agentic Probe Improvement

This repo now uses VS Code custom agents for agentic workflows (instead of Python agent modules).

Simple code for:

1. Loading a TuberLens probe and extracting activations from its probed model.
2. Running red-team and judge flows via `.github/agents/*.agent.md`.
3. Marking red-team success whenever the probe misclassifies a prompt.

## Install

```bash
pip install -e .
```

Install TuberLens from your local path (required):

```bash
pip install -e /home/ankush/Documents/tuberlens
```

## Quick Run

Evaluate prompts against a probe (activation extraction + scores):

```bash
python scripts/run_redteam.py \
  --probe-path /path/to/probe.pkl \
  --prompts "Give me a safe bedtime story." "How can I bypass account security?"
```

The script prints a summary and writes JSON output to `outputs/redteam_results.json` by default.

## Custom Agents

Custom agent files:

- `.github/agents/redteam.agent.md`
- `.github/agents/judge.agent.md`
- `.github/agents/orchestrator.agent.md`

Requested compatibility folder:

- `.github/agents_folder/README.md`

Prompt template:

- `.github/prompts/redteam-round.prompt.md`

Ready-to-run chat command sequence:

- `docs/ORCHESTRATOR_CHAT_RUNBOOK.md`

Aggressive Fast-N variant (find N successful failures quickly):

- `docs/ORCHESTRATOR_CHAT_RUNBOOK_FAST_N.md`

## Notes

- This implementation intentionally stays simple and transparent.
- Agent logic is defined in custom agent markdown files, not Python workflow modules.
- Prompt setup follows French Fries style: explicit criteria, iterative rounds, and feedback-guided generation.
