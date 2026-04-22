from __future__ import annotations

import argparse
import json
import random
from typing import Any

from agentic_probe_improvement.tuberlens_adapter import TuberLensProbeRunner


def _load_conversation_inputs(args: argparse.Namespace) -> list[str | list[dict[str, str]]]:
    if args.prompts:
        return args.prompts

    if args.conversations_json:
        raw = json.loads(args.conversations_json)
        if not isinstance(raw, list):
            raise ValueError("--conversations-json must decode to a list")
        return raw

    if args.inputs_jsonl:
        with open(args.inputs_jsonl, "r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]

        if args.sample_size is not None:
            if args.sample_size <= 0:
                raise ValueError("--sample-size must be greater than 0")
            if args.sample_size > len(rows):
                raise ValueError(
                    "--sample-size cannot exceed number of rows in --inputs-jsonl"
                )
            rng = random.Random(args.seed)
            rows = rng.sample(rows, args.sample_size)

        conversations: list[list[dict[str, str]]] = []
        for idx, row in enumerate(rows):
            raw_inputs = row.get("inputs")
            if raw_inputs is None:
                raise ValueError(f"Row {idx} is missing 'inputs'")

            parsed: Any = raw_inputs
            if isinstance(raw_inputs, str):
                parsed = json.loads(raw_inputs)

            if not isinstance(parsed, list):
                raise ValueError(f"Row {idx} 'inputs' must be a list of messages")

            conversations.append(parsed)

        return conversations

    raise ValueError("No inputs provided")


def _conversation_preview(sample: str | list[dict[str, str]]) -> str:
    if isinstance(sample, str):
        return sample

    for message in reversed(sample):
        if message.get("role") == "user":
            return message.get("content", "")

    return sample[-1].get("content", "") if sample else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract activations and probe scores for candidate prompts."
    )
    parser.add_argument("--probe-path", required=True, help="Path to probe .pkl file")

    parser.add_argument(
        "--prompts",
        nargs="+",
        help="One or more plain-text prompt strings (each treated as a single user message)",
    )
    parser.add_argument(
        "--conversations-json",
        help=(
            "JSON list of conversations where each conversation is a list of "
            "{role, content} messages"
        ),
    )
    parser.add_argument(
        "--inputs-jsonl",
        help=(
            "Path to JSONL where each row contains 'inputs' as a JSON string or "
            "list of {role, content} messages"
        ),
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        help="Randomly sample this many rows when --inputs-jsonl is used",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used when --sample-size is set",
    )
    parser.add_argument(
        "--pos-label",
        default="positive",
        help="Label assigned when score >= 0.5",
    )
    parser.add_argument(
        "--neg-label",
        default="negative",
        help="Label assigned when score < 0.5",
    )
    parser.add_argument("--output", default="outputs/redteam_results.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_inputs = _load_conversation_inputs(args)

    runner = TuberLensProbeRunner(args.probe_path)
    scores = runner.predict_scores(model_inputs)

    payload = {
        "results": [
            {
                "input": model_input,
                "score": score,
                "predicted_label": args.pos_label if score >= 0.5 else args.neg_label,
            }
            for model_input, score in zip(model_inputs, scores)
        ],
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("=== Probe Evaluation Complete ===")
    print(f"Inputs: {len(model_inputs)}")
    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
