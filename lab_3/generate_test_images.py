
import numpy as np
from PIL import Image
import os

def create_noise_image(width=512, height=512):
    x = np.linspace(0, 255, width)
    y = np.linspace(0, 255, height)
    base = np.meshgrid(x, y)
    img = (base[0] + base[1]) / 2
    noise = np.random.normal(0, 30, (height, width))
    noisy1 = np.clip(img + noise, 0, 255).astype(np.uint8)
    salt_pepper = np.random.random((height, width))
    noisy2 = np.copy(img).astype(np.uint8)
    noisy2[salt_pepper > 0.99] = 255
    noisy2[salt_pepper < 0.01] = 0
    return noisy1, noisy2

def create_blurry_image(width=512, height=512):
    from scipy import ndimage
    x = np.linspace(0, 255, width)
    y = np.linspace(0, 255, height)
    base = np.meshgrid(x, y)
    img = (base[0] + base[1]) / 2
    blurry = ndimage.gaussian_filter(img, sigma=2)
    return blurry.astype(np.uint8)

def create_low_contrast_image(width=512, height=512):
    """Create low contrast test image."""
    x = np.linspace(0, 255, width)
    y = np.linspace(0, 255, height)
    base = np.meshgrid(x, y)
    img = (base[0] + base[1]) / 2
    img = np.clip(img + np.random.normal(0, 20, (height, width)), 0, 255)
    return img.astype(np.uint8)

def create_binary_shapes_image(width=512, height=512, seed=0):
    rng = np.random.RandomState(seed)
    img = np.zeros((height, width), dtype=np.uint8)

    sq = width // 6
    cx, cy = int(width * 0.2), int(height * 0.2)
    img[cy - sq:cy + sq, cx - sq:cx + sq] = 255

    r = width // 8
    cx, cy = int(width * 0.75), int(height * 0.2)
    y, x = np.ogrid[-cy:height - cy, -cx:width - cx]
    img[x**2 + y**2 <= r**2] = 255

    cx, cy = int(width * 0.2), int(height * 0.75)
    arm, thick = width // 7, width // 28
    img[cy - thick:cy + thick, cx - arm:cx + arm] = 255
    img[cy - arm:cy + arm, cx - thick:cx + thick] = 255

    y0 = int(height * 0.5)
    img[y0:y0 + 2, int(width * 0.55):int(width * 0.95)] = 255

    cx, cy = int(width * 0.75), int(height * 0.75)
    br = width // 10
    y, x = np.ogrid[-cy:height - cy, -cx:width - cx]
    img[x**2 + y**2 <= br**2] = 255
    for _ in range(6):
        ang = rng.uniform(0, 2 * np.pi)
        dist = br + rng.randint(2, 10)
        px = int(cx + dist * np.cos(ang))
        py = int(cy + dist * np.sin(ang))
        bump = rng.randint(1, 4)
        img[max(0, py - bump):py + bump, max(0, px - bump):px + bump] = 255

    noise = rng.random((height, width))
    img[noise > 0.998] = 255

    return img


def create_small_details_image(width=512, height=512, seed=0):
    """Create grayscale image with uneven background and small bright/dark blobs."""
    rng = np.random.RandomState(seed)
    x = np.linspace(0, 4 * np.pi, width)
    y = np.linspace(0, 4 * np.pi, height)
    xx, yy = np.meshgrid(x, y)
    background = 128 + 40 * np.sin(xx / 2 + seed) + 25 * np.cos(yy / 3) + 15 * np.sin((xx + yy) / 4)
    img = np.clip(background, 20, 235)

    for _ in range(15):
        cx = rng.randint(10, width - 10)
        cy = rng.randint(10, height - 10)
        rad = rng.randint(2, 5)
        local = img[max(0, cy - rad):cy + rad, max(0, cx - rad):cx + rad]
        img[max(0, cy - rad):cy + rad, max(0, cx - rad):cx + rad] = np.clip(local + rng.randint(60, 100), 0, 255)

    for _ in range(15):
        cx = rng.randint(10, width - 10)
        cy = rng.randint(10, height - 10)
        rad = rng.randint(2, 5)
        local = img[max(0, cy - rad):cy + rad, max(0, cx - rad):cx + rad]
        img[max(0, cy - rad):cy + rad, max(0, cx - rad):cx + rad] = np.clip(local - rng.randint(60, 100), 0, 255)

    return img.astype(np.uint8)


def save_images():
    """Generate and save test images."""
    for i in range(5):
        noisy1, noisy2 = create_noise_image()
        blurry = create_blurry_image()
        low_contrast = create_low_contrast_image()
        binary_shapes = create_binary_shapes_image(seed=i)
        small_details = create_small_details_image(seed=i)

        # Save with prefix
        Image.fromarray(noisy1).save(f"test_images/noisy/noise_gauss_{i}.png")
        Image.fromarray(noisy2).save(f"test_images/noisy/noise_salt_pepper_{i}.png")
        Image.fromarray(blurry).save(f"test_images/blurry/blurry_{i}.png")
        Image.fromarray(low_contrast).save(f"test_images/low_contrast/low_contrast_{i}.png")
        Image.fromarray(binary_shapes).save(f"test_images/morphology_binary/binary_{i}.png")
        Image.fromarray(small_details).save(f"test_images/morphology_details/details_{i}.png")

    print("Generated 30 test images (5 in each category)")

if __name__ == "__main__":
    os.makedirs("test_images/noisy", exist_ok=True)
    os.makedirs("test_images/blurry", exist_ok=True)
    os.makedirs("test_images/low_contrast", exist_ok=True)
    os.makedirs("test_images/morphology_binary", exist_ok=True)
    os.makedirs("test_images/morphology_details", exist_ok=True)
    save_images()