#!/usr/bin/env python3
"""Nonlinear filters based on order statistics."""
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from numpy.lib.stride_tricks import sliding_window_view
from processing import buffer


def _as_gray(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale float64."""
    if image.ndim >= 3 and image.shape[-1] in (3, 4):
        # Standard RGB to grayscale weights
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


def _sliding_windows(image: np.ndarray, ksize: int, padding: str = "reflect") -> np.ndarray:
    """Create sliding window view of image with padding."""
    pad = ksize // 2
    padded = buffer.pad(image, pad, padding)
    # Sliding window view
    return sliding_window_view(padded, (ksize, ksize))  # (H, W, k, k)


def _sorted_windows(image: np.ndarray, ksize: int, padding: str = "reflect") -> np.ndarray:
    """Get sorted window values for each pixel."""
    windows = _sliding_windows(image, ksize, padding)
    # Flatten last two dimensions and sort
    h, w, k1, k2 = windows.shape
    flat = windows.reshape(h, w, k1 * k2)
    return np.sort(flat, axis=-1)


def _streaming_minmax_1d(arr: np.ndarray, k: int, op: str) -> np.ndarray:
    """Sliding window min/max along the last axis (van Herk / Gil-Werman).

    Runs in O(n) instead of O(n*k): the array is split into contiguous
    blocks of length k, with a running min/max accumulated from the left
    (g) and from the right (h) inside each block. Since the window length
    equals the block length, any window overlaps at most two adjacent
    blocks, so its min/max is just op(h[i], g[i + k - 1]).
    """
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


def _separable_minmax(image: np.ndarray, ksize: int, padding: str, op: str) -> np.ndarray:
    """Full 2D min/max filter for a square ksize x ksize window via two 1D passes."""
    half = ksize // 2
    padded = buffer.pad(image, half, padding)
    rows = _streaming_minmax_1d(padded, ksize, op)
    cols = _streaming_minmax_1d(rows.T, ksize, op).T
    return cols


def _median_filter_gray(image: np.ndarray, ksize: int, padding: str) -> np.ndarray:
    img = _as_gray(image)
    sorted_vals = _sorted_windows(img, ksize, padding)
    n = ksize * ksize
    return sorted_vals[..., n // 2]


def median_filter(image: np.ndarray, ksize: int = 3, padding: str = "reflect") -> np.ndarray:
    """Median filter (order statistic filter with median)."""
    if ksize % 2 == 0:
        ksize += 1
    if image.ndim < 3:
        return _median_filter_gray(image, ksize, padding)
    return _apply_per_channel(image, _median_filter_gray, ksize, padding)


def _min_filter_gray(image: np.ndarray, ksize: int, padding: str) -> np.ndarray:
    img = _as_gray(image)
    return _separable_minmax(img, ksize, padding, "min")


def min_filter(image: np.ndarray, ksize: int = 3, padding: str = "reflect") -> np.ndarray:
    """Minimum filter (erosion)."""
    if ksize % 2 == 0:
        ksize += 1
    if image.ndim < 3:
        return _min_filter_gray(image, ksize, padding)
    return _apply_per_channel(image, _min_filter_gray, ksize, padding)


def _max_filter_gray(image: np.ndarray, ksize: int, padding: str) -> np.ndarray:
    img = _as_gray(image)
    return _separable_minmax(img, ksize, padding, "max")


def max_filter(image: np.ndarray, ksize: int = 3, padding: str = "reflect") -> np.ndarray:
    """Maximum filter (dilation)."""
    if ksize % 2 == 0:
        ksize += 1
    if image.ndim < 3:
        return _max_filter_gray(image, ksize, padding)
    return _apply_per_channel(image, _max_filter_gray, ksize, padding)


def _percentile_filter_gray(image: np.ndarray, ksize: int, p: float, padding: str) -> np.ndarray:
    img = _as_gray(image)
    sorted_vals = _sorted_windows(img, ksize, padding)
    n = ksize * ksize
    rank = int(np.clip(np.round(p / 100.0 * (n - 1)), 0, n - 1))
    return sorted_vals[..., rank]


def percentile_filter(image: np.ndarray, ksize: int = 3, p: float = 50.0, padding: str = "reflect") -> np.ndarray:
    """Order statistic filter at given percentile p (0-100)."""
    if ksize % 2 == 0:
        ksize += 1
    if image.ndim < 3:
        return _percentile_filter_gray(image, ksize, p, padding)
    return _apply_per_channel(image, _percentile_filter_gray, ksize, p, padding)


def _alpha_trimmed_mean_filter_gray(image: np.ndarray, ksize: int, alpha: float, padding: str) -> np.ndarray:
    img = _as_gray(image)
    sorted_vals = _sorted_windows(img, ksize, padding)
    n = ksize * ksize
    trim = int(np.clip(np.round(alpha * n), 0, n // 2))
    if trim > 0:
        trimmed = sorted_vals[..., trim:n-trim]
    else:
        trimmed = sorted_vals
    return trimmed.mean(axis=-1)


def alpha_trimmed_mean_filter(image: np.ndarray, ksize: int = 3, alpha: float = 0.2, padding: str = "reflect") -> np.ndarray:
    """Alpha-trimmed mean filter."""
    if ksize % 2 == 0:
        ksize += 1
    if image.ndim < 3:
        return _alpha_trimmed_mean_filter_gray(image, ksize, alpha, padding)
    return _apply_per_channel(image, _alpha_trimmed_mean_filter_gray, ksize, alpha, padding)


def _adaptive_median_filter_gray(image: np.ndarray, max_ksize: int, start_ksize: int, padding: str) -> np.ndarray:
    img = _as_gray(image)
    h, w = img.shape
    result = np.zeros((h, w))
    assigned = np.zeros((h, w), dtype=bool)

    k = start_ksize
    while k <= max_ksize:
        hp = k // 2
        ek = 2 * hp + 1
        sorted_vals = _sorted_windows(img, ek, padding)
        n = ek * ek
        z_min = sorted_vals[..., 0]
        z_max = sorted_vals[..., -1]
        z_med = sorted_vals[..., n // 2]

        condition = (z_min < z_med) & (z_med < z_max)
        in_range = (z_min < img) & (img < z_max)
        candidate = np.where(in_range, img, z_med)

        take = condition & ~assigned
        result = np.where(take, candidate, result)
        assigned = assigned | take
        k += 2

    # Max window reached for any still-unassigned pixel
    hp = max_ksize // 2
    ek = 2 * hp + 1
    sorted_vals = _sorted_windows(img, ek, padding)
    fallback_median = sorted_vals[..., (ek * ek) // 2]
    result = np.where(assigned, result, fallback_median)

    return result


def adaptive_median_filter(image: np.ndarray, max_ksize: int = 7, start_ksize: int = 3, padding: str = "reflect") -> np.ndarray:
    """Adaptive median filter."""
    if image.ndim < 3:
        return _adaptive_median_filter_gray(image, max_ksize, start_ksize, padding)
    return _apply_per_channel(image, _adaptive_median_filter_gray, max_ksize, start_ksize, padding)


def _contraharmonic_mean_filter_gray(image: np.ndarray, ksize: int, Q: float, padding: str) -> np.ndarray:
    img = _as_gray(image)
    pad = ksize // 2
    padded = buffer.pad(img, pad, padding)
    # Create uniform kernel for mean
    kernel = np.ones((ksize, ksize))
    # Use convolution-like approach
    num = np.zeros_like(img)
    den = np.zeros_like(img)
    for di in range(ksize):
        for dj in range(ksize):
            w = padded[di:di+img.shape[0], dj:dj+img.shape[1]]
            num += w ** (Q + 1)
            den += w ** Q
    den = np.where(den == 0, 1, den)
    return num / den


def contraharmonic_mean_filter(image: np.ndarray, ksize: int = 3, Q: float = 1.5, padding: str = "reflect") -> np.ndarray:
    """Contraharmonic mean filter."""
    if ksize % 2 == 0:
        ksize += 1
    if image.ndim < 3:
        return _contraharmonic_mean_filter_gray(image, ksize, Q, padding)
    return _apply_per_channel(image, _contraharmonic_mean_filter_gray, ksize, Q, padding)


def _bilateral_filter_gray(image: np.ndarray, ksize: int, sigma_spatial: float, sigma_range: float, padding: str) -> np.ndarray:
    img = _as_gray(image) / 255.0  # Normalize
    h, w = img.shape
    pad = ksize // 2
    padded = buffer.pad(img, pad, padding)

    # Precompute spatial Gaussian
    x = np.arange(-pad, pad + 1)
    y = np.arange(-pad, pad + 1)
    X, Y = np.meshgrid(x, y)
    spatial_gauss = np.exp(-(X**2 + Y**2) / (2 * sigma_spatial**2))

    num = np.zeros_like(img)
    den = np.zeros_like(img)
    for di in range(ksize):
        for dj in range(ksize):
            window = padded[di:di+h, dj:dj+w]
            range_gauss = np.exp(-(window - img)**2 / (2 * sigma_range**2))
            weight = spatial_gauss[di, dj] * range_gauss
            num += weight * window
            den += weight
    zero_den = den == 0
    safe_den = np.where(zero_den, 1, den)
    result = np.where(zero_den, img, num / safe_den)

    return np.clip(result * 255, 0, 255)


def bilateral_filter(image: np.ndarray, ksize: int = 5, sigma_spatial: float = 1.5, sigma_range: float = 0.1, padding: str = "reflect") -> np.ndarray:
    """Bilateral filter (edge-preserving smoothing)."""
    if ksize % 2 == 0:
        ksize += 1
    if image.ndim < 3:
        return _bilateral_filter_gray(image, ksize, sigma_spatial, sigma_range, padding)
    return _apply_per_channel(image, _bilateral_filter_gray, ksize, sigma_spatial, sigma_range, padding)