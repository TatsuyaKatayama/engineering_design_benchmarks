import tempfile
import unittest
from pathlib import Path

from scripts.build_public_dist import build_public_dist, check_public_dist


class PublicDistTest(unittest.TestCase):
    def test_build_public_dist_excludes_private_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dist_root = build_public_dist(Path(tmpdir) / "precision_arm_benchmark_public")

            self.assertTrue((dist_root / "README.md").exists())
            self.assertTrue((dist_root / "armbench_public" / "public_mcp_server.py").exists())
            self.assertFalse((dist_root / "armbench_eval").exists())
            self.assertFalse((dist_root / "knowledge" / "hidden_oracle.json").exists())
            self.assertFalse((dist_root / "reports" / "doe_sorted_regulation.csv").exists())

            check_public_dist(dist_root)


if __name__ == "__main__":
    unittest.main()
