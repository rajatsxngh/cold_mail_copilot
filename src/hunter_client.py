import os
import requests

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "").strip()
HUNTER_BASE_URL = "https://api.hunter.io/v2"


def _split_name(full_name: str):
    """Split 'John Dennis' -> ('John', 'Dennis')."""
    parts = full_name.strip().split()
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def find_recruiter_email(full_name: str, domain: str) -> str | None:
    """Try to find an email using Hunter.

    1) First call Email Finder (recommended by Hunter).
    2) If nothing comes back, fall back to Domain Search and try to
       match the name there.
    """

    if not HUNTER_API_KEY:
        print("[Hunter] No API key configured – returning None")
        return None

    if not full_name or not domain:
        print("[Hunter] Missing name or domain – returning None")
        return None

    domain = domain.strip().lower()
    full_name = full_name.strip()
    first, last = _split_name(full_name)

    # -----------------------------
    # 1) Try Email Finder endpoint
    # -----------------------------
    params = {
        "domain": domain,
        "api_key": HUNTER_API_KEY,
    }

    # Hunter allows either (first_name + last_name) OR full_name
    if first and last:
        params["first_name"] = first
        params["last_name"] = last
    else:
        params["full_name"] = full_name

    try:
        resp = requests.get(f"{HUNTER_BASE_URL}/email-finder", params=params, timeout=10)
        print("[Hunter] Email Finder status:", resp.status_code)
        data = resp.json()
        print("[Hunter] Email Finder response (short):",
              {k: data.get(k) for k in ["data", "errors"] if k in data})

        if resp.status_code == 200:
            email = data.get("data", {}).get("email")
            if email:
                return email
    except Exception as e:
        print("[Hunter] Email Finder error:", e)

    # --------------------------------
    # 2) Fallback: Domain Search
    # --------------------------------
    try:
        ds_params = {
            "domain": domain,
            "api_key": HUNTER_API_KEY,
        }
        resp = requests.get(f"{HUNTER_BASE_URL}/domain-search", params=ds_params, timeout=10)
        print("[Hunter] Domain Search status:", resp.status_code)
        data = resp.json()
        print("[Hunter] Domain Search keys:", list(data.keys()))

        if resp.status_code != 200:
            return None

        emails = data.get("data", {}).get("emails", [])
        if not emails:
            return None

        # Try to match the name exactly
        target = full_name.lower()
        for e in emails:
            fn = (e.get("first_name") or "").strip()
            ln = (e.get("last_name") or "").strip()
            combined = (fn + " " + ln).strip().lower()
            if combined == target:
                return e.get("value")

        # If no exact match, just return the first email as a fallback
        return emails[0].get("value")

    except Exception as e:
        print("[Hunter] Domain Search error:", e)

    return None