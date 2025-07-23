#!/bin/bash

# Update system
sudo apt update
sudo apt upgrade -y

# Install Docker and Docker Compose
sudo apt install -y docker.io docker-compose

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group
sudo usermod -aG docker $USER

# Create application directory
sudo mkdir -p /var/www/letstrythis
sudo chown $USER:$USER /var/www/letstrythis

# Create necessary directories
mkdir -p /var/www/letstrythis/logs
mkdir -p /var/www/letstrythis/backup

# Generate SSH key for GitHub Actions
ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N ""

# Display the public key to add to GitHub
echo "Add this public key to your GitHub repository's deploy keys:"
cat ~/.ssh/github_actions.pub

# Create SSH config for GitHub Actions
cat > ~/.ssh/config << EOL
Host github-actions
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_actions
EOL

# Set proper permissions
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/github_actions
chmod 644 ~/.ssh/github_actions.pub

echo "VPS setup completed! Please add the SSH public key to your GitHub repository's deploy keys." 