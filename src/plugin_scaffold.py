"""Scaffold a new plugin in the marketplace.

Creates the directory tree, plugin.json, and an empty SKILL.md template.
The author is detected via git_meta.get_author() so contributors get their
own attribution automatically.
"""

import json
from pathlib import Path

from src.config import ROOT
from src.git_meta import get_author


def plugin_dir(plugin_name: str) -> Path:
    return ROOT / "plugins" / plugin_name


def skill_dir(plugin_name: str, skill_name: str) -> Path:
    return plugin_dir(plugin_name) / "skills" / skill_name


def write_plugin_manifest(
    plugin_name: str,
    description: str,
    author: str,
    version: str = "0.1.0",
) -> Path:
    """Write plugins/<name>/.claude-plugin/plugin.json. Returns the path."""
    path = plugin_dir(plugin_name) / ".claude-plugin" / "plugin.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": plugin_name,
        "description": description,
        "version": version,
        "author": {"name": author},
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def write_skill_stub(
    plugin_name: str,
    skill_name: str,
    description: str,
) -> Path:
    """Write plugins/<name>/skills/<skill>/SKILL.md with a minimal template."""
    path = skill_dir(plugin_name, skill_name) / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"---\n"
        f"name: {skill_name}\n"
        f"description: {description}\n"
        f"---\n"
        f"\n"
        f"# {skill_name}\n"
        f"\n"
        f"TODO: rules go here.\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def register_in_marketplace(
    plugin_name: str,
    description: str,
    version: str = "0.1.0",
) -> Path:
    """Append the plugin to .claude-plugin/marketplace.json. Idempotent."""
    path = ROOT / ".claude-plugin" / "marketplace.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    entry = {
        "name": plugin_name,
        "source": f"./plugins/{plugin_name}",
        "description": description,
        "version": version,
    }
    existing = [p for p in data["plugins"] if p["name"] == plugin_name]
    if existing:
        existing[0].update(entry)
    else:
        data["plugins"].append(entry)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def scaffold_plugin(
    plugin_name: str,
    skill_name: str,
    description: str,
    *,
    author: str | None = None,
    version: str = "0.1.0",
) -> dict[str, Path]:
    """Create a full plugin skeleton and register it in the marketplace.

    Returns a dict of {role: path} for the created files.
    """
    resolved_author = author or get_author()
    return {
        "manifest": write_plugin_manifest(
            plugin_name, description, resolved_author, version=version,
        ),
        "skill": write_skill_stub(plugin_name, skill_name, description),
        "marketplace": register_in_marketplace(
            plugin_name, description, version=version,
        ),
        "author_used": Path(resolved_author),  # surfaced for logging
    }
