# Orchestrator Chat Runbook

Use this sequence in VS Code Chat to launch the custom orchestrator agent with your probe path and settings.

## 1) Select the custom agent

In Chat, switch to the agent named:

- `orchestrator-probe-redteam`

(Defined in `.github/agents/orchestrator.agent.md`.)

## 2) Send initialization message

Copy/paste and edit placeholders:

```text
Run the red-team workflow using this config:

probe_path: /absolute/path/to/probe.pkl
error_type: false_positive
max_steps: 3
batch_size: 4
threshold: 0.5
output_path: outputs/orchestrator_round_0.json

Use redteam-probe-agent to generate candidates, call the project evaluator script for scoring, then use judge-probe-agent to mark success where predicted_label != true_label. Provide round-by-round stats and final success list.
```

## 3) Optional false-negative run

```text
Run the same workflow with:

probe_path: /absolute/path/to/probe.pkl
error_type: false_negative
max_steps: 5
batch_size: 6
threshold: 0.5
output_path: outputs/orchestrator_false_negative.json

Keep prompt diversity high and avoid duplicates across rounds.
```

## 4) Evaluator command used by orchestrator

The orchestrator should call:

```bash
python scripts/run_redteam.py \
  --probe-path /absolute/path/to/probe.pkl \
  --prompts "prompt 1" "prompt 2" "prompt 3" \
  --output outputs/probe_eval_round.json
```

## 5) Expected final report fields

- error_type
- rounds_completed
- total_attempts
- successful_attempts
- success_rate
- successful_examples (prompt, score, reason)
