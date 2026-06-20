"""
Music Bank — MIO Evaluator Agent (ACP) Job Service

Uses the Virtuals Compute API (OpenAI-compatible) for agent inference
and the ACP CLI for job management.

API: https://compute.virtuals.io/v1
SDK: from openai import OpenAI
"""

import os
import json
import random
from typing import Optional
from api.config import MIO_AGENT_WALLET, MIO_AGENT_ID, MIO_AGENT_URL


class MIOJobService:
    """Manage ACP jobs with the MIO Evaluator agent via Virtuals Compute API."""

    def __init__(self):
        self.agent_wallet = MIO_AGENT_WALLET
        self.agent_id = MIO_AGENT_ID
        self.agent_url = MIO_AGENT_URL
        self.virtuals_api_key = os.getenv("VIRTUALS_API_KEY", "")
        self.compute_base_url = "https://compute.virtuals.io/v1"

    @property
    def available(self) -> bool:
        return bool(self.virtuals_api_key)

    def _get_client(self):
        """Get OpenAI-compatible client for Virtuals Compute API."""
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=self.virtuals_api_key,
                base_url=self.compute_base_url,
            )
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    async def create_job(
        self,
        track_id: int,
        track_title: str,
        artist_name: str,
        eval_type: str = "music_standard_eval",
        context: str = "",
    ) -> dict:
        """
        Create an evaluation job by calling the MIO agent via Virtuals Compute API.
        """
        if not self.available:
            return self._mock_job(track_title, artist_name, eval_type)

        try:
            client = self._get_client()

            # Build the evaluation prompt based on tier
            prompts = {
                "music_quick_eval": f"""You are the AIM MIO Evaluation Agent. Evaluate this music track quickly.

Track: {track_title}
Artist: {artist_name}
Genre: {context or 'Unknown'}

Provide a brief evaluation (1-100 score) with short feedback on:
- Production quality
- Marketability  
- Genre fit

Respond in JSON format:
{{"score": <1-100>, "feedback": "<brief feedback>", "verdict": "PASS or FAIL", "genre_fit": "<genre fit assessment>", "marketability": "<1-100>"}}""",

                "music_standard_eval": f"""You are the AIM MIO Evaluation Agent. Provide a detailed music track analysis.

Track: {track_title}
Artist: {artist_name}
Genre: {context or 'Unknown'}

Evaluate across these categories (each scored 1-100):
- Production Quality
- Marketability
- Genre Fit
- Originality
- Catchiness

Respond in JSON format:
{{"score": <overall 1-100>, "feedback": "<detailed feedback>", "verdict": "PASS or FAIL", "categories": {{"production": <score>, "marketability": <score>, "genre_fit": <score>, "originality": <score>, "catchiness": <score>}}, "recommendations": ["<actionable suggestion 1>", "<suggestion 2>"], "comparisons": "<comparison to top tracks in genre>"}}""",

                "music_portfolio_audit": f"""You are the AIM MIO Evaluation Agent. Provide a full artist portfolio audit.

Artist: {artist_name}
Track: {track_title} (representative sample)
Genre: {context or 'Unknown'}

Evaluate:
- Portfolio consistency
- Growth trajectory
- Genre positioning
- Market readiness
- Competitor comparison

Respond in JSON format:
{{"overall_score": <1-100>, "portfolio_report": "<full analysis>", "recommendations": ["<strategic recommendation 1>", "<suggestion 2>"], "competitor_analysis": "<comparison to similar artists>", "growth_trajectory": "<assessment>", "market_readiness": "<ready for label/sync/independent>"}}""",

                "music_batch_eval": f"""You are the AIM MIO Evaluation Agent. Batch evaluation summary.

Artist: {artist_name}
Track: {track_title} (one of multiple tracks)
Genre: {context or 'Unknown'}

Provide batch-level analysis:
- Individual track score
- Aggregate statistics
- Genre distribution insights
- Top track identification

Respond in JSON format:
{{"results": [{{"title": "<title>", "score": <1-100>, "feedback": "<brief>"}}], "aggregate_stats": {{"avg_score": <avg>, "min_score": <min>, "max_score": <max>, "std_dev": <std>}}, "genre_distribution": {{"<genre>": <count>}}, "top_tracks": ["<top track 1>"], "recommendations": ["<batch-level recommendation>"]}}""",
            }

            prompt = prompts.get(eval_type, prompts["music_standard_eval"])

            # Call Virtuals Compute API (OpenAI-compatible)
            response = client.chat.completions.create(
                model="moonshotai/kimi-k2-0905",
                messages=[
                    {"role": "system", "content": "You are the AIM MIO Evaluation Agent, a Phase 4 Evaluator on Virtuals ACP. You evaluate music tracks using the V4A framework (Truth, Neighbor, Fruit, Mammon, Service). Always respond in valid JSON format."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse the response
            result_text = response.choices[0].message.content
            try:
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                # If not valid JSON, wrap it
                result_data = {"feedback": result_text, "score": 70, "verdict": "PASS"}

            job_id = f"virtuals_{random.randint(10000,99999)}"

            return {
                "status": "completed",
                "job_id": job_id,
                "result": result_data,
                "message": f"Evaluation complete for '{track_title}' by {artist_name}.",
                "eval_type": eval_type,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error calling Virtuals API: {str(e)}",
            }

    async def get_job_status(self, job_id: str) -> dict:
        """Check job status. For Virtuals, results are returned immediately."""
        if not self.available or job_id.startswith("mock_") or job_id.startswith("local_"):
            return self._mock_status(job_id)

        # For real Virtuals jobs, results are returned in create_job
        return {"status": "completed", "message": "Job completed via Virtuals Compute API"}

    def _mock_status(self, job_id: str) -> dict:
        """Mock status for development."""
        scores = {
            "music_quick_eval": {"score": random.randint(60, 95), "feedback": "Good production quality. Catchy hook. Consider tightening the intro.", "verdict": "PASS"},
            "music_standard_eval": {"score": random.randint(55, 90), "feedback": "Solid track with good marketability. Production is clean. The bridge could be stronger.", "verdict": "PASS"},
            "music_portfolio_audit": {"score": random.randint(50, 85), "feedback": "Portfolio shows consistent quality. Growth trajectory is positive.", "verdict": "PASS"},
            "music_batch_eval": {"score": random.randint(60, 88), "feedback": "Batch complete. Top tracks identified. Genre distribution is healthy.", "verdict": "PASS"},
        }
        result = None
        for key, val in scores.items():
            if key in job_id:
                result = val
                break
        if not result:
            result = {"score": random.randint(60, 90), "feedback": "Evaluation complete. Track shows good potential.", "verdict": "PASS"}

        return {"status": "completed", "result": result, "mock": True}

    def _mock_job(self, track_title: str, artist_name: str, eval_type: str) -> dict:
        """Mock job for development (no Virtuals API key)."""
        job_id = f"mock_{eval_type}_{random.randint(1000,9999)}"
        return {
            "status": "completed",
            "job_id": job_id,
            "result": {
                "score": random.randint(60, 90),
                "feedback": f"Mock evaluation for '{track_title}' by {artist_name}. Type: {eval_type}.",
                "verdict": "PASS",
            },
            "message": f"Mock job completed for '{track_title}'. Type: {eval_type}.",
            "mock": True,
        }

    def get_service_tiers(self) -> list[dict]:
        """Return available evaluation service tiers."""
        return [
            {
                "id": "music_quick_eval",
                "name": "Quick Eval",
                "description": "Single track quality check (1-100 score)",
                "price_usd": 1,
                "duration": "~5 minutes",
                "icon": "⚡",
            },
            {
                "id": "music_standard_eval",
                "name": "Standard Eval",
                "description": "Detailed track analysis with feedback",
                "price_usd": 3,
                "duration": "~30 minutes",
                "icon": "📊",
            },
            {
                "id": "music_portfolio_audit",
                "name": "Portfolio Audit",
                "description": "Full artist portfolio analysis + recommendations",
                "price_usd": 8,
                "duration": "~2 hours",
                "icon": "🔍",
            },
            {
                "id": "music_batch_eval",
                "name": "Batch Eval",
                "description": "Evaluate up to 100 tracks at once",
                "price_usd": 15,
                "duration": "~10 hours",
                "icon": "📦",
            },
        ]


# Singleton
mio_job_service = MIOJobService()
