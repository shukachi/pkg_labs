#!/usr/bin/env python3
"""Morphological image processing operations."""
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from numpy.lib.stride_tricks import sliding_window_view
from processing import buffer


def _as_gray(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale float64."""
    if image.ndim >= 3 and image.shape[-1] in (3, 4):
        return np.dot(image[..., :3], [0.2989, 0.5870, 0.1140]).astype(np.float64)
    return image.astype(np.float64)


def _apply_per_channel(image: np.ndarray, func, *args, **kwargs) -> np.ndarray:
    """Apply a single-channel 2D func to each color channel independently."""
    if image.ndim < 3:
        return func(image, *args, **kwargs)
    has_alpha = image.shape[-1] == 4
    with ThreadPoolExecutor(max_workers=3) as executor:
        channels = list(executor.map(lambda c: func(image[..., c], *args, **kwargs), range(3)))
    if has_alpha:
        channels.append(image[..., 3].astype(np.float64))
    return np.stack(channels, axis=-1)


def _sliding_window(image: np.ndarray, ksize: int, padding: str = "reflect") -> np.ndarray:
    """Sliding window view with padding."""
    pad = ksize // 2
    padded = buffer.pad(image, pad, padding)
    return sliding_window_view(padded, (ksize, ksize))


def _streaming_minmax_1d(arr: np.ndarray, k: int, op: str) -> np.ndarray:
    """Sliding window min/max along the last axis (van Herk / Gil-Werman), O(n)."""
    n_pad = arr.shape[-1]
    n_out = n_pad - k + 1
    nblocks = -(-n_pad // k)
    total = nblocks * k
    extra = total - n_pad
    if extra:
        pad_width = [(0, 0)] * (arr.ndim - 1) + [(0, extra)]
        arr = np.pad(arr, pad_width, mode="edge")
    blocks = arr.reshape(arr.shape[:-1] + (nblocks, k))
    reducer = np.minimum if op == "min" else np.maximum
    g = reducer.accumulate(blocks, axis=-1)
    h = reducer.accumulate(blocks[..., ::-1], axis=-1)[..., ::-1]
    g = g.reshape(arr.shape[:-1] + (total,))
    h = h.reshape(arr.shape[:-1] + (total,))
    left = h[..., :n_out]
    right = g[..., k - 1:k - 1 + n_out]
    return reducer(left, right)


def _separable_minmax(image: np.ndarray, kh: int, kw: int, padding: str, op: str) -> np.ndarray:
    """Full 2D min/max filter for a solid kh x kw rectangle via two 1D passes."""
    pad_h, pad_w = kh // 2, kw // 2
    padded = buffer.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), padding)
    rows = _streaming_minmax_1d(padded, kw, op)
    cols = _streaming_minmax_1d(rows.T, kh, op).T
    return cols


def _apply_kernel(image: np.ndarray, kernel: np.ndarray, operation: str = 'min', padding: str = "reflect") -> np.ndarray:
    """Apply a binary kernel with given operation (min/max)."""
    if operation in ('min', 'max') and np.all(kernel == 1):
        kh, kw = kernel.shape
        return _separable_minmax(image, kh, kw, padding, operation)
    kh, kw = kernel.shape
    pad_h, pad_w = kh // 2, kw // 2
    padded = buffer.pad(image, (pad_h, pad_w), padding)
    windows = sliding_window_view(padded, (kh, kw))  # (H, W, kh, kw)
    # Zero out positions where kernel is 0
    mask = kernel.astype(bool)
    masked = np.where(mask, windows, np.inf if operation == 'min' else -np.inf)
    if operation == 'min':
        result = masked.min(axis=(2, 3))
    else:
        result = masked.max(axis=(2, 3))
    return result


def create_structuring_element(shape: str = 'cross', size: int = 3) -> np.ndarray:
    """Create structuring element (structuring element).

    Args:
        shape: 'cross', 'square', 'diamond', 'disk', 'line_h', 'line_v'
        size: size of the structuring element (must be odd)

    Returns:
        Binary kernel (1 = foreground, 0 = background)
    """
    if size % 2 == 0:
        size += 1
    n = size
    se = np.zeros((n, n), dtype=np.uint8)
    center = n // 2

    if shape == 'square':
        se[:] = 1
    elif shape == 'cross':
        se[center, :] = 1
        se[:, center] = 1
    elif shape == 'diamond':
        # Manhattan distance from center
        y, x = np.ogrid[-center:n-center, -center:n-center]
        se = (np.abs(x) + np.abs(y) <= center).astype(np.uint8)
    elif shape == 'disk':
        # Euclidean distance from center
        y, x = np.ogrid[-center:n-center, -center:n-center]
        se = (x**2 + y**2 <= center**2).astype(np.uint8)
    elif shape == 'line_h':
        se[center, :] = 1
    elif shape == 'line_v':
        se[:, center] = 1
    else:
        se[:] = 1
    return se


def _erosion_gray(image: np.ndarray, se: np.ndarray, padding: str) -> np.ndarray:
    img = _as_gray(image)
    return _apply_kernel(img, se, operation='min', padding=padding)


def erosion(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """Erosion: min filter with structuring element."""
    if image.ndim < 3:
        return _erosion_gray(image, se, padding)
    return _apply_per_channel(image, _erosion_gray, se, padding)


def _dilation_gray(image: np.ndarray, se: np.ndarray, padding: str) -> np.ndarray:
    img = _as_gray(image)
    return _apply_kernel(img, se, operation='max', padding=padding)


def dilation(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """Dilation: max filter with structuring element."""
    if image.ndim < 3:
        return _dilation_gray(image, se, padding)
    return _apply_per_channel(image, _dilation_gray, se, padding)


def opening(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """Opening: erosion followed by dilation."""
    return dilation(erosion(image, se, padding), se, padding)


def closing(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """Closing: dilation followed by erosion."""
    return erosion(dilation(image, se, padding), se, padding)


def gradient(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """Morphological gradient: dilation - erosion."""
    return dilation(image, se, padding) - erosion(image, se, padding)


def internal_gradient(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """Internal gradient: image - erosion."""
    return image.astype(np.float64) - erosion(image, se, padding)


def external_gradient(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """External gradient: dilation - image."""
    return dilation(image, se, padding) - image.astype(np.float64)


def top_hat(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """White top hat: image - opening."""
    return image.astype(np.float64) - opening(image, se, padding)


def black_hat(image: np.ndarray, se: np.ndarray, padding: str = "reflect") -> np.ndarray:
    """Black top hat: closing - image."""
    return closing(image, se, padding) - image.astype(np.float64)