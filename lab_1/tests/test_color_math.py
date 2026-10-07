
import unittest
from model.color_math import (ColorEngine, rgb_to_hsv, hsv_to_rgb,
                              build_rgb_to_xyz, ILLUMINANTS)


class TestRGBtoXYZ(unittest.TestCase):
    def setUp(self):
        self.eng = ColorEngine("D65")

    def test_red_d65(self):
        x, y, z = self.eng.rgb_to_xyz([255, 0, 0])
        self.assertAlmostEqual(x, 0.4124, places=3)
        self.assertAlmostEqual(y, 0.2126, places=3)
        self.assertAlmostEqual(z, 0.0193, places=3)

    def test_green_d65(self):
        x, y, z = self.eng.rgb_to_xyz([0, 255, 0])
        self.assertAlmostEqual(x, 0.3576, places=3)
        self.assertAlmostEqual(y, 0.7152, places=3)
        self.assertAlmostEqual(z, 0.1192, places=3)

    def test_blue_d65(self):
        x, y, z = self.eng.rgb_to_xyz([0, 0, 255])
        self.assertAlmostEqual(x, 0.1805, places=3)
        self.assertAlmostEqual(y, 0.0722, places=3)
        self.assertAlmostEqual(z, 0.9503, places=3)

    def test_white_is_unit_luminance(self):
        _, y, _ = self.eng.rgb_to_xyz([255, 255, 255])
        self.assertAlmostEqual(y, 1.0, places=6)

    def test_black(self):
        self.assertEqual(self.eng.rgb_to_xyz([0, 0, 0]), [0.0, 0.0, 0.0])

    def test_roundtrip(self):
        for rgb in ([255, 0, 0], [10, 200, 90], [128, 128, 128]):
            xyz = self.eng.rgb_to_xyz(rgb)
            back, _ = self.eng.xyz_to_rgb(xyz, "clip")
            self.assertEqual(back, rgb)


class TestIlluminants(unittest.TestCase):
    def test_matrices_differ(self):
        m65, _ = build_rgb_to_xyz(ILLUMINANTS["D65"])
        m50, _ = build_rgb_to_xyz(ILLUMINANTS["D50"])
        me,  _ = build_rgb_to_xyz(ILLUMINANTS["E"])
        self.assertNotAlmostEqual(m65[0][0], m50[0][0], places=3)
        self.assertNotAlmostEqual(m65[0][0], me[0][0], places=3)

    def test_matrix_rows_sum_to_white(self):
        for name in ("D65", "D50", "E"):
            eng = ColorEngine(name)
            xyz = eng.rgb_to_xyz([255, 255, 255])
            for got, exp in zip(xyz, eng.white_xyz):
                self.assertAlmostEqual(got, exp, places=6)


class TestHSV(unittest.TestCase):
    def test_red(self):
        self.assertEqual(rgb_to_hsv([255, 0, 0]), [0.0, 1.0, 1.0])

    def test_green(self):
        h, s, v = rgb_to_hsv([0, 255, 0])
        self.assertAlmostEqual(h, 120.0, places=6)

    def test_blue(self):
        h, s, v = rgb_to_hsv([0, 0, 255])
        self.assertAlmostEqual(h, 240.0, places=6)

    def test_gray_has_zero_saturation(self):
        self.assertEqual(rgb_to_hsv([128, 128, 128])[1], 0.0)

    def test_roundtrip(self):
        for rgb in ([255, 0, 0], [12, 200, 77], [0, 0, 0], [255, 255, 255]):
            h, s, v = rgb_to_hsv(rgb)
            self.assertEqual(hsv_to_rgb(h, s, v), rgb)


class TestGamutMapping(unittest.TestCase):
    def setUp(self):
        self.eng = ColorEngine("D65")

    def test_in_gamut_no_warning(self):
        rgb, clipped = self.eng.xyz_to_rgb(self.eng.rgb_to_xyz([10, 200, 90]))
        self.assertFalse(clipped)

    def test_clipping_vs_scaling(self):
        xyz = [0.15, 0.9, 0.05]
        rgb_c, clipped_c = self.eng.xyz_to_rgb(xyz, "clip")
        rgb_s, clipped_s = self.eng.xyz_to_rgb(xyz, "scale")
        self.assertTrue(clipped_c)
        self.assertTrue(clipped_s)
        self.assertTrue(all(0 <= c <= 255 for c in rgb_c))
        self.assertTrue(all(0 <= c <= 255 for c in rgb_s))
        self.assertNotEqual(rgb_c, rgb_s)

    def test_clip_saturates_at_border(self):
        rgb, clipped = self.eng.xyz_to_rgb([2.0, 0.0, 0.0], "clip")
        self.assertTrue(clipped)
        self.assertEqual(rgb[0], 255)
        self.assertEqual(rgb[1], 0)
        self.assertTrue(0 <= rgb[2] <= 255)


if __name__ == "__main__":
    unittest.main()