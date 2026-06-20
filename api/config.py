"""
Music Bank — Configuration
"""
import os

SECRET_KEY = os.getenv("MUSIC_BANK_SECRET", "music-bank-mvp-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72

# ═══ MIO Evaluator Agent (ACP) ═══
# Agent ID: 019ec475-d3e5-7e06-84e0-16f51fdea0b9
# Wallet: 0xf9fb5dfcbbef68cb470db0153e94ba4817625ceb
MIO_AGENT_WALLET = "0xf9fb5dfcbbef68cb470db0153e94ba4817625ceb"
MIO_AGENT_ID = "019ec475-d3e5-7e06-84e0-16f51fdea0b9"
MIO_AGENT_URL = "https://app.virtuals.io/acp/agents/019ec475-d3e5-7e06-84e0-16f51fdea0b9"

# MIO token contract on Base
MIO_CONTRACT_ADDRESS = os.getenv("MIO_CONTRACT_ADDRESS", "")

# Platform wallet for receiving USDC/MIO deposits
BASE_PLATFORM_WALLET = os.getenv("BASE_PLATFORM_WALLET", MIO_AGENT_WALLET)
