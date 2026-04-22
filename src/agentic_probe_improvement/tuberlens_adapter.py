from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MessageLike = dict[str, str]
ConversationLike = list[MessageLike]
RunnerInput = str | ConversationLike



class TuberLensProbeRunner:
    """Small wrapper around a pickled TuberLens probe and its backing model."""

    def __init__(self, probe_path: str | Path):
        self.probe_path = Path(probe_path)
        if not self.probe_path.exists():
            raise FileNotFoundError(f"Probe not found: {self.probe_path}")

        self._probe = self._load_probe(self.probe_path)
        self._validate_probe()

        from tuberlens.model import LLMModel  # type: ignore

        self._model = LLMModel.load(self._probe.model_name)
        self._align_probe_classifier_device()

    @staticmethod
    def _load_probe(path: Path) -> Any:
        try:
            with path.open("rb") as f:
                return pickle.load(f)
        except RuntimeError as err:
            # Some probe pickles were serialized from CUDA environments.
            # On CPU-only machines, retry by mapping tensors to CPU.
            if "Attempting to deserialize object on a CUDA device" not in str(err):
                raise

            import torch

            return torch.load(path, map_location=torch.device("cpu"), weights_only=False)

    def _align_probe_classifier_device(self) -> None:
        """Ensure probe classifier tensors live on the same device as model activations."""
        classifier = getattr(self._probe, "_classifier", None)
        if classifier is None:
            return

        classifier_model = getattr(classifier, "model", None)
        if classifier_model is None:
            return

        target_device = getattr(self._model, "llm_device", None)
        if target_device is None:
            target_device = next(self._model.model.parameters()).device

        classifier_model.to(target_device)
        if hasattr(classifier, "device"):
            classifier.device = str(target_device)

    def _validate_probe(self) -> None:
        required_attrs = ["model_name", "layer", "predict_proba_from_inputs"]
        for attr in required_attrs:
            if not hasattr(self._probe, attr):
                raise AttributeError(
                    f"Loaded probe is missing required attribute: {attr}"
                )

        if self._probe.model_name is None:
            raise ValueError("Probe has no model_name")
        if self._probe.layer is None:
            raise ValueError("Probe has no layer")

    @property
    def pos_label(self) -> str:
        return getattr(self._probe, "pos_class_label", "positive")

    @property
    def neg_label(self) -> str:
        return getattr(self._probe, "neg_class_label", "negative")

    @property
    def description(self) -> str:
        return getattr(self._probe, "description", "Binary classification probe")

    def _to_tuberlens_inputs(self, inputs: list[RunnerInput]):
        from tuberlens.interfaces.dataset import Message  # type: ignore

        normalized_inputs: list[list[Any]] = []
        for sample in inputs:
            if isinstance(sample, str):
                normalized_inputs.append([Message(role="user", content=sample)])
                continue

            conversation: list[Any] = []
            for idx, message in enumerate(sample):
                role = message.get("role")
                content = message.get("content")
                if not isinstance(role, str) or not isinstance(content, str):
                    raise ValueError(
                        "Invalid conversation message at index "
                        f"{idx}. Expected dict with string role/content."
                    )
                conversation.append(Message(role=role, content=content))

            normalized_inputs.append(conversation)

        return normalized_inputs


    def predict_scores(self, inputs: list[RunnerInput]) -> list[float]:
        tuberlens_inputs = self._to_tuberlens_inputs(inputs)
        scores = self._probe.predict_proba_from_inputs(
            tuberlens_inputs, model=self._model
        )
        return [float(x) for x in scores]
