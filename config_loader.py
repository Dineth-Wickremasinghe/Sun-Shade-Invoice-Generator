import configparser
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.ini")

_DEFAULTS = {
    "name":    "Sun & Shade",
    "tagline": "Textile Invoice Generator",
    "address": "",
    "phone":   "",
    "email":   "",
}


def load_company_config() -> dict:
    """
    Load company details from config.ini.
    Falls back to defaults if the file or a key is missing.
    """
    config = configparser.ConfigParser()
    config.read(_CONFIG_PATH)

    section = config["company"] if "company" in config else {}
    return {key: section.get(key, default) for key, default in _DEFAULTS.items()}


if __name__ == "__main__":
    info = load_company_config()
    for k, v in info.items():
        print(f"{k:10}: {v}")