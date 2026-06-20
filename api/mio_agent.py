"""
Music Bank — MIO Evaluator Agent (ACP) Job Service

Handles creating jobs on Virtuals ACP for the MIO Evaluator agent.
Uses the Virtuals ACP Python SDK (github.com/Virtual-Protocol/acp-python).

Job Flow:
1. Music Bank creates ACP job via Virtuals API
2. Virtuals routes job to MIO Evaluator agent
3. Agent processes using V4A framework
4. Results sent back via callback
5. Music Bank displays results to artist
"""

import os
import json
import time
import httpx
from typing import Optional
from api.config import MIO_AGENT_WALLET, MIO_AGENT_ID, MIO_AGENT_URL


class MIOJobService:
    """Manage ACP jobs with the MIO Evaluator agent."""

    def __init__(self):
        self.agent_wallet = MIO_AGENT_WALLET
        self.agent_id = MIO_AGENT_ID
        self.agent_url = MIO_AGENT_URL
        self.virtuals_api_key = os.getenv("VIRTUALS_API_KEY", "")
        self.base_url = "https://api.virtuals.io/v1"

    @property
    def available(self) -> bool:
        return bool(self.virtuals_api_key)

    async def create_job(
        self,
        track_id: int,
        track_title: str,
        artist_name: str,
        eval_type: str = "standard_eval",
        context: str = "",
    ) -> dict:
        """
        Create an ACP job on Virtuals for the MIO Evaluator agent.

        The job goes through 4 phases:
        1. Request — we submit the job request
        2. Negotiation — agent accepts and agrees on terms
        3. Transaction — payment held in escrow
        4. Evaluation — agent delivers results, payment released
        """
        if not self.available:
            return self._mock_job(track_title, artist_name, eval_type)

        # Map eval types to Virtuals job parameters
        job_configs = {
            "micro_eval": {
                "service_name": "micro_eval",
                "description": "Quick track quality evaluation (1-100 score)",
                "price_usd": 1,
                "price_mio": 20,
                "estimated_duration": "10s",
            },
            "standard_eval": {
                "service_name": "standard_eval",
                "description": "Detailed track analysis with feedback",
                "price_usd": 5,
                "price_mio": 100,
                "estimated_duration": "30s",
            },
            "full_eval": {
                "service_name": "full_eval",
                "description": "Full artist portfolio audit + recommendations",
                "price_usd": 15,
                "price_mio": 300,
                "estimated_duration": "2min",
            },
            "cluster_eval": {
                "service_name": "cluster_eval",
                "description": "Batch evaluation of up to 100 tracks",
                "price_usd": 99,
                "price_mio": 2000,
                "estimated_duration": "10min",
            },
        }

        config = job_configs.get(eval_type, job_configs["standard_eval"])

        job_data = {
            "agent_id": self.agent_id,
            "service_name": config["service_name"],
            "description": config["description"],
            "price_mio": config["price_mio"],
            "estimated_duration": config["estimated_duration"],
            "input_data": {
                "track_id": track_id,
                "track_title": track_title,
                "artist_name": artist_name,
                "context": context,
                "callback_url": f"{os.getenv('APP_URL', '')}/api/agent/callback",
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/acp/jobs",
                json=job_data,
                headers={
                    "Authorization": f"Bearer {self.virtuals_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if resp.status_code == 200:
                result = resp.json()
                return {
                    "status": "created",
                    "job_id": result.get("job_id"),
                    "virtuals_job_id": result.get("id"),
                    "phase": "request",
                    "message": f"Job created on Virtuals ACP! Phase: Request. Agent will accept shortly.",
                    "estimated_completion": config["estimated_duration"],
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to create job: {resp.status_code} {resp.text}",
                }

    async def get_job_status(self, job_id: str) -> dict:
        """Check job status on Virtuals ACP."""
        if not self.available:
            return {"status": "completed", "result": {"score": 75, "feedback": "Good track!"}}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/acp/jobs/{job_id}",
                headers={"Authorization": f"Bearer {self.virtuals_api_key}"},
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"status": "unknown", "error": resp.text}

    async def approve_job(self, job_id: str) -> dict:
        """Approve/accept a job on Virtuals (moves to Transaction phase)."""
        if not self.available:
            return {"status": "approved"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/acp/jobs/{job_id}/approve",
                headers={"Authorization": f"Bearer {self.virtuals_api_key}"},
                timeout=15.0,
            )
            return resp.json() if resp.status_code == 200 else {"status": "error"}

    def _mock_job(self, track_title: str, artist_name: str, eval_type: str) -> dict:
        """Mock job for development (no Virtuals API key)."""
        import random
        durations = {
            "micro_eval": "~10 seconds",
            "standard_eval": "~30 seconds",
            "full_eval": "~2 minutes",
            "cluster_eval": "~10 minutes",
        }
        job_id = f"mock_{random.randint(1000,9999)}"
        return {
            "status": "created",
            "job_id": job_id,
            "virtuals_job_id": None,
            "phase": "request",
            "message": f"Mock job created for '{track_title}' by {artist_name}. Type: {eval_type}.",
            "estimated_completion": durations.get(eval_type, "~30 seconds"),
            "mock": True,
        }

    def get_service_tiers(self) -> list[dict]:
        """Return available evaluation service tiers."""
        return [
            {
                "id": "micro_eval",
                "name": "Quick Eval",
                "description": "Single track quality check (1-100 score)",
                "price_usd": 1,
                "price_mio": 20,
                "duration": "~10 seconds",
                "icon": "⚡",
            },
            {
                "id": "standard_eval",
                "name": "Standard Eval",
                "description": "Detailed track analysis with feedback",
                "price_usd": 5,
                "price_mio": 100,
                "duration": "~30 seconds",
                "icon": "📊",
            },
            {
                "id": "full_eval",
                "name": "Portfolio Audit",
                "description": "Full artist portfolio analysis + recommendations",
                "price_usd": 15,
                "price_mio": 300,
                "duration": "~2 minutes",
                "icon": "🔍",
            },
            {
                "id": "cluster_eval",
                "name": "Batch Eval",
                "description": "Evaluate up to 100 tracks at once",
                "price_usd": 99,
                "price_mio": 2000,
                "duration": "~10 minutes",
                "icon": "📦",
            },
        ]


# Singleton
mio_job_service = MIOJobService()
