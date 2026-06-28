import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Application, Job
from backend.models import User
from backend.routes.applications import prepare, save_review, start_automation
from backend.schemas import AutomationStartIn, ReviewUpdateIn


class PrepareApplicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.job = Job(
            job_id="job_test",
            user_id="demo_user",
            company="Acme",
            title="Software Engineer",
            duplicate_hash="prepare-test",
            resume_version="SWE",
            status="SCORED",
        )
        self.db.add(self.job)
        self.user = User(user_id="demo_user", first_name="Ada", last_name="Lovelace", full_name="Ada Lovelace", email="ada@example.com")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_new_application_is_prepared_for_review(self):
        application = prepare(self.job.job_id, self.db, self.user)

        self.assertEqual(application.status, "NEEDS_REVIEW")
        self.assertEqual(application.current_step, "Prepared for review")
        self.assertEqual(application.resume_version, "SWE")
        self.assertEqual(application.generated_answers["full_name"], "Ada Lovelace")
        self.assertEqual(application.generated_answers["email"], "ada@example.com")
        self.assertIn("Please verify", application.generated_answers["notes_for_review"])
        self.assertIn("Application prepared for review.", application.logs)
        self.assertEqual(self.db.get(Job, self.job.id).status, "NEEDS_REVIEW")

    def test_legacy_created_application_is_updated(self):
        existing = Application(
            application_id="app_test",
            user_id="demo_user",
            job_id=self.job.job_id,
            status="CREATED",
            current_step="READY_FOR_WORKER",
        )
        self.db.add(existing)
        self.db.commit()

        application = prepare(self.job.job_id, self.db, self.user)

        self.assertEqual(application.application_id, "app_test")
        self.assertEqual(application.status, "NEEDS_REVIEW")
        self.assertEqual(application.current_step, "Prepared for review")

    def test_review_edits_persist_and_automation_queues(self):
        application = prepare(self.job.job_id, self.db, self.user)
        answers = dict(application.generated_answers)
        answers["why_interested"] = "Edited and verified answer."

        saved = save_review(application.application_id, ReviewUpdateIn(generated_answers=answers, notes="Checked facts"), self.db, self.user)
        self.assertEqual(saved.generated_answers["why_interested"], "Edited and verified answer.")
        self.assertIn("Review changes saved.", saved.logs)

        queued = start_automation(application.application_id, AutomationStartIn(confirm_missing=True), self.db, self.user)
        self.assertTrue(queued["queued"])
        self.assertEqual(queued["application"].status, "READY_FOR_WORKER")
        self.assertEqual(queued["application"].current_step, "Queued for automation")
        self.assertIn("Application queued for worker automation.", queued["application"].logs)


if __name__ == "__main__":
    unittest.main()
