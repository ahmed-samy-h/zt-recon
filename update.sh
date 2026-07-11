#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0;m'

echo -e "${YELLOW}[*] Updating ZT-RECON to the latest version...${NC}"

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[!] Please run this update script as root (using sudo).${NC}"
  exit 1
fi

if [ ! -d ".git" ]; then
  echo -e "${RED}[!] This does not look like a git clone of ZT-RECON.${NC}"
  echo -e "${RED}[!] Run this script from inside the folder you originally 'git clone'd.${NC}"
  exit 1
fi

echo -e "${GREEN}[+] Step 1: Pulling latest changes from GitHub...${NC}"
git pull origin main

echo -e "${GREEN}[+] Step 2: Re-running installation to sync files & dependencies...${NC}"
chmod +x install.sh
./install.sh

echo -e "${GREEN}[========== UPDATE COMPLETED SUCCESSFULLY ==========]${NC}"
echo -e "${YELLOW}[*] If this is your first update to v2.0.0, ZT-RECON switched AI providers${NC}"
echo -e "${YELLOW}[*] from Groq to Anthropic, so you will be asked for a NEW Anthropic API key${NC}"
echo -e "${YELLOW}[*] (sk-ant-...) the next time you run: sudo zt-recon -t <Target>${NC}"