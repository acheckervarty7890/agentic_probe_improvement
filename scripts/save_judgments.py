from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json_argument(raw_json: str | None, json_path: str | None, *, flag_name: str) -> Any:
    if raw_json:
        return json.loads(raw_json)

    if json_path:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise ValueError(f"Either {flag_name}-json or {flag_name}-path must be provided")


def _canonicalize_attempt(value: Any) -> str:
    if isinstance(value, str):
        return value

    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _judgment_key(judgment: dict[str, Any]) -> str | None:
    for field in ("input", "prompt", "conversation"):
        if field in judgment:
            return _canonicalize_attempt(judgment[field])
    return None


def _result_key(result: dict[str, Any]) -> str | None:
    for field in ("input", "prompt", "conversation"):
        if field in result:
            return _canonicalize_attempt(result[field])
    return None


def _merge_results(
    results_payload: dict[str, Any], judgments_payload: dict[str, Any]
) -> dict[str, Any]:
    results = results_payload.get("results")
    judgments = judgments_payload.get("judgments")

    if not isinstance(results, list):
        raise ValueError("Results payload must contain a list under 'results'")
    if not isinstance(judgments, list):
        raise ValueError("Judgments payload must contain a list under 'judgments'")

    keyed_judgments: dict[str, dict[str, Any]] = {}
    for judgment in judgments:
        if not isinstance(judgment, dict):
            raise ValueError("Each judgment must be an object")
        key = _judgment_key(judgment)
        if key is not None and key not in keyed_judgments:
            keyed_judgments[key] = judgment

    merged_results: list[dict[str, Any]] = []
    matched_count = 0
    used_index_fallback = False

    if len(results) == len(judgments):
        indexed_judgments = judgments
    else:
        indexed_judgments = []

    for idx, result in enumerate(results):
        if not isinstance(result, dict):
            raise ValueError("Each result must be an object")

        merged_result = dict(result)
        result_key = _result_key(result)
        judgment = keyed_judgments.get(result_key) if result_key is not None else None

        if judgment is None and indexed_judgments:
            candidate = indexed_judgments[idx]
            if isinstance(candidate, dict):
                judgment = candidate
                used_index_fallback = True

        if judgment is not None:
            matched_count += 1
            merged_result["judgment"] = {
                "true_label": judgment.get("true_label"),
                "predicted_label": judgment.get(
                    "predicted_label", merged_result.get("predicted_label")
                ),
                "success": judgment.get("success"),
                "reason": judgment.get("reason"),
            }

        merged_results.append(merged_result)

    successful_attempts = sum(
        1
        for result in merged_results
        if isinstance(result.get("judgment"), dict)
        and result["judgment"].get("success") is True
    )
    judged_attempts = sum(1 for result in merged_results if "judgment" in result)

    return {
        "results": merged_results,
        "summary": {
            "total_attempts": len(merged_results),
            "judged_attempts": judged_attempts,
            "matched_judgments": matched_count,
            "successful_attempts": successful_attempts,
            "success_rate": (
                successful_attempts / judged_attempts if judged_attempts else None
            ),
            "used_index_fallback": used_index_fallback,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge judge-agent outputs into saved red-team results."
    )
    parser.add_argument(
        "--results-path",
        required=True,
        help="Path to the JSON results written by scripts/run_redteam.py",
    )
    parser.add_argument(
        "--judgments-json",
        help="Judge-agent JSON payload as a string",
    )
    parser.add_argument(
        "--judgments-path",
        help="Path to judge-agent JSON payload",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path for the merged output JSON",
    )
    parser.add_argument(
        "--delete-results",
        action="store_true",
        help="Delete the --results-path file after merging (leaves only the collated output)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with open(args.results_path, "r", encoding="utf-8") as f:
        results_payload = json.load(f)

    judgments_payload = _load_json_argument(
        args.judgments_json,
        args.judgments_path,
        flag_name="--judgments",
    )

    merged_payload = _merge_results(results_payload, judgments_payload)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_payload, f, indent=2)

    if args.delete_results:
        Path(args.results_path).unlink(missing_ok=True)

    print("=== Judge Output Saved ===")
    print(f"Merged output saved to: {args.output}")


if __name__ == "__main__":
    main()