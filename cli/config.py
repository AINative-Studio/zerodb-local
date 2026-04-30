"""
Configuration management for ZeroDB CLI

Handles loading/saving of config, credentials, and environment settings.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


CONFIG_DIR = Path.home() / ".zerodb"
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def ensure_config_dir():
    """Ensure config directory exists"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """
    Load CLI configuration

    Returns:
        Configuration dictionary
    """
    ensure_config_dir()

    if not CONFIG_FILE.exists():
        return {
            'active_env': 'local',
            'project_id': None,
            'local_api_url': 'http://localhost:8000',
            'cloud_api_url': 'https://api.ainative.studio'
        }

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_config(config: Dict[str, Any]):
    """
    Save CLI configuration

    Args:
        config: Configuration dictionary
    """
    ensure_config_dir()

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_cloud_credentials() -> Optional[Dict[str, Any]]:
    """
    Get cloud credentials

    Returns:
        Credentials dictionary or None if not logged in
    """
    ensure_config_dir()

    if not CREDENTIALS_FILE.exists():
        return None

    with open(CREDENTIALS_FILE, 'r') as f:
        return json.load(f)


def save_cloud_credentials(credentials: Dict[str, Any]):
    """
    Save cloud credentials

    Args:
        credentials: Credentials dictionary from login
    """
    ensure_config_dir()

    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f, indent=2)

    # Set restrictive permissions (only owner can read)
    os.chmod(CREDENTIALS_FILE, 0o600)


def clear_cloud_credentials():
    """Clear cloud credentials (logout)"""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()


def get_project_id() -> Optional[str]:
    """Get current linked project ID"""
    config = load_config()
    return config.get('project_id')


def set_project_id(project_id: str):
    """Set current linked project ID"""
    config = load_config()
    config['project_id'] = project_id
    save_config(config)
