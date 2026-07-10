import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

CRTSH_URL = "https://crt.sh/?q=%25.{domain}&output=json"
DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$")


def is_domain(target):
    """Distinguishes a domain name from a raw IP so we only run
    subdomain enumeration when it actually makes sense."""
    ip_pattern = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
    if ip_pattern.match(target):
        return False
    return bool(DOMAIN_REGEX.match(target))


def discover_subdomains(domain, timeout=15):
    """Passive subdomain discovery via crt.sh certificate transparency logs.
    No active probing of the target here — purely OSINT."""
    print(f"[*] Enumerating subdomains for: {domain} (crt.sh)")
    found = set()

    try:
        resp = requests.get(CRTSH_URL.format(domain=domain), timeout=timeout)
        resp.raise_for_status()
        entries = resp.json()

        for entry in entries:
            name_value = entry.get("name_value", "")
            for line in name_value.split("\n"):
                clean = line.strip().lower().lstrip("*.")
                if clean.endswith(domain):
                    found.add(clean)

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"[!] Subdomain enumeration failed: {e}")

    found.add(domain)
    return sorted(found)


def _check_alive(subdomain, timeout=5):
    """Checks whether a subdomain responds over HTTPS or HTTP."""
    for scheme in ("https", "http"):
        url = f"{scheme}://{subdomain}"
        try:
            resp = requests.get(url, timeout=timeout, allow_redirects=True)
            return {
                "subdomain": subdomain,
                "url": url,
                "status_code": resp.status_code,
                "server": resp.headers.get("Server", "Unknown"),
            }
        except requests.exceptions.RequestException:
            continue
    return None


def filter_alive_subdomains(subdomains, max_workers=20):
    """Concurrently probes every discovered subdomain and returns only the
    ones that are actually up (alive), similar to an httpx-style filter."""
    print(f"[*] Probing {len(subdomains)} subdomains for liveness...")
    alive = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_check_alive, sd): sd for sd in subdomains}
        for future in as_completed(futures):
            result = future.result()
            if result:
                alive.append(result)

    alive.sort(key=lambda x: x["subdomain"])
    print(f"[+] {len(alive)}/{len(subdomains)} subdomains are alive.")
    return alive


def save_subdomain_files(target, all_subdomains, alive_subdomains, session_dir):
    """Persists both the raw and alive subdomain lists to disk BEFORE they
    are sent to the AI, so the user can review them independently."""
    import os

    os.makedirs(session_dir, exist_ok=True)
    all_path = os.path.join(session_dir, f"{target}_subdomains_all.txt")
    alive_path = os.path.join(session_dir, f"{target}_subdomains_alive.txt")

    with open(all_path, "w") as f:
        f.write("\n".join(all_subdomains))

    with open(alive_path, "w") as f:
        for entry in alive_subdomains:
            f.write(f"{entry['url']}  [{entry['status_code']}]  {entry['server']}\n")

    print(f"[+] Saved full subdomain list  -> {all_path}")
    print(f"[+] Saved alive subdomain list -> {alive_path}")
    return all_path, alive_path


def run_subdomain_recon(domain, session_dir):
    """Full pipeline: discover -> filter alive -> save to file -> return
    a compact summary ready to be handed to the AI engine."""
    all_subs = discover_subdomains(domain)
    alive_subs = filter_alive_subdomains(all_subs)
    save_subdomain_files(domain, all_subs, alive_subs, session_dir)

    return {
        "total_discovered": len(all_subs),
        "total_alive": len(alive_subs),
        "alive_subdomains": alive_subs,
    }