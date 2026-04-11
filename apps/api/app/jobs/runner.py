from app.jobs.service import JobService


def create_runner() -> JobService:
    return JobService()
