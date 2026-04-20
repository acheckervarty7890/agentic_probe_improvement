from __future__ import annotations

import argparse
import json

from agentic_probe_improvement.tuberlens_adapter import TuberLensProbeRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract activations and probe scores for candidate prompts."
    )
    parser.add_argument("--probe-path", required=True, help="Path to probe .pkl file")
    parser.add_argument(
        "--prompts",
        nargs="+",
        required=True,
        help="One or more prompt strings to evaluate",
    )
    parser.add_argument("--output", default="outputs/redteam_results.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    runner = TuberLensProbeRunner(args.probe_path)
    activation = runner.extract_activation_summary(args.prompts)
    scores = runner.predict_scores(args.prompts)

    payload = {
        "activation_shape": activation.shape,
        "activation_mean_abs": activation.mean_abs_activation,
        "results": [
            {
                "prompt": prompt,
                "score": score,
            }
            for prompt, score in zip(args.prompts, scores)
        ],
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("=== Probe Evaluation Complete ===")
    print(f"Prompts: {len(args.prompts)}")
    print(f"Activation shape: {activation.shape}")
    print(f"Mean |activation|: {activation.mean_abs_activation:.6f}")
    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
