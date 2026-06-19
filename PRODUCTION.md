# Music Bank — Production Setup Guide

## Prerequisites

1. **DO Droplet** — Ubuntu 24.04, 2 vCPU, 2GB RAM, 50GB SSD ($12/mo)
2. **Domain** — `musicbank.innerinetcompany.com` (subdomain of existing .com)
3. **Stripe Account** — For fan deposits (https://dashboard.stripe.com/register)

---

## Step 1: Create DO Droplet

1. Go to https://cloud.digitalocean.com/droplets/new
2. Choose **Ubuntu 24.04 LTS**
3. Select **Basic** plan — **$12/mo** (2 vCPU, 2GB RAM, 50GB SSD)
4. Choose datacenter region closest to you
5. Add SSH key (recommended) or use password
6. Click **Create Droplet**
7. Note the **IP address**

---

## Step 2: Configure DNS

In your WordPress.com DNS panel (for innerinetcompany.com):

Add an **A record**:
```
Type: A
Name: musicbank
Value: <YOUR_DROPLET_IP>
TTL: 3600
```

Wait 5-10 minutes for DNS propagation.

Verify:
```bash
dig musicbank.innerinetcompany.com +short
# Should return your droplet IP
```

---

## Step 3: Deploy Music Bank

SSH into your droplet:
```bash
ssh root@<YOUR_DROPLET_IP>
```

Run the deployment script:
```bash
curl -fsSL https://raw.githubusercontent.com/TheInnerI/music-bank/main/scripts/deploy.sh | bash
```

Or manually:
```bash
git clone https://github.com/TheInnerI/music-bank.git
cd music-bank
cp .env.example .env
nano .env  # Edit with your values
# Update Caddyfile with your domain
docker compose up -d --build
```

---

## Step 4: Configure Stripe

### 4a: Create Stripe Account
1. Go to https://dashboard.stripe.com/register
2. Complete identity verification
3. Get your API keys from https://dashboard.stripe.com/apikeys

### 4b: Add Stripe Keys to .env
```bash
nano /root/music-bank/.env

# Add:
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 4c: Configure Stripe Custom Domain ($10/mo)
1. Go to https://dashboard.stripe.com/settings/custom-domains
2. Click **Add your domain**
3. Enter: `payments.musicbank.innerinetcompany.com`
4. Stripe will give you DNS records to add:
   - CNAME: `payments.musicbank` → `hosted-checkout.stripecdn.com`
   - TXT: `_acme-challenge.payments.musicbank` → `<value from Stripe>`
5. Add these records in WordPress.com DNS panel
6. Wait for Stripe to verify (usually 5-15 minutes)

### 4d: Configure Stripe Webhook
1. Go to https://dashboard.stripe.com/webhooks
2. Click **Add endpoint**
3. URL: `https://musicbank.innerinetcompany.com/bank/webhook/stripe`
4. Events to listen for:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `transfer.created`
   - `transfer.failed`
5. Copy the **Signing secret** → `STRIPE_WEBHOOK_SECRET` in .env

### 4e: Restart Music Bank
```bash
cd /root/music-bank
docker compose restart music-bank
```

---

## Step 5: Verify Everything

```bash
# Health check
curl https://musicbank.innerinetcompany.com/health

# Should return:
# {"status":"healthy","service":"music-bank","version":"0.1.0"}

# Check Stripe is configured
curl https://musicbank.innerinetcompany.com/bank/
# Should load the bank dashboard
```

---

## Step 6: Import Your Music

1. Go to `https://musicbank.innerinetcompany.com/auth/register`
2. Create your artist account
3. Go to **Dashboard** → **Import**
4. Enter your YouTube channel: `@innerinetwork`
5. Click **Import from YouTube**
6. All 722 videos will import with auto-protection

---

## Monthly Costs Summary

| Service | Cost |
|---|---|
| DO Droplet (2 vCPU, 2GB, 50GB) | $12/mo |
| Stripe Custom Domain | $10/mo |
| Domain (innerinetcompany.com) | $0 (already owned) |
| SSL Certificate | $0 (Let's Encrypt via Caddy) |
| **Total** | **$22/mo** |

---

## Revenue Potential

| Source | Fee | Break-even |
|---|---|---|
| Fan deposits ($5 avg) | 5% platform fee | 44 deposits/mo = $22 |
| Sync licensing ($500 avg) | 10% platform fee | 1 deal every 2 months |
| Pro subscriptions | $9.99/mo | 3 artists on Pro |

**You break even with just 44 fan deposits per month.**

---

## Troubleshooting

### SSL not working
```bash
docker compose logs caddy
# Check for DNS propagation issues
dig musicbank.innerinetcompany.com +short
```

### Stripe payments failing
```bash
docker compose logs music-bank | grep -i stripe
# Check webhook configuration
```

### Import failing
```bash
docker compose logs music-bank | grep -i import
# Check API keys in .env
```

### Need to update
```bash
cd /root/music-bank
git pull
docker compose up -d --build
```
