"""Banking routes — multi-rail deposits, payouts, and artist payment settings."""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from api.database import get_db
from api.templates import respond
from api.routes.auth import get_current_artist
from api.payments import payment_router

router = APIRouter()


# ============================================================
# ARTIST BANK DASHBOARD
# ============================================================

@router.get("/")
async def bank_dashboard(request: Request):
    """Artist's bank dashboard — multi-rail balances and transactions."""
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    db = await get_db()
    try:
        # Get all balances
        cursor = await db.execute(
            "SELECT balance_cents, balance_usdc, balance_mio, balance_btc, "
            "stripe_account_id, stripe_onboarding_complete, "
            "eth_wallet_address, base_wallet_address, btc_address, cashapp_cashtag "
            "FROM artists WHERE id=?",
            (artist["id"],)
        )
        row = await cursor.fetchone()
        balances = dict(row) if row else {}

        # Get recent payment deposits
        cursor = await db.execute(
            "SELECT pd.*, t.title as track_title FROM payment_deposits pd "
            "LEFT JOIN tracks t ON pd.track_id=t.id "
            "WHERE pd.artist_id=? ORDER BY pd.created_at DESC LIMIT 20",
            (artist["id"],)
        )
        recent_deposits = [dict(r) for r in await cursor.fetchall()]

        # Get payout requests
        cursor = await db.execute(
            "SELECT * FROM payout_requests WHERE artist_id=? ORDER BY created_at DESC LIMIT 20",
            (artist["id"],)
        )
        payouts = [dict(r) for r in await cursor.fetchall()]

        # Get payout methods
        cursor = await db.execute(
            "SELECT * FROM artist_payout_methods WHERE artist_id=? AND is_active=1",
            (artist["id"],)
        )
        payout_methods = [dict(r) for r in await cursor.fetchall()]

        # Get legacy bank transactions
        cursor = await db.execute(
            "SELECT * FROM bank_transactions WHERE artist_id=? ORDER BY created_at DESC LIMIT 10",
            (artist["id"],)
        )
        transactions = [dict(r) for r in await cursor.fetchall()]
    finally:
        await db.close()

    return respond("artist/dashboard.html", {
        "request": request,
        "artist": artist,
        "balances": balances,
        "recent_deposits": recent_deposits,
        "payouts": payouts,
        "payout_methods": payout_methods,
        "transactions": transactions,
        "active_tab": "bank",
    })


# ============================================================
# PAYOUT METHOD MANAGEMENT
# ============================================================

@router.post("/payout-methods/add")
async def add_payout_method(request: Request):
    """Add a payout method for an artist."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    method_type = form.get("method_type", "")

    db = await get_db()
    try:
        if method_type == "stripe_connect":
            # Initiate Stripe Connect onboarding
            stripe_result = await payment_router.stripe.create_connect_account(
                artist_id=artist["id"],
                email=artist["email"],
            )
            await db.execute(
                "INSERT INTO artist_payout_methods (artist_id, method_type, stripe_account_id, is_default) VALUES (?,?,?,1)",
                (artist["id"], method_type, stripe_result["account_id"])
            )
            await db.execute(
                "UPDATE artists SET stripe_account_id=?, stripe_onboarding_complete=0 WHERE id=?",
                (stripe_result["account_id"], artist["id"])
            )
            await db.commit()
            return JSONResponse({
                "status": "ok",
                "method": "stripe_connect",
                "onboarding_url": stripe_result.get("onboarding_url", ""),
                "message": "Stripe Connect account created. Complete onboarding to receive payouts.",
            })

        elif method_type == "coinbase_usdc":
            wallet = form.get("wallet_address", "").strip()
            if not wallet or not wallet.startswith("0x"):
                raise HTTPException(status_code=400, detail="Valid Ethereum/Base wallet address required (0x...)")
            await db.execute(
                "INSERT INTO artist_payout_methods (artist_id, method_type, eth_wallet_address, base_wallet_address, is_default) VALUES (?,?,?,?,1)",
                (artist["id"], method_type, wallet, wallet)
            )
            await db.execute(
                "UPDATE artists SET eth_wallet_address=?, base_wallet_address=? WHERE id=?",
                (wallet, wallet, artist["id"])
            )
            await db.commit()
            return JSONResponse({
                "status": "ok",
                "method": "coinbase_usdc",
                "message": f"Base wallet {wallet[:10]}... added for USDC payouts.",
            })

        elif method_type == "bitcoin":
            btc_addr = form.get("btc_address", "").strip()
            if not btc_addr:
                raise HTTPException(status_code=400, detail="Bitcoin address required")
            await db.execute(
                "INSERT INTO artist_payout_methods (artist_id, method_type, btc_address, is_default) VALUES (?,?,?,1)",
                (artist["id"], method_type, btc_addr)
            )
            await db.execute("UPDATE artists SET btc_address=? WHERE id=?", (btc_addr, artist["id"]))
            await db.commit()
            return JSONResponse({
                "status": "ok",
                "method": "bitcoin",
                "message": f"Bitcoin address {btc_addr[:12]}... added for BTC payouts.",
            })

        elif method_type == "cashapp":
            cashtag = form.get("cashtag", "").strip().replace("$", "")
            if not cashtag:
                raise HTTPException(status_code=400, detail="Cash App cashtag required")
            await db.execute(
                "INSERT INTO artist_payout_methods (artist_id, method_type, cashapp_cashtag, is_default) VALUES (?,?,?,1)",
                (artist["id"], method_type, cashtag)
            )
            await db.execute("UPDATE artists SET cashapp_cashtag=? WHERE id=?", (cashtag, artist["id"]))
            await db.commit()
            return JSONResponse({
                "status": "ok",
                "method": "cashapp",
                "message": f"Cash App ${cashtag} added for USD payouts.",
            })

        else:
            raise HTTPException(status_code=400, detail=f"Unknown payout method: {method_type}")
    finally:
        await db.close()


# ============================================================
# FAN DEPOSIT ENDPOINTS (Multi-Rail)
# ============================================================

@router.post("/deposit/stripe")
async def deposit_stripe(request: Request):
    """
    Create a Stripe PaymentIntent for a fan deposit.
    Returns client_secret for Stripe.js on frontend.
    """
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in to deposit")

    form = await request.form()
    track_id = int(form.get("track_id", 0))
    amount_usd = float(form.get("amount", 0))
    message = form.get("message", "").strip()

    if amount_usd < 1:
        raise HTTPException(status_code=400, detail="Minimum deposit is $1.00")

    amount_cents = int(amount_usd * 100)

    db = await get_db()
    try:
        # Get track and artist
        cursor = await db.execute("SELECT artist_id FROM tracks WHERE id=?", (track_id,))
        track_row = await cursor.fetchone()
        if not track_row:
            raise HTTPException(status_code=404, detail="Track not found")

        recipient_id = track_row["artist_id"]
        if recipient_id == current_artist["id"]:
            raise HTTPException(status_code=400, detail="Cannot deposit to your own track")

        # Process via payment router
        deposit_data = await payment_router.process_deposit(
            payment_rail="stripe",
            amount_cents=amount_cents,
            artist_id=recipient_id,
            track_id=track_id,
            fan_id=current_artist["id"],
            message=message,
        )

        # Record deposit
        await db.execute(
            "INSERT INTO payment_deposits "
            "(artist_id, track_id, fan_artist_id, amount_cents, payment_rail, "
            "stripe_payment_intent_id, platform_fee_cents, artist_payout_cents, message, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (recipient_id, track_id, current_artist["id"], amount_cents, "stripe",
             deposit_data["stripe_payment_intent_id"],
             deposit_data["platform_fee_cents"], deposit_data["artist_payout_cents"],
             message, deposit_data["status"])
        )
        await db.commit()

        return JSONResponse({
            "status": "ok",
            "client_secret": deposit_data.get("client_secret", ""),
            "payment_intent_id": deposit_data["stripe_payment_intent_id"],
            "amount_cents": amount_cents,
            "platform_fee_cents": deposit_data["platform_fee_cents"],
            "artist_payout_cents": deposit_data["artist_payout_cents"],
        })
    finally:
        await db.close()


@router.post("/deposit/stripe/confirm")
async def confirm_stripe_deposit(request: Request):
    """
    Confirm a Stripe deposit after client-side payment.
    Called by frontend after Stripe.js confirms the payment.
    """
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    payment_intent_id = form.get("payment_intent_id", "")

    db = await get_db()
    try:
        # Find the deposit
        cursor = await db.execute(
            "SELECT * FROM payment_deposits WHERE stripe_payment_intent_id=? AND fan_artist_id=?",
            (payment_intent_id, current_artist["id"])
        )
        deposit = await cursor.fetchone()
        if not deposit:
            raise HTTPException(status_code=404, detail="Deposit not found")

        deposit = dict(deposit)

        # Credit artist's balance
        await db.execute(
            "UPDATE artists SET balance_cents = balance_cents + ?, total_earnings_cents = total_earnings_cents + ? WHERE id=?",
            (deposit["artist_payout_cents"], deposit["artist_payout_cents"], deposit["artist_id"])
        )

        # Update track earnings
        if deposit["track_id"]:
            await db.execute(
                "UPDATE tracks SET earnings_cents = earnings_cents + ?, deposits = deposits + 1 WHERE id=?",
                (deposit["artist_payout_cents"], deposit["track_id"])
            )

        # Mark deposit completed
        await db.execute(
            "UPDATE payment_deposits SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?",
            (deposit["id"],)
        )

        # Record platform fee
        await db.execute(
            "INSERT INTO platform_fees (deposit_id, fee_cents) VALUES (?,?)",
            (deposit["id"], deposit["platform_fee_cents"])
        )

        # Record bank transaction
        await db.execute(
            "INSERT INTO bank_transactions (artist_id, amount_cents, transaction_type, description) VALUES (?,?,?,?)",
            (deposit["artist_id"], deposit["artist_payout_cents"], "deposit", f"Stripe deposit on track #{deposit['track_id']}")
        )

        await db.commit()
        return JSONResponse({"status": "ok", "message": "Deposit completed!"})
    finally:
        await db.close()


@router.post("/deposit/usdc")
async def deposit_usdc(request: Request):
    """
    Deposit USDC on Base to support an artist.
    Fan provides tx_hash of their USDC transfer to the artist's wallet.
    """
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in to deposit")

    form = await request.form()
    track_id = int(form.get("track_id", 0))
    amount_usdc = float(form.get("amount_usdc", 0))
    tx_hash = form.get("tx_hash", "").strip()
    from_wallet = form.get("from_wallet", "").strip()
    message = form.get("message", "").strip()

    if amount_usdc < 1:
        raise HTTPException(status_code=400, detail="Minimum deposit is 1 USDC")

    if not tx_hash or not tx_hash.startswith("0x"):
        raise HTTPException(status_code=400, detail="Valid Base transaction hash required (0x...)")

    # Convert USDC to cents (1 USDC = $1 = 100 cents)
    amount_cents = int(amount_usdc * 100)

    db = await get_db()
    try:
        cursor = await db.execute("SELECT artist_id FROM tracks WHERE id=?", (track_id,))
        track_row = await cursor.fetchone()
        if not track_row:
            raise HTTPException(status_code=404, detail="Track not found")

        recipient_id = track_row["artist_id"]
        if recipient_id == current_artist["id"]:
            raise HTTPException(status_code=400, detail="Cannot deposit to your own track")

        # Process deposit
        deposit_data = await payment_router.process_deposit(
            payment_rail="usdc_base",
            amount_cents=amount_cents,
            artist_id=recipient_id,
            track_id=track_id,
            fan_id=current_artist["id"],
            message=message,
            tx_hash=tx_hash,
            from_wallet=from_wallet,
            amount_usdc=amount_usdc,
        )

        # Record deposit
        await db.execute(
            "INSERT INTO payment_deposits "
            "(artist_id, track_id, fan_artist_id, amount_cents, amount_usdc, payment_rail, "
            "base_tx_hash, from_wallet_address, platform_fee_cents, artist_payout_cents, message, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (recipient_id, track_id, current_artist["id"], amount_cents, amount_usdc, "usdc_base",
             tx_hash, from_wallet,
             deposit_data["platform_fee_cents"], deposit_data["artist_payout_cents"],
             message, deposit_data["status"])
        )

        # If verified, credit immediately
        if deposit_data.get("verified"):
            await db.execute(
                "UPDATE artists SET balance_usdc = balance_usdc + ?, balance_cents = balance_cents + ? WHERE id=?",
                (amount_usdc - (deposit_data["platform_fee_cents"] / 100), deposit_data["artist_payout_cents"], recipient_id)
            )
            if track_id:
                await db.execute(
                    "UPDATE tracks SET earnings_cents = earnings_cents + ?, deposits = deposits + 1 WHERE id=?",
                    (deposit_data["artist_payout_cents"], track_id)
                )

        await db.commit()
        return JSONResponse({
            "status": "ok",
            "verified": deposit_data.get("verified", False),
            "amount_usdc": amount_usdc,
            "artist_payout_cents": deposit_data["artist_payout_cents"],
            "message": "USDC deposit verified and credited!" if deposit_data.get("verified") else "USDC deposit recorded. Verifying on-chain...",
        })
    finally:
        await db.close()


@router.post("/deposit/mio")
async def deposit_mio(request: Request):
    """
    Deposit $MIO tokens (Virtuals on Base) to support an artist.
    """
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in to deposit")

    form = await request.form()
    track_id = int(form.get("track_id", 0))
    amount_mio = float(form.get("amount_mio", 0))
    tx_hash = form.get("tx_hash", "").strip()
    from_wallet = form.get("from_wallet", "").strip()
    message = form.get("message", "").strip()

    if amount_mio < 10:
        raise HTTPException(status_code=400, detail="Minimum deposit is 10 $MIO")

    if not tx_hash or not tx_hash.startswith("0x"):
        raise HTTPException(status_code=400, detail="Valid Base transaction hash required")

    # Convert MIO to cents
    amount_cents = payment_router.virtuals.mio_to_cents(amount_mio)

    db = await get_db()
    try:
        cursor = await db.execute("SELECT artist_id FROM tracks WHERE id=?", (track_id,))
        track_row = await cursor.fetchone()
        if not track_row:
            raise HTTPException(status_code=404, detail="Track not found")

        recipient_id = track_row["artist_id"]
        if recipient_id == current_artist["id"]:
            raise HTTPException(status_code=400, detail="Cannot deposit to your own track")

        deposit_data = await payment_router.process_deposit(
            payment_rail="virtuals_mio",
            amount_cents=amount_cents,
            artist_id=recipient_id,
            track_id=track_id,
            fan_id=current_artist["id"],
            message=message,
            tx_hash=tx_hash,
            from_wallet=from_wallet,
            amount_mio=amount_mio,
        )

        await db.execute(
            "INSERT INTO payment_deposits "
            "(artist_id, track_id, fan_artist_id, amount_cents, amount_mio, payment_rail, "
            "virtuals_tx_hash, from_wallet_address, platform_fee_cents, artist_payout_cents, message, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (recipient_id, track_id, current_artist["id"], amount_cents, amount_mio, "virtuals_mio",
             tx_hash, from_wallet,
             deposit_data["platform_fee_cents"], deposit_data["artist_payout_cents"],
             message, deposit_data["status"])
        )

        if deposit_data.get("verified"):
            await db.execute(
                "UPDATE artists SET balance_mio = balance_mio + ?, balance_cents = balance_cents + ? WHERE id=?",
                (amount_mio, deposit_data["artist_payout_cents"], recipient_id)
            )
            if track_id:
                await db.execute(
                    "UPDATE tracks SET earnings_cents = earnings_cents + ?, deposits = deposits + 1 WHERE id=?",
                    (deposit_data["artist_payout_cents"], track_id)
                )

        await db.commit()
        return JSONResponse({
            "status": "ok",
            "verified": deposit_data.get("verified", False),
            "amount_mio": amount_mio,
            "artist_payout_cents": deposit_data["artist_payout_cents"],
            "message": "$MIO deposit verified and credited!" if deposit_data.get("verified") else "$MIO deposit recorded. Verifying on-chain...",
        })
    finally:
        await db.close()


# ============================================================
# SYNC LICENSING MARKETPLACE
# ============================================================

@router.get("/licensing")
async def licensing_marketplace(request: Request):
    """Browse tracks available for sync licensing."""
    current_artist = await get_current_artist(request)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT t.*, a.display_name as artist_name, a.username as artist_username "
            "FROM tracks t JOIN artists a ON t.artist_id=a.id "
            "WHERE t.sync_available=1 AND t.is_published=1 "
            "ORDER BY t.plays DESC LIMIT 50"
        )
        tracks = [dict(t) for t in await cursor.fetchall()]
    finally:
        await db.close()

    from api.copyright import SYNC_CATEGORIES
    return respond("legal/licensing.html", {
        "request": request,
        "tracks": tracks,
        "sync_categories": SYNC_CATEGORIES,
        "current_artist": current_artist,
    })


@router.post("/licensing/inquiry")
async def licensing_inquiry(request: Request):
    """Submit a licensing inquiry for a track."""
    current_artist = await get_current_artist(request)
    if not current_artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO licensing_deals "
            "(track_id, licensee_name, licensee_email, license_type, "
            "intended_use, budget_range, status) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                int(form.get("track_id", 0)),
                form.get("licensee_name", ""),
                form.get("licensee_email", ""),
                form.get("license_type", "sync"),
                form.get("intended_use", ""),
                form.get("budget_range", ""),
                "inquiry",
            )
        )
        await db.commit()
    finally:
        await db.close()

    return JSONResponse({
        "status": "ok",
        "message": "Licensing inquiry submitted. The artist will be notified.",
    })


# ============================================================
# ARTIST PAYOUT ENDPOINTS
# ============================================================

@router.post("/payout/request")
async def request_payout(request: Request):
    """Request a payout via the artist's preferred method."""
    artist = await get_current_artist(request)
    if not artist:
        raise HTTPException(status_code=401, detail="Must be logged in")

    form = await request.form()
    payout_method = form.get("payout_method", "stripe_connect")
    amount_usd = float(form.get("amount", 0))
    amount_cents = int(amount_usd * 100)

    if amount_cents < 500:
        raise HTTPException(status_code=400, detail="Minimum payout is $5.00")

    # Check balance
    if payout_method == "stripe_connect" and amount_cents > artist.get("balance_cents", 0):
        raise HTTPException(status_code=400, detail=f"Insufficient USD balance. Available: ${artist.get('balance_cents', 0)/100:.2f}")
    if payout_method == "coinbase_usdc" and amount_cents > artist.get("balance_cents", 0):
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Available: ${artist.get('balance_cents', 0)/100:.2f}")

    db = await get_db()
    try:
        # Process payout
        payout_result = await payment_router.process_payout(
            artist_id=artist["id"],
            payout_method=payout_method,
            amount_cents=amount_cents,
            artist_data=artist,
        )

        # Record payout request
        await db.execute(
            "INSERT INTO payout_requests "
            "(artist_id, amount_cents, payout_method, status, stripe_transfer_id, coinbase_transfer_id, btc_tx_hash, cashapp_transfer_id) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (artist["id"], amount_cents, payout_method, payout_result["status"],
             payout_result.get("stripe_transfer_id", ""),
             payout_result.get("coinbase_transfer_id", ""),
             payout_result.get("btc_tx_hash", ""),
             payout_result.get("cashapp_transfer_id", ""))
        )

        # Deduct from balance
        if payout_result["status"] == "processing":
            await db.execute(
                "UPDATE artists SET balance_cents = balance_cents - ? WHERE id=?",
                (amount_cents, artist["id"])
            )
            await db.execute(
                "INSERT INTO bank_transactions (artist_id, amount_cents, transaction_type, description) VALUES (?,?,?,?)",
                (artist["id"], -amount_cents, "payout", f"Payout via {payout_method}: ${amount_usd:.2f}")
            )

        await db.commit()

        if payout_result["status"] == "failed":
            return JSONResponse({
                "status": "error",
                "message": payout_result.get("error", "Payout failed"),
            })

        return JSONResponse({
            "status": "ok",
            "payout_method": payout_method,
            "amount_cents": amount_cents,
            "message": f"Payout of ${amount_usd:.2f} via {payout_method} initiated!",
        })
    finally:
        await db.close()


# ============================================================
# STRIPE WEBHOOK
# ============================================================

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks for payment confirmations."""
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = payment_router.stripe.verify_webhook(body, sig_header)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]
        payment_intent_id = pi["id"]

        db = await get_db()
        try:
            # Find and complete the deposit
            cursor = await db.execute(
                "SELECT * FROM payment_deposits WHERE stripe_payment_intent_id=? AND status='pending'",
                (payment_intent_id,)
            )
            deposit = await cursor.fetchone()
            if deposit:
                deposit = dict(deposit)
                # Credit artist
                await db.execute(
                    "UPDATE artists SET balance_cents = balance_cents + ?, total_earnings_cents = total_earnings_cents + ? WHERE id=?",
                    (deposit["artist_payout_cents"], deposit["artist_payout_cents"], deposit["artist_id"])
                )
                await db.execute(
                    "UPDATE payment_deposits SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?",
                    (deposit["id"],)
                )
                await db.execute(
                    "INSERT INTO platform_fees (deposit_id, fee_cents) VALUES (?,?)",
                    (deposit["id"], deposit["platform_fee_cents"])
                )
                await db.commit()
        finally:
            await db.close()

    return JSONResponse({"status": "ok"})


# ============================================================
# STRIPE CONNECT CALLBACKS
# ============================================================

@router.get("/stripe/onboarding")
async def stripe_onboarding(request: Request):
    """Start Stripe Connect onboarding for an artist."""
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    result = await payment_router.stripe.create_connect_account(
        artist_id=artist["id"],
        email=artist["email"],
    )

    if result.get("onboarding_url"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=result["onboarding_url"])

    return JSONResponse({"status": "ok", "message": "Stripe account already set up"})


@router.get("/stripe/complete")
async def stripe_onboarding_complete(request: Request):
    """Stripe Connect onboarding complete callback."""
    artist = await get_current_artist(request)
    if not artist:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")

    db = await get_db()
    try:
        await db.execute(
            "UPDATE artists SET stripe_onboarding_complete=1 WHERE id=?",
            (artist["id"],)
        )
        await db.commit()
    finally:
        await db.close()

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/bank/?stripe=connected")
