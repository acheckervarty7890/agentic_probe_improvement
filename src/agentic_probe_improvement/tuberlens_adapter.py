from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BatchActivationsSummary:
    shape: tuple[int, ...]
    mean_abs_activation: float


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

    def _to_tuberlens_inputs(self, prompts: list[str]):
        from tuberlens.interfaces.dataset import Message  # type: ignore

        return [[Message(role="user", content=prompt)] for prompt in prompts]

    def extract_activation_summary(
        self,
        prompts: list[str],
        max_length: int = 512,
    ) -> BatchActivationsSummary:
        """Extract activations via TuberLens from the probe's configured layer."""
        inputs = self._to_tuberlens_inputs(prompts)
        activation = self._model.get_activations(
            inputs=inputs,
            layer=self._probe.layer,
            max_length=max_length,
            show_progress=False,
        )

        acts = activation.activations.float()
        return BatchActivationsSummary(
            shape=tuple(acts.shape),
            mean_abs_activation=float(acts.abs().mean().item()),
        )

    def predict_scores(self, prompts: list[str]) -> list[float]:
        inputs = self._to_tuberlens_inputs(prompts)
        scores = self._probe.predict_proba_from_inputs(inputs, model=self._model)
        return [float(x) for x in scores]
