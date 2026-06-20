#!/bin/bash
# Quick fix: Install Docker on Ubuntu 24.04

# Remove old versions
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Install prerequisites
apt update
apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify
docker --version
docker compose version

echo "✅ Docker installed!"
