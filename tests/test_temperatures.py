"""python3 -m unittest tests/test_temperatures.py  (stdlib only; krino.temperatures imports no torch)"""
import math, os, tempfile, unittest, json
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from krino.temperatures import apply, load, parse, temper, DEFAULT


class TemperTests(unittest.TestCase):
    def test_argmax_and_sum(self):
        p = [0.2, 0.5, 0.3]
        for t in (0.3, 0.5, 1.0, 1.95):
            q = temper(p, t)
            self.assertAlmostEqual(sum(q), 1.0, places=9)
            self.assertEqual(max(range(3), key=q.__getitem__), 1)
        self.assertEqual(temper(p, 1.0), p)

    def test_sharpening_leaves_the_noul_band(self):
        p = [0.35, 0.65]                      # in (0.20, 0.80): an abstention under METHOD-v1.5
        self.assertGreater(temper(p, 0.3)[1], 0.80)
        self.assertLess(temper(p, 1.95)[1], 0.65)

    def test_softmax_identity(self):
        z = [1.0, -0.5, 0.2]; m = max(z); e = [math.exp(v - m) for v in z]; p = [v / sum(e) for v in e]
        e2 = [math.exp((v - m) / 2.0) for v in z]; want = [v / sum(e2) for v in e2]
        for a, b in zip(temper(p, 2.0), want): self.assertAlmostEqual(a, b, places=9)

    def test_apply_by_type(self):
        ps = [[0.35, 0.65], [0.2, 0.5, 0.3]]; meta = [{"type": "noul"}, {"type": "choice"}]
        out = apply(ps, meta, {"noul": 0.3, "choice": 1.0})
        self.assertGreater(out[0][1], 0.8); self.assertEqual(out[1], ps[1])

    def test_parse_and_load(self):
        self.assertEqual(parse("choice=1.95, noul=0.3"), {"choice": 1.95, "noul": 0.3})
        with self.assertRaises(ValueError): parse("foo=1")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load(d), DEFAULT)
            Path(d, "krino.json").write_text(json.dumps({"temperatures": {"noul": 0.5}}))
            self.assertEqual(load(d)["noul"], 0.5); self.assertEqual(load(d)["choice"], 1.0)
            os.environ["KRINO_TEMPERATURES"] = "score=0.7"
            try: self.assertEqual(load(d)["score"], 0.7)
            finally: del os.environ["KRINO_TEMPERATURES"]


if __name__ == "__main__":
    unittest.main()
