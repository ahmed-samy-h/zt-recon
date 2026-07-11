#!/usr/bin/env bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0;m'

echo -e "${YELLOW}[*] Starting ZT-RECON Full Deployment & Installation...${NC}"

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[!] Please run this installation script as root (using sudo).${NC}"
  exit 1
fi

echo -e "${GREEN}[+] Step 1: Copying project files to /opt/zt-recon...${NC}"
mkdir -p /opt/zt-recon
cp -r * /opt/zt-recon/

echo -e "${GREEN}[+] Step 2: Installing Core Hacking Tools & Python dependencies...${NC}"
apt update -y

apt install -y nmap sqlmap dirsearch python3-pip python3-bs4 python3-rich wget unzip python3-full \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info fonts-liberation

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --break-system-packages 2>/dev/null
fi

echo -e "${GREEN}[+] Step 3: Installing ProjectDiscovery Nuclei v3.3.8...${NC}"
NUCLEI_URL="https://github.com/projectdiscovery/nuclei/releases/download/v3.3.8/nuclei_3.3.8_linux_amd64.zip"
wget -O /tmp/nuclei.zip "$NUCLEI_URL" 2>/dev/null
unzip -o /tmp/nuclei.zip -d /tmp/ >/dev/null

mv /tmp/nuclei /usr/local/bin/
chmod +x /usr/local/bin/nuclei
rm -f /tmp/nuclei.zip /tmp/README.md /tmp/LICENSE.md

echo -e "${GREEN}[+] Step 4: Downloading latest Nuclei OWASP templates...${NC}"
nuclei -update-templates -silent

echo -e "${GREEN}[+] Step 5: Configuring zt-recon as a global executable shortcut...${NC}"

sed -i '1s/^/#!\/usr\/bin\/env python3\n/' /opt/zt-recon/main.py 2>/dev/null

ln -sf /opt/zt-recon/main.py /usr/local/bin/zt-recon
chmod +x /opt/zt-recon/main.py
chmod +x /usr/local/bin/zt-recon

echo -e "${GREEN}[========== INSTALLATION COMPLETED SUCCESSFULLY ==========]${NC}"
echo -e "${YELLOW}[*] You can now run the tool globally from anywhere using: sudo zt-recon -t <Target>${NC}"
