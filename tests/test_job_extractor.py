import json
import unittest
from unittest.mock import Mock, patch

from backend.job_extractor import JobExtractionError, detect_portal, extract_job_from_url


class JobExtractorTests(unittest.TestCase):
    def test_detects_supported_portals(self):
        self.assertEqual(detect_portal("https://boards.greenhouse.io/acme/jobs/1"), "greenhouse")
        self.assertEqual(detect_portal("https://jobs.lever.co/acme/1"), "lever")
        self.assertEqual(detect_portal("https://example.com/jobs/1"), "generic")

    @patch("backend.job_extractor.httpx.get")
    def test_extracts_job_posting_json_ld(self, get):
        posting = {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Software Engineer",
            "hiringOrganization": {"name": "Acme"},
            "jobLocation": {"address": {"addressLocality": "New York", "addressRegion": "NY"}},
            "description": "<p>Build APIs with Python and SQL.</p>",
            "employmentType": "FULL_TIME",
        }
        response = Mock(status_code=200, text=f'<script type="application/ld+json">{json.dumps(posting)}</script>')
        response.raise_for_status.return_value = None
        get.return_value = response

        result = extract_job_from_url("https://boards.greenhouse.io/acme/jobs/1")

        self.assertEqual(result["company"], "Acme")
        self.assertEqual(result["title"], "Software Engineer")
        self.assertEqual(result["location"], "New York, NY")
        self.assertEqual(result["job_description"], "Build APIs with Python and SQL.")
        self.assertEqual(result["portal"], "greenhouse")

    def test_rejects_invalid_url(self):
        with self.assertRaises(JobExtractionError):
            extract_job_from_url("not-a-url")

    def test_rejects_private_url(self):
        with self.assertRaisesRegex(JobExtractionError, "private network"):
            extract_job_from_url("http://127.0.0.1/internal")

    @patch("backend.job_extractor.httpx.get")
    def test_reports_blocked_page(self, get):
        get.return_value = Mock(status_code=403)
        with self.assertRaisesRegex(JobExtractionError, "blocked or requires login"):
            extract_job_from_url("https://example.com/jobs/1")


if __name__ == "__main__":
    unittest.main()
