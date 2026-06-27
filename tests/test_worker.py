import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import Application, Job, User
import worker.worker as worker_module


class FakePage:
    def goto(self, url, **kwargs):
        self.url = url


class FakeContext:
    def __init__(self):
        self.page = FakePage()

    def new_page(self):
        return self.page

    def close(self):
        pass


class FakeBrowser:
    def new_context(self):
        return FakeContext()

    def close(self):
        pass


class FakePlaywright:
    def stop(self):
        pass


class FakeHandler:
    @staticmethod
    def prepare_application(page, job, profile, resume_path):
        return {"logs": ["Filled Email"], "blocker": None}


class WorkerTests(unittest.TestCase):
    def test_worker_prepares_queued_application_without_submit(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        db = factory()
        job = Job(job_id="job_worker", user_id="demo_user", company="Acme", title="Engineer", apply_url="https://example.com/apply", duplicate_hash="worker")
        app = Application(application_id="app_worker", user_id="demo_user", job_id="job_worker", status="READY_FOR_WORKER", generated_answers={"email": "ada@example.com"}, logs=[])
        db.add_all([job, app, User(user_id="demo_user", email="ada@example.com")])
        db.commit(); db.close()

        with patch.object(worker_module, "SessionLocal", factory), patch.object(worker_module, "create_tables"), patch.object(worker_module, "launch_browser", return_value=(FakePlaywright(), FakeBrowser())), patch.object(worker_module, "detect_blocker", return_value=None), patch.object(worker_module, "save_screenshot"), patch.dict(worker_module.HANDLERS, {"generic": FakeHandler}):
            worker_module.run_once()

        check = factory()
        saved = check.query(Application).filter_by(application_id="app_worker").one()
        self.assertEqual(saved.status, "NEEDS_REVIEW")
        self.assertEqual(saved.current_step, "Prepared for review")
        self.assertIn("Worker started preparing application.", saved.logs)
        self.assertIn("Stopped before final submission.", saved.logs)
        self.assertIn("Ready for user review.", saved.logs)
        check.close(); engine.dispose()


if __name__ == "__main__":
    unittest.main()
