import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTests(unittest.TestCase):
    def test_playwright_image_and_python_package_versions_match(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("playwright/python:v1.60.0-noble", dockerfile)
        self.assertIn("playwright==1.60.0", requirements)
        self.assertIn("PLAYWRIGHT_BROWSERS_PATH=/ms-playwright", dockerfile)

    def test_railway_uses_the_dockerfile_builder(self):
        config = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))

        self.assertEqual(config["build"]["builder"], "DOCKERFILE")
        self.assertEqual(config["build"]["dockerfilePath"], "Dockerfile")


if __name__ == "__main__":
    unittest.main()
