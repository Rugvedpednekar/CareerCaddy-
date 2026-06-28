import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.serve import port_from_environment


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

    def test_web_launchers_do_not_depend_on_shell_port_expansion(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        procfile = (ROOT / "Procfile").read_text(encoding="utf-8")

        self.assertIn('CMD ["python", "-m", "backend.serve"]', dockerfile)
        self.assertIn("web: python -m backend.serve", procfile)
        self.assertNotIn("$PORT", dockerfile)
        self.assertNotIn("$PORT", procfile)

    def test_port_is_parsed_as_an_integer(self):
        with patch.dict(os.environ, {"PORT": "43123"}):
            self.assertEqual(port_from_environment(), 43123)

    def test_invalid_port_has_a_clear_error(self):
        with patch.dict(os.environ, {"PORT": "$PORT"}):
            with self.assertRaisesRegex(RuntimeError, "PORT must be an integer"):
                port_from_environment()


if __name__ == "__main__":
    unittest.main()
