import unittest
from unittest.mock import patch

from agent.form_filler import answer_custom_question


class AgentFormFillerTests(unittest.TestCase):
    def test_custom_answer_uses_profile_and_job_context(self):
        profile = {"full_name": "Ada Lovelace", "skills": ["Python"]}
        job = {"company": "Analytical Engines", "title": "Software Engineer", "job_description": "Build reliable systems"}

        with patch("agent.form_filler.generate_screening_answer", return_value="A tailored, truthful answer.") as generate:
            result = answer_custom_question("Why do you want to work here?", profile, job)

        self.assertEqual(result, "A tailored, truthful answer.")
        generate.assert_called_once_with("Why do you want to work here?", job, profile)


if __name__ == "__main__":
    unittest.main()
