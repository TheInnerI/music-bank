"""
Music Bank — MIO Evaluator Agent (ACP) Integration

The MIO Evaluator agent (ID: 019ec475-d3e5-7e06-84e0-16f51fdea0b9) provides
AI-powered evaluation services for artists and fans on Music Bank.

Use cases:
1. Track Quality Evaluation — AI rates track quality (1-100)
2. Artist Portfolio Audit — Full portfolio analysis + recommendations
3. Fan Sentiment Analysis — Analyze comments/likes for artist feedback
4. Pricing Recommendations — Suggest sync licensing prices
5. Content Moderation — Flag inappropriate content
6. Trend Analysis — Identify trending genres/moods

Pricing (in $MIO tokens):
- micro_eval: $1 (single track quick eval)
- standard_eval: $5 (detailed track analysis)
- full_eval: $15 (portfolio audit)
- cluster_eval: $99 (batch evaluation of up to 100 tracks)
"""

import os
import httpx
import json
from typing import Optional
from api.config import MIO_AGENT_WALLET, MIO_AGENT_ID, MIO_AGENT_URL


class MIOAgentService:
    """Interact with the MIO Evaluator agent via ACP."""

    def __init__(self):
        self.agent_wallet = MIO_AGENT_WALLET
        self.agent_id = MIO_AGENT_ID
        self.agent_url = MIO_AGENT_URL
        self.api_key = os.getenv("VIRTUALS_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def available(self) -> bool:
        return self._available

    async def create_evaluation_job(
        self,
        track_id: int,
        track_title: str,
        artist_name: str,
        eval_type: str = "standard_eval",
        context: str = "",
    ) -> dict:
        """
        Create an evaluation job for the MIO agent.

        eval_type options:
        - micro_eval: Quick quality check ($1)
        - standard_eval: Detailed analysis ($5)
        - full_eval: Portfolio audit ($15)
        - cluster_eval: Batch evaluation ($99)
        """
        if not self.available:
            return self._mock_evaluation(track_title, artist_name, eval_type)

        job_data = {
            "type": eval_type,
            "track_id": track_id,
            "track_title": track_title,
            "artist_name": artist_name,
            "context": context,
            "callback_url": f"{os.getenv('APP_URL', '')}/api/agent/callback",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.agent_url}/jobs",
                json=job_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            return resp.json()

    def _mock_evaluation(self, track_title: str, artist_name: str, eval_type: str) -> dict:
        """Mock evaluation for development."""
        import random
        return {
            "status": "pending",
            "job_id": f"mock_{random.randint(1000,9999)}",
            "eval_type": eval_type,
            "track_title": track_title,
            "artist_name": artist_name,
            "estimated_completion": "30 seconds",
            "mock": True,
        }

    async def get_job_status(self, job_id: str) -> dict:
        """Check status of an evaluation job."""
        if not self.available:
            return {"status": "completed", "result": {"score": 75, "feedback": "Good track!"}}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.agent_url}/jobs/{job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=15.0,
            )
            return resp.json()

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
mio_agent = MIOAgentService()
