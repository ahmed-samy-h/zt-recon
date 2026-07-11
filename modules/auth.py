import os
import json
import stat

SYSTEM_CONFIG_DIR = "/opt/zt-recon"
SYSTEM_CONFIG_PATH = os.path.join(SYSTEM_CONFIG_DIR, ".anthropic_api_key")

FALLBACK_CONFIG_DIR = os.path.expanduser("~/.config/zt-recon")
FALLBACK_CONFIG_PATH = os.path.join(FALLBACK_CONFIG_DIR, ".anthropic_api_key")


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
    """Ensures a valid Anthropic API key is configured, stored system-wide so
    it survives across users/sudo sessions and is only ever asked for once."""
    config_path = _resolve_config_path()

    if not os.path.exists(config_path):
        print("[!] Anthropic API Key not found in configuration.")
        token = input("[+] Please enter your Anthropic API Key (sk-ant-...): ").strip()

        if not token.startswith("sk-ant-"):
            print("[!] Warning: Anthropic API keys normally start with 'sk-ant-'. Saving anyway.")

        config_data = {"ANTHROPIC_API_KEY": token}
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)
        print(f"[+] Token saved securely at {config_path}")
    else:
        with open(config_path, "r") as f:
            config_data = json.load(f)

    return config_data.get("ANTHROPIC_API_KEY")


def reset_auth():
    """Deletes the stored key so the user can re-enter a new one."""
    for path in (SYSTEM_CONFIG_PATH, FALLBACK_CONFIG_PATH):
        if os.path.exists(path):
            os.remove(path)