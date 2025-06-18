from pathlib import Path
from typing import Any
import re


def set_env_vars(path: str = ".env", **updates: str) -> None:
    """Create or update environment variables in a .env style file."""
    env_path = Path(path)
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    env_map: dict[str, str] = {}
    for line in lines:
        if line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key.strip()] = value.strip()
    env_map.update({k: str(v) for k, v in updates.items()})
    new_lines = []
    processed = set()
    for line in lines:
        if line.strip().startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={env_map[key]}")
            processed.add(key)
        else:
            new_lines.append(f"{key}={env_map[key]}")
            processed.add(key)
    for key, value in env_map.items():
        if key not in processed:
            new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
