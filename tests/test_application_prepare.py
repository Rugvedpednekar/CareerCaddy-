import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Application, Job
from backend.routes.applications import prepare


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
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_new_application_is_prepared_for_review(self):
        application = prepare(self.job.job_id, self.db)

        self.assertEqual(application.status, "NEEDS_REVIEW")
        self.assertEqual(application.current_step, "Prepared for review")
        self.assertEqual(application.resume_version, "SWE")
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

        application = prepare(self.job.job_id, self.db)

        self.assertEqual(application.application_id, "app_test")
        self.assertEqual(application.status, "NEEDS_REVIEW")
        self.assertEqual(application.current_step, "Prepared for review")


if __name__ == "__main__":
    unittest.main()
