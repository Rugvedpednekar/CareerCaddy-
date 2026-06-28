import unittest
from pathlib import Path
from unittest.mock import patch

from backend.resume_parser import parse_resume_file


class ResumeParserTests(unittest.TestCase):
    @patch("backend.resume_parser._read_text")
    def test_extracts_resume_contact_skills_and_sections(self, read_text):
        read_text.return_value = """Ada Lovelace
ada@example.com | (555) 111-2222 | Boston, MA
https://linkedin.com/in/ada-lovelace https://github.com/ada
SUMMARY
Data analyst focused on Python, SQL, Excel, SPSS, research, and survey design.
EXPERIENCE
Analyzed employee engagement survey results using SPSS and Excel.
PROJECTS
Built a people analytics research dashboard.
EDUCATION
Master of Science in Organizational Psychology, Expected May 2027"""

        parsed = parse_resume_file(str(Path("resume.txt")))

        self.assertEqual(parsed["full_name"], "Ada Lovelace")
        self.assertEqual(parsed["email"], "ada@example.com")
        self.assertEqual(parsed["location"], "Boston, MA")
        self.assertIn("SPSS", parsed["skills"])
        self.assertTrue(parsed["experience"])
        self.assertTrue(parsed["projects"])
        self.assertEqual(parsed["graduation_date"], "May 2027")


if __name__ == "__main__":
    unittest.main()
