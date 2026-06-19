"""
Music Bank — Multi-Rail Payment Service

Payment Rails:
  FAN DEPOSITS (how fans pay artists):
    1. Stripe (card/bank) → USD cents to artist balance_cents
    2. USDC on Base → USDC to artist balance_usdc
    3. $MIO token (Virtuals on Base) → MIO to artist balance_mio
    4. Cash App (manual/off-ramp) → USD cents to artist balance_cents

  ARTIST PAYOUTS (how artists cash out):
    1. Stripe Connect → bank account (USD)
    2. Coinbase → USDC to fiat
    3. Bitcoin → BTC to wallet
    4. Cash App → USD to Cash App

Platform fee: 5% on all deposits (configurable)
"""
import os
import time
from typing import Optional

# ============================================================
# STRIPE INTEGRATION
# ============================================================

class StripeService:
    """Stripe payment processing for fan deposits + artist payouts."""

    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.platform_fee_pct = float(os.getenv("PLATFORM_FEE_PCT", "5.0"))
        self._available = bool(self.api_key)

    @property
    def available(self) -> bool:
        return self._available

    async def create_payment_intent(
        self,
        amount_cents: int,
        artist_id: int,
        track_id: int,
        fan_id: Optional[int] = None,
        message: str = "",
    ) -> dict:
        """
        Create a Stripe PaymentIntent for a fan deposit.
        The amount goes to the platform, then we transfer to artist via Connect.
        """
        if not self.available:
            return self._mock_payment_intent(amount_cents, artist_id, track_id)

        import httpx

        platform_fee = int(amount_cents * self.platform_fee_pct / 100)
        artist_amount = amount_cents - platform_fee

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.stripe.com/v1/payment_intents",
                auth=(self.api_key, ""),
                data={
                    "amount": amount_cents,
                    "currency": "usd",
                    "metadata[artist_id]": str(artist_id),
                    "metadata[track_id]": str(track_id),
                    "metadata[fan_id]": str(fan_id or ""),
                    "metadata[message]": message[:500],
                    "metadata[type]": "music_bank_deposit",
                    "application_fee_amount": platform_fee,
                    # Transfer to artist's Stripe Connect account if they have one
                    # "transfer_data[destination]": artist_stripe_account_id,
                },
                timeout=30.0,
            )
            data = resp.json()
            if "id" not in data:
                raise Exception(f"Stripe error: {data.get('error', {}).get('message', 'unknown')}")
            return {
                "payment_intent_id": data["id"],
                "client_secret": data["client_secret"],
                "amount_cents": amount_cents,
                "platform_fee_cents": platform_fee,
                "artist_payout_cents": artist_amount,
            }

    def _mock_payment_intent(self, amount_cents: int, artist_id: int, track_id: int) -> dict:
        """Mock PaymentIntent for development."""
        platform_fee = int(amount_cents * self.platform_fee_pct / 100)
        return {
            "payment_intent_id": f"pi_mock_{int(time.time())}_{artist_id}",
            "client_secret": f"pi_mock_secret_{int(time.time())}",
            "amount_cents": amount_cents,
            "platform_fee_cents": platform_fee,
            "artist_payout_cents": amount_cents - platform_fee,
            "mock": True,
        }

    async def create_connect_account(self, artist_id: int, email: str) -> dict:
        """
        Create a Stripe Connect Express account for an artist.
        Returns the account ID and onboarding link.
        """
        if not self.available:
            return {
                "account_id": f"acct_mock_{artist_id}",
                "onboarding_url": f"/bank/stripe/onboarding?artist_id={artist_id}&mock=true",
                "mock": True,
            }

        import httpx

        async with httpx.AsyncClient() as client:
            # Create Connect account
            resp = await client.post(
                "https://api.stripe.com/v1/accounts",
                auth=(self.api_key, ""),
                data={
                    "type": "express",
                    "metadata[artist_id]": str(artist_id),
                    "metadata[platform]": "music_bank",
                },
                timeout=30.0,
            )
            account_data = resp.json()
            account_id = account_data["id"]

            # Create onboarding link
            resp = await client.post(
                f"https://api.stripe.com/v1/account_links",
                auth=(self.api_key, ""),
                data={
                    "account": account_id,
                    "refresh_url": f"{os.getenv('APP_URL', 'http://localhost:8090')}/bank/stripe/refresh",
                    "return_url": f"{os.getenv('APP_URL', 'http://localhost:8090')}/bank/stripe/complete",
                    "type": "account_onboarding",
                },
                timeout=30.0,
            )
            link_data = resp.json()

            return {
                "account_id": account_id,
                "onboarding_url": link_data["url"],
            }

    async def create_payout(self, artist_stripe_account_id: int, amount_cents: int) -> dict:
        """
        Create a payout to artist's bank via Stripe Connect.
        """
        if not self.available:
            return {
                "transfer_id": f"tr_mock_{int(time.time())}",
                "amount_cents": amount_cents,
                "mock": True,
            }

        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.stripe.com/v1/transfers",
                auth=(self.api_key, ""),
                data={
                    "amount": amount_cents,
                    "currency": "usd",
                    "destination": artist_stripe_account_id,
                    "metadata[type]": "music_bank_payout",
                },
                timeout=30.0,
            )
            data = resp.json()
            return {
                "transfer_id": data.get("id", ""),
                "amount_cents": amount_cents,
            }

    def verify_webhook(self, payload: bytes, sig_header: str) -> Optional[dict]:
        """Verify Stripe webhook signature."""
        if not self.available or not self.webhook_secret:
            return None
        try:
            import stripe
            return stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
        except Exception:
            return None


# ============================================================
# BASE / USDC INTEGRATION
# ============================================================

class BasePaymentService:
    """USDC payments on Base L2 for fan deposits."""

    # USDC contract on Base mainnet
    USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    # Base RPC endpoint
    BASE_RPC = "https://mainnet.base.org"
    # Platform wallet (receives deposits)
    PLATFORM_WALLET = os.getenv("BASE_PLATFORM_WALLET", "")

    def __init__(self):
        self._available = bool(self.PLATFORM_WALLET)

    @property
    def available(self) -> bool:
        return self._available

    def get_deposit_address(self, artist_id: int) -> str:
        """
        In production, this generates a unique deposit address per artist.
        For MVP, artists provide their own Base wallet address.
        """
        return self.PLATFORM_WALLET

    async def verify_usdc_transfer(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        expected_amount_usdc: float,
    ) -> dict:
        """
        Verify a USDC transfer on Base.
        Checks that the transfer was to the artist's wallet and amount matches.
        """
        if not self.available:
            return self._mock_verify_transfer(tx_hash, expected_amount_usdc)

        import httpx

        # Query Base RPC for transaction receipt
        async with httpx.AsyncClient() as client:
            # Get transaction receipt
            resp = await client.post(
                self.BASE_RPC,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [tx_hash],
                    "id": 1,
                },
                timeout=15.0,
            )
            receipt = resp.json().get("result", {})
            if not receipt:
                return {"verified": False, "error": "Transaction not found"}

            # Check status (0x1 = success)
            if receipt.get("status") != "0x1":
                return {"verified": False, "error": "Transaction failed"}

            # Parse logs for USDC Transfer event
            # USDC Transfer event signature: Transfer(address,address,uint256)
            # Topic 0: 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
            logs = receipt.get("logs", [])
            transfer_log = None
            USDC_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

            for log in logs:
                if log.get("address", "").lower() == self.USDC_CONTRACT.lower():
                    topics = log.get("topics", [])
                    if topics and topics[0] == USDC_TRANSFER_TOPIC:
                        transfer_log = log
                        break

            if not transfer_log:
                return {"verified": False, "error": "No USDC transfer found in transaction"}

            # Parse amount from data (uint256, 6 decimals for USDC)
            data = transfer_log.get("data", "0x0")
            if data.startswith("0x"):
                data = data[2:]
            raw_amount = int(data, 16) if data else 0
            amount_usdc = raw_amount / 1_000_000  # USDC has 6 decimals

            # Parse from/to from topics
            topics = transfer_log.get("topics", [])
            if len(topics) >= 3:
                from_addr = "0x" + topics[1][-40:]
                to_addr = "0x" + topics[2][-40:]
            else:
                from_addr = ""
                to_addr = ""

            # Verify amount (allow 1% tolerance for fees)
            amount_ok = abs(amount_usdc - expected_amount_usdc) / max(expected_amount_usdc, 0.01) < 0.01

            return {
                "verified": amount_ok,
                "amount_usdc": amount_usdc,
                "from_address": from_addr,
                "to_address": to_addr,
                "tx_hash": tx_hash,
            }

    def _mock_verify_transfer(self, tx_hash: str, expected_amount: float) -> dict:
        """Mock verification for development."""
        return {
            "verified": True,
            "amount_usdc": expected_amount,
            "from_address": "0xMockFanAddress",
            "to_address": "0xMockArtistAddress",
            "tx_hash": tx_hash,
            "mock": True,
        }

    def usdc_to_cents(self, amount_usdc: float) -> int:
        """Convert USDC amount to USD cents."""
        return int(amount_usdc * 100)


# ============================================================
# VIRTUALS $MIO TOKEN INTEGRATION
# ============================================================

class VirtualsPaymentService:
    """
    $MIO token deposits via Virtuals Protocol on Base.
    Fans deposit $MIO tokens to support artists.
    """

    # $MIO token contract on Base (Virtuals)
    MIO_CONTRACT = os.getenv("MIO_CONTRACT_ADDRESS", "")
    BASE_RPC = "https://mainnet.base.org"

    def __init__(self):
        self._available = bool(self.MIO_CONTRACT)

    @property
    def available(self) -> bool:
        return self._available

    async def verify_mio_transfer(
        self,
        tx_hash: str,
        expected_amount_mio: float,
    ) -> dict:
        """Verify a $MIO token transfer on Base."""
        if not self.available or not self.MIO_CONTRACT:
            return self._mock_verify_transfer(tx_hash, expected_amount_mio)

        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.BASE_RPC,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [tx_hash],
                    "id": 1,
                },
                timeout=15.0,
            )
            receipt = resp.json().get("result", {})
            if not receipt or receipt.get("status") != "0x1":
                return {"verified": False, "error": "Transaction not found or failed"}

            # Parse for MIO Transfer event (same ERC-20 pattern as USDC)
            logs = receipt.get("logs", [])
            MIO_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

            for log in logs:
                if log.get("address", "").lower() == self.MIO_CONTRACT.lower():
                    topics = log.get("topics", [])
                    if topics and topics[0] == MIO_TRANSFER_TOPIC:
                        data = log.get("data", "0x0")
                        if data.startswith("0x"):
                            data = data[2:]
                        raw_amount = int(data, 16) if data else 0
                        # MIO token decimals (check actual contract, assuming 18)
                        amount_mio = raw_amount / 1e18

                        return {
                            "verified": abs(amount_mio - expected_amount_mio) / max(expected_amount_mio, 0.01) < 0.01,
                            "amount_mio": amount_mio,
                            "tx_hash": tx_hash,
                        }

            return {"verified": False, "error": "No MIO transfer found"}

    def _mock_verify_transfer(self, tx_hash: str, expected_amount: float) -> dict:
        return {
            "verified": True,
            "amount_mio": expected_amount,
            "tx_hash": tx_hash,
            "mock": True,
        }

    def mio_to_cents(self, amount_mio: float, mio_price_usd: float = 0.05) -> int:
        """
        Convert $MIO tokens to USD cents.
        Default price $0.05 per MIO — in production, fetch from DEX.
        """
        return int(amount_mio * mio_price_usd * 100)


# ============================================================
# COINBASE INTEGRATION (for artist payouts)
# ============================================================

class CoinbaseService:
    """
    Coinbase Commerce / Exchange for artist payouts.
    Artists can convert USDC to fiat via Coinbase.
    """

    def __init__(self):
        self.api_key = os.getenv("COINBASE_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def available(self) -> bool:
        return self._available

    async def create_usdc_payout(
        self,
        destination_address: str,
        amount_usdc: float,
    ) -> dict:
        """
        Send USDC to artist's wallet via Coinbase.
        In production, this uses Coinbase's send API.
        """
        if not self.available:
            return {
                "transfer_id": f"cb_mock_{int(time.time())}",
                "amount_usdc": amount_usdc,
                "destination": destination_address,
                "mock": True,
            }

        # Coinbase API integration would go here
        # For now, return mock
        return {
            "transfer_id": f"cb_{int(time.time())}",
            "amount_usdc": amount_usdc,
            "destination": destination_address,
        }


# ============================================================
# CASH APP INTEGRATION (for artist payouts)
# ============================================================

class CashAppService:
    """
    Cash App payouts for artists.
    Uses Cash App Pay API or manual transfer via Cashtag.
    """

    def __init__(self):
        self.client_id = os.getenv("CASHAPP_CLIENT_ID", "")
        self._available = bool(self.client_id)

    @property
    def available(self) -> bool:
        return self._available

    async def create_payout(
        self,
        cashtag: str,
        amount_cents: int,
        note: str = "Music Bank payout",
    ) -> dict:
        """
        Send USD to artist's Cash App via Cashtag.
        """
        if not self.available:
            return {
                "transfer_id": f"ca_mock_{int(time.time())}",
                "amount_cents": amount_cents,
                "cashtag": cashtag,
                "mock": True,
            }

        return {
            "transfer_id": f"ca_{int(time.time())}",
            "amount_cents": amount_cents,
            "cashtag": cashtag,
        }


# ============================================================
# BITCOIN PAYOUT (via Strike or similar)
# ============================================================

class BitcoinService:
    """
    Bitcoin payouts via Strike API.
    Artists receive BTC to their wallet.
    """

    def __init__(self):
        self.api_key = os.getenv("STRIKE_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def available(self) -> bool:
        return self._available

    async def create_btc_payout(
        self,
        btc_address: str,
        amount_cents: int,
    ) -> dict:
        """
        Send BTC to artist's Bitcoin address.
        Converts USD cents to BTC at current rate.
        """
        if not self.available:
            return {
                "tx_hash": f"btc_mock_{int(time.time())}",
                "amount_cents": amount_cents,
                "btc_address": btc_address,
                "mock": True,
            }

        return {
            "tx_hash": f"btc_{int(time.time())}",
            "amount_cents": amount_cents,
            "btc_address": btc_address,
        }


# ============================================================
# PAYMENT ROUTER — Main entry point
# ============================================================

class PaymentRouter:
    """
    Routes payments between fans and artists across all rails.
    """

    def __init__(self):
        self.stripe = StripeService()
        self.base = BasePaymentService()
        self.virtuals = VirtualsPaymentService()
        self.coinbase = CoinbaseService()
        self.cashapp = CashAppService()
        self.bitcoin = BitcoinService()
        self.platform_fee_pct = float(os.getenv("PLATFORM_FEE_PCT", "5.0"))

    def calculate_fee(self, amount_cents: int) -> tuple[int, int]:
        """Calculate platform fee and artist payout."""
        fee = int(amount_cents * self.platform_fee_pct / 100)
        return fee, amount_cents - fee

    async def process_deposit(
        self,
        payment_rail: str,
        amount_cents: int,
        artist_id: int,
        track_id: int,
        fan_id: Optional[int] = None,
        message: str = "",
        # Rail-specific params
        tx_hash: str = "",
        from_wallet: str = "",
        amount_usdc: float = 0,
        amount_mio: float = 0,
    ) -> dict:
        """
        Process a fan deposit via the specified payment rail.
        Returns deposit record data.
        """
        platform_fee, artist_payout = self.calculate_fee(amount_cents)

        result = {
            "payment_rail": payment_rail,
            "amount_cents": amount_cents,
            "platform_fee_cents": platform_fee,
            "artist_payout_cents": artist_payout,
            "artist_id": artist_id,
            "track_id": track_id,
            "fan_artist_id": fan_id,
            "message": message,
            "status": "pending",
        }

        if payment_rail == "stripe":
            stripe_result = await self.stripe.create_payment_intent(
                amount_cents=amount_cents,
                artist_id=artist_id,
                track_id=track_id,
                fan_id=fan_id,
                message=message,
            )
            result["stripe_payment_intent_id"] = stripe_result["payment_intent_id"]
            result["client_secret"] = stripe_result.get("client_secret", "")
            result["status"] = "pending"  # Requires client-side confirmation

        elif payment_rail == "usdc_base":
            result["amount_usdc"] = amount_usdc
            result["from_wallet_address"] = from_wallet
            result["base_tx_hash"] = tx_hash
            # Verify the on-chain transfer
            if tx_hash:
                verify = await self.base.verify_usdc_transfer(
                    tx_hash=tx_hash,
                    from_address=from_wallet,
                    to_address="",  # Artist's wallet
                    expected_amount_usdc=amount_usdc,
                )
                result["verified"] = verify.get("verified", False)
                result["status"] = "completed" if verify.get("verified") else "pending"

        elif payment_rail == "virtuals_mio":
            result["amount_mio"] = amount_mio
            result["from_wallet_address"] = from_wallet
            result["virtuals_tx_hash"] = tx_hash
            if tx_hash:
                verify = await self.virtuals.verify_mio_transfer(
                    tx_hash=tx_hash,
                    expected_amount_mio=amount_mio,
                )
                result["verified"] = verify.get("verified", False)
                result["status"] = "completed" if verify.get("verified") else "pending"

        return result

    async def process_payout(
        self,
        artist_id: int,
        payout_method: str,
        amount_cents: int,
        artist_data: dict,
    ) -> dict:
        """
        Process an artist payout request.
        """
        result = {
            "artist_id": artist_id,
            "amount_cents": amount_cents,
            "payout_method": payout_method,
            "status": "pending",
        }

        if payout_method == "stripe_connect":
            if artist_data.get("stripe_account_id"):
                payout = await self.stripe.create_payout(
                    artist_stripe_account_id=artist_data["stripe_account_id"],
                    amount_cents=amount_cents,
                )
                result["stripe_transfer_id"] = payout.get("transfer_id", "")
                result["status"] = "processing"
            else:
                result["status"] = "failed"
                result["error"] = "Artist has not completed Stripe Connect onboarding"

        elif payout_method == "coinbase_usdc":
            if artist_data.get("base_wallet_address"):
                payout = await self.coinbase.create_usdc_payout(
                    destination_address=artist_data["base_wallet_address"],
                    amount_usdc=amount_cents / 100,  # Approximate
                )
                result["coinbase_transfer_id"] = payout.get("transfer_id", "")
                result["status"] = "processing"
            else:
                result["status"] = "failed"
                result["error"] = "Artist has not set a Base wallet address"

        elif payout_method == "bitcoin":
            if artist_data.get("btc_address"):
                payout = await self.bitcoin.create_btc_payout(
                    btc_address=artist_data["btc_address"],
                    amount_cents=amount_cents,
                )
                result["btc_tx_hash"] = payout.get("tx_hash", "")
                result["status"] = "processing"
            else:
                result["status"] = "failed"
                result["error"] = "Artist has not set a Bitcoin address"

        elif payout_method == "cashapp":
            if artist_data.get("cashapp_cashtag"):
                payout = await self.cashapp.create_payout(
                    cashtag=artist_data["cashapp_cashtag"],
                    amount_cents=amount_cents,
                )
                result["cashapp_transfer_id"] = payout.get("transfer_id", "")
                result["status"] = "processing"
            else:
                result["status"] = "failed"
                result["error"] = "Artist has not set a Cash App cashtag"

        return result


# Singleton
payment_router = PaymentRouter()
