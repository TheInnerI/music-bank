#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Music Bank — Production Deployment Script
# Run this on a fresh Ubuntu 24.04 DO Droplet
# ═══════════════════════════════════════════════════════════

set -e

echo "🎵 Music Bank — Inner I Observer Deployment"
echo "============================================"

# ═══ Step 1: System Update ═══
echo ""
echo "📦 Step 1: Updating system..."
apt update && apt upgrade -y

# ═══ Step 2: Install Docker ═══
echo ""
echo "🐳 Step 2: Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    usermod -aG docker root
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# ═══ Step 3: Install Docker Compose ═══
echo ""
echo "🐳 Step 3: Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt install -y docker-compose-plugin
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# ═══ Step 4: Clone Music Bank ═══
echo ""
echo "📥 Step 4: Cloning Music Bank..."
cd /root
if [ -d "music-bank" ]; then
    cd music-bank && git pull
else
    git clone https://github.com/TheInnerI/music-bank.git
    cd music-bank
fi
echo "✅ Music Bank cloned/updated"

# ═══ Step 5: Configure Environment ═══
echo ""
echo "🔧 Step 5: Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your actual values:"
    echo "   nano .env"
    echo ""
    echo "   Required:"
    echo "   - MUSIC_BANK_SECRET (random string)"
    echo ""
    echo "   Optional (for payments):"
    echo "   - STRIPE_SECRET_KEY"
    echo "   - YOUTUBE_API_KEY"
    echo "   - SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET"
fi

# ═══ Step 6: Configure Caddy ═══
echo ""
echo "🌐 Step 6: Configuring Caddy..."
read -p "Enter your domain (e.g., musicbank.innerinetcompany.com): " DOMAIN
if [ -n "$DOMAIN" ]; then
    cat > Caddyfile << EOF
$DOMAIN {
    reverse_proxy music-bank:8090
    log {
        output file /data/access.log
    }
}
EOF
    echo "✅ Caddy configured for $DOMAIN"
fi

# ═══ Step 7: Build & Deploy ═══
echo ""
echo "🚀 Step 7: Building and deploying..."
docker compose build
docker compose up -d
echo "✅ Music Bank deployed!"

# ═══ Step 8: Verify ═══
echo ""
echo "🔍 Step 8: Verifying deployment..."
sleep 5
if curl -s http://localhost:8090/health | grep -q "healthy"; then
    echo "✅ Health check passed!"
else
    echo "⚠️  Health check failed. Check logs:"
    echo "   docker compose logs music-bank"
fi

# ═══ Step 9: Setup UFW Firewall ═══
echo ""
echo "🛡️ Step 9: Configuring firewall..."
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "✅ Firewall configured (ports 80, 443 open)"

# ═══ Step 10: Setup Auto-Renew SSL ═══
echo ""
echo "🔒 Step 10: SSL certificates..."
echo "Caddy will automatically obtain and renew Let's Encrypt certificates."
echo "Make sure your domain's A record points to this droplet's IP."

# ═══ Summary ═══
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎵 Music Bank Deployment Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📍 Access your instance:"
echo "   Local:  http://localhost:8090"
echo "   Public: https://$DOMAIN"
echo ""
echo "📊 Health check:"
echo "   curl https://$DOMAIN/health"
echo ""
echo "📋 Manage services:"
echo "   docker compose logs -f music-bank    # View logs"
echo "   docker compose restart music-bank    # Restart"
echo "   docker compose down                  # Stop"
echo ""
echo "🔧 To update:"
echo "   cd /root/music-bank && git pull && docker compose up -d --build"
echo ""
echo "═══════════════════════════════════════════════════════════"
