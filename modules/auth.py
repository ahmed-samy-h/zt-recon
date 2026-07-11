import os
import json
import stat

SYSTEM_CONFIG_DIR = "/opt/zt-recon"
SYSTEM_CONFIG_PATH = os.path.join(SYSTEM_CONFIG_DIR, ".google_api_key")

FALLBACK_CONFIG_DIR = os.path.expanduser("~/.config/zt-recon")
FALLBACK_CONFIG_PATH = os.path.join(FALLBACK_CONFIG_DIR, ".google_api_key")


def _resolve_config_path():
    try:
        os.makedirs(SYSTEM_CONFIG_DIR, exist_ok=True)
        test_file = os.path.join(SYSTEM_CONFIG_DIR, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return SYSTEM_CONFIG_PATH
    except (PermissionError, OSError):
        os.makedirs(FALLBACK_CONFIG_DIR, exist_ok=True)
        return FALLBACK_CONFIG_PATH


def initialize_auth():
    """Ensures a valid Google AI Studio (Gemini) API key is configured,
    stored system-wide so it survives across users/sudo sessions and is
    only ever asked for once."""
    config_path = _resolve_config_path()

    if not os.path.exists(config_path):
        print("[!] Google AI Studio API Key not found in configuration.")
        token = input(
            "[+] Please enter your Google AI Studio API Key "
            "(get Token at aistudio.google.com, usually starts with 'AIzaSy'): "
        ).strip()

        # The STANDARD/correct Gemini Developer API key format starts with
        # "AIzaSy" (this is what the generativelanguage.googleapis.com REST
        # endpoint -- which the google-genai SDK talks to -- expects).
        #
        # A small number of Google accounts have recently (2026) started
        # generating keys with an "AQ." prefix instead, due to a known,
        # currently-unresolved issue on Google's side (see the Google AI
        # Developers Forum, e.g. discuss.ai.google.dev threads titled
        # "Gemini API key start from AQ"). Those "AQ." keys do NOT work
        # against the standard REST endpoint this tool uses and will fail
        # authentication -> warn specifically about that case instead of
        # treating "AQ" as the expected/normal prefix.
        if token.startswith("AQ"):
            print(
                "[!] Warning: this key starts with 'AQ.' -- that's a known-broken "
                "key format some Google accounts have recently been issued instead "
                "of the standard 'AIzaSy...' format, and it will likely fail "
                "authentication against this tool's API endpoint. If AI analysis "
                "calls fail with an auth error, regenerate the key at "
                "aistudio.google.com and confirm it starts with 'AIzaSy'."
            )
        elif not token.startswith("AIzaSy"):
            print(
                "[!] Warning: Google AI Studio API keys normally start with "
                "'AIzaSy'. Saving anyway, but double-check you copied the full key."
            )

        config_data = {"GOOGLE_API_KEY": token}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)
        print(f"[+] Token saved securely at {config_path}")
    else:
        with open(config_path, "r") as f:
            config_data = json.load(f)

    return config_data.get("GOOGLE_API_KEY")


def reset_auth():
    """Deletes the stored key so the user can re-enter a new one."""
    for path in (SYSTEM_CONFIG_PATH, FALLBACK_CONFIG_PATH):
        if os.path.exists(path):
            os.remove(path)