"""Hire a worker — the marketplace primitive.

Buyer creates a canonical job → WorkerKit executes → outcome recorded.

This is the Trojan horse: every hire produces a SubmissionRun,
which builds worker capability evidence, which attracts more hires.
"""
from get_me_money.job import CanonicalJob, JobRouter, JobStatus


def create_hire_job(
    title: str,
    description: str,
    reward: float,
    skills: list[str] | None = None,
    buyer_id: str = "",
) -> CanonicalJob:
    """Create a canonical job for hiring a worker."""
    job = CanonicalJob(
        title=title,
        description=description,
        reward=reward,
        skills_required=skills or [],
        hard_requirements=[description[:200]],
        scoring={"completeness": 0.5, "quality": 0.5, "timeliness": 0.25, "communication": 0.25},
        buyer_id=buyer_id,
    )
    job.status = JobStatus.FUNDED
    return job


def estimate_job_cost(job: CanonicalJob) -> dict:
    """Estimate the cost of executing a job through WorkerKit."""
    return {
        "job_reward": job.reward,
        "estimated_inference_cost": job.reward * 0.02,
        "estimated_platform_fee": job.reward * 0.075,
        "estimated_total_cost": job.reward * 0.10,
        "estimated_net": job.reward * 0.90,
        "breakdown": {
            "inference": "hermes model calls",
            "platform_fee": "taskmarket/moltjobs fee",
            "verification": "judge + gate",
        },
    }
