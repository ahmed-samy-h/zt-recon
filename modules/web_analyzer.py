import requests

def analyze_web_target(url):
    """Gathers HTTP headers, available methods, and core source code components."""
    print(f"[*] Gathering Web Intel from: {url}")
    results = {}
    try:

        response = requests.get(url, timeout=5)
        results["headers"] = dict(response.headers)
        results["status_code"] = response.status_code
        results["snippet"] = response.text[:1500]


        options_resp = requests.options(url, timeout=5)
        results["allowed_methods"] = options_resp.headers.get("Allow", "Not Disclosed")

    except requests.exceptions.RequestException as e:
        results["error"] = str(e)

    return results