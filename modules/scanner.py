import nmap
import time


class NetworkScanner:
    def __init__(self, rate_limit_delay=1, evasion=True):
        self.nm = nmap.PortScanner()
        self.rate_limit_delay = rate_limit_delay
        self.evasion = evasion

    def _evasion_flags(self):
        """Firewall/WAF evasion flags actually wired into the nmap calls
        (packet fragmentation, custom MTU, and random data-length padding),
        matching what the writeup describes."""
        if not self.evasion:
            return ""
        return " -f --mtu 24 --data-length 32"

    def host_discovery(self, target):
        """Performs initial host discovery using TCP SYN ping on common ports
        instead of ICMP, since most modern firewalls drop ICMP echo."""
        print(f"[*] Starting Host Discovery for: {target}")
        self.nm.scan(hosts=target, arguments="-sn -PS22,80,443")
        time.sleep(self.rate_limit_delay)
        return [host for host in self.nm.all_hosts() if self.nm[host].state() == "up"]

    def scan_ports(self, ip):
        """Scans for open ports on a specific live IP, with evasion flags."""
        print(f"[*] Scanning open ports for IP: {ip}")
        args = f"-p 1-1024{self._evasion_flags()}"
        self.nm.scan(hosts=ip, arguments=args)
        time.sleep(self.rate_limit_delay)

        open_ports = []
        if ip in self.nm.all_hosts():
            for proto in self.nm[ip].all_protocols():
                lport = self.nm[ip][proto].keys()
                for port in lport:
                    if self.nm[ip][proto][port]["state"] == "open":
                        open_ports.append(port)
        return open_ports

    def service_os_discovery(self, ip, ports):
        """Performs Service, Version, and OS detection (-sV -O), with evasion flags."""
        if not ports:
            return {}
        port_str = ",".join(map(str, ports))
        print(f"[*] Running Service & OS Detection on {ip} for ports: {port_str}")

        args = f"-sV -O{self._evasion_flags()}"
        self.nm.scan(hosts=ip, ports=port_str, arguments=args)
        time.sleep(self.rate_limit_delay)

        scan_results = {
            "os_match": self.nm[ip].get("osmatch", []),
            "services": {}
        }

        for proto in self.nm[ip].all_protocols():
            for port in self.nm[ip][proto].keys():
                scan_results["services"][port] = {
                    "name": self.nm[ip][proto][port]["name"],
                    "product": self.nm[ip][proto][port]["product"],
                    "version": self.nm[ip][proto][port]["version"],
                }
        return scan_results