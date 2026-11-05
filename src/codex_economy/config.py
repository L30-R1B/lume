"""Versioned operational configuration; no credentials in configuration or prompts."""

import copy
import json
from .security import write_project

DEFAULT = {
    "version": 1,
    "context_bytes": 6000,
    "output_bytes": 10000000,
    "task_seconds": 300,
    "observed_token_budget": None,
    "profiles": {
        "default": {"model": None, "effort": None},
        "lean": {"model": None, "effort": "low"},
        "escalated": {"model": None, "effort": "high"},
    },
    "delegation": {"enabled": False, "max_agents": 2},
    "auxiliary": {"mode": "auto", "model": "jev-latest", "allow_paid": False},
}


def validate(config):
    import jsonschema

    config = copy.deepcopy(config)
    if isinstance(config, dict) and isinstance(config.get("auxiliary"), dict):
        config["auxiliary"].setdefault("allow_paid", False)

    def obj(properties):
        return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}

    profile = obj(
        {"model": {"type": ["string", "null"]}, "effort": {"enum": [None, "low", "medium", "high", "xhigh", "max"]}}
    )
    schema = obj(
        {
            "version": {"const": 1},
            "context_bytes": {"type": "integer", "minimum": 128, "maximum": 100000},
            "output_bytes": {"type": "integer", "minimum": 1024, "maximum": 100000000},
            "task_seconds": {"type": "integer", "minimum": 1, "maximum": 86400},
            "observed_token_budget": {"type": ["integer", "null"], "minimum": 1},
            "profiles": {"type": "object", "minProperties": 1, "additionalProperties": profile},
            "delegation": obj(
                {"enabled": {"type": "boolean"}, "max_agents": {"type": "integer", "minimum": 1, "maximum": 3}}
            ),
            "auxiliary": obj(
                {
                    "mode": {"enum": ["auto", "off"]},
                    "model": {"type": "string", "minLength": 1},
                    "allow_paid": {"type": "boolean"},
                }
            ),
        }
    )
    try:
        jsonschema.validate(config, schema)
    except jsonschema.ValidationError as error:
        raise ValueError("Invalid configuration: " + error.message) from None
    return config


def load(store):
    path = store.home / "config.json"
    if path.is_symlink():
        raise ValueError("Configuration cannot be a symlink")
    return validate(json.loads(path.read_text()) if path.exists() else copy.deepcopy(DEFAULT))


def update(store, patch):
    config = load(store)
    if not isinstance(patch, dict):
        raise ValueError("Configuration patch must be an object")
    for key, value in patch.items():
        if key in config and isinstance(value, dict) and isinstance(config[key], dict):
            config[key].update(value)
        else:
            config[key] = value
    validate(config)
    path = store.home / "config.json"
    write_project(
        store.home,
        "config.json",
        json.dumps(config, indent=2) + "\n",
        expected=path.read_text() if path.exists() else None,
    )
    return config


def secret(store, value=None, remove=False):
    path = store.home / "typesafe.key"
    if path.is_symlink():
        raise ValueError("Secret file cannot be a symlink")
    if remove:
        path.unlink(missing_ok=True)
    if value is not None:
        value = value.strip()
        if not 8 <= len(value) <= 512 or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise ValueError("Invalid credential encoding")
        write_project(store.home, "typesafe.key", value, expected=path.read_text() if path.exists() else None)
    import os

    return {
        "provider": "typesafe",
        "available": bool(os.environ.get("TYPESAFE_API_KEY") or path.exists()),
        "source": "environment" if os.environ.get("TYPESAFE_API_KEY") else "managed_file" if path.exists() else None,
        "secret_exposed": False,
    }
