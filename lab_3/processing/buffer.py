#!/usr/bin/env python3
"""Buffer Wrapper layer: edge-padding abstraction for pixel access."""
import numpy as np

_MODES = {"reflect": "reflect", "clamp": "edge"}


def pad(image: np.ndarray, amount, padding: str = "reflect") -> np.ndarray:
    """Pad image by amount using the given padding strategy ('reflect' or 'clamp')."""
    if padding not in _MODES:
        raise ValueError(f"Unknown padding mode: {padding}")
    return np.pad(image, amount, mode=_MODES[padding])
