
import numpy as np
from PIL import Image
from processing import filters, morphology


def test_order_statistics():
    """Test order statistics filters."""
    # Create a synthetic test image
    x = np.linspace(0, 255, 512)
    y = np.linspace(0, 255, 512)
    X, Y = np.meshgrid(x, y)
    img = (X + Y) / 2
    img = np.clip(img + np.random.normal(0, 30, img.shape), 0, 255).astype(np.uint8)

    print("Testing order statistics filters...")
    for filter_name in ["median", "min", "max", "alpha_trimmed_mean", "adaptive_median", "contraharmonic_mean", "bilateral"]:
        ksize = 5
        try:
            if filter_name == "median":
                result = filters.median_filter(img, ksize)
            elif filter_name == "min":
                result = filters.min_filter(img, ksize)
            elif filter_name == "max":
                result = filters.max_filter(img, ksize)
            elif filter_name == "alpha_trimmed_mean":
                result = filters.alpha_trimmed_mean_filter(img, ksize, 0.2)
            elif filter_name == "adaptive_median":
                result = filters.adaptive_median_filter(img, 7, 3)
            elif filter_name == "contraharmonic_mean":
                result = filters.contraharmonic_mean_filter(img, ksize, 1.5)
            elif filter_name == "bilateral":
                result = filters.bilateral_filter(img, ksize, 1.5, 0.1)
            print(f"  {filter_name}: OK (shape {result.shape}, dtype {result.dtype})")
        except Exception as e:
            print(f"  {filter_name}: FAILED - {e}")


def test_morphology():
    """Test morphological operations."""
    # Create a binary test image
    img = np.zeros((100, 100), dtype=np.uint8)
    img[25:75, 25:75] = 255  # White square

    print("\nTesting morphological operations...")
    for shape in ["square", "cross", "diamond", "disk", "line_h", "line_v"]:
        se = morphology.create_structuring_element(shape, 3)
        try:
            erosion_result = morphology.erosion(img, se)
            dilation_result = morphology.dilation(img, se)
            opening_result = morphology.opening(img, se)
            closing_result = morphology.closing(img, se)
            gradient_result = morphology.gradient(img, se)
            top_hat_result = morphology.top_hat(img, se)
            black_hat_result = morphology.black_hat(img, se)
            print(f"  {shape}: OK")
        except Exception as e:
            print(f"  {shape}: FAILED - {e}")


def test_on_test_images():
    """Test on actual test images."""
    print("\nTesting on test images...")
    test_files = [
        "test_images/noisy/noise_gauss_0.png",
        "test_images/noisy/noise_salt_pepper_0.png",
        "test_images/blurry/blurry_0.png",
        "test_images/low_contrast/low_contrast_0.png",
    ]

    for test_file in test_files:
        try:
            img = Image.open(test_file)
            img_array = np.array(img)
            result = filters.median_filter(img_array, 5)
            # Save result
            out_file = f"test_outputs/{test_file.replace('.png', '_median.png')}"
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            Image.fromarray(np.clip(result, 0, 255).astype(np.uint8)).save(out_file)
            print(f"  {os.path.basename(test_file)}: OK")
        except Exception as e:
            print(f"  {test_file}: FAILED - {e}")


if __name__ == "__main__":
    import os
    test_order_statistics()
    test_morphology()
    test_on_test_images()
    print("\nAll tests completed.")