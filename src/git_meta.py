"""Detect repository metadata from git for plugin authorship.

Used when scaffolding a new plugin so that contributors get their own
attribution without hardcoding a name in the scaffolding code.
"""

import re
import subprocess
from functools import lru_cache

# SSH form: git@host:owner/repo(.git)?
_SSH_REMOTE = re.compile(r"^[^@]+@[^:]+:(?P<owner>[^/]+)/[^/]+?(?:\.git)?/?$")
# HTTPS form: https://host/owner/repo(.git)?
_HTTPS_REMOTE = re.compile(r"^https?://[^/]+/(?P<owner>[^/]+)/[^/]+?(?:\.git)?/?$")


def _run_git(*args: str, cwd: str | None = None) -> str | None:
    """Run a git command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def parse_remote_owner(url: str) -> str | None:
    """Extract the owner segment from a GitHub/GitLab/Bitbucket remote URL."""
    for pattern in (_SSH_REMOTE, _HTTPS_REMOTE):
        match = pattern.match(url.strip())
        if match:
            return match.group("owner")
    return None


@lru_cache(maxsize=1)
def get_author(cwd: str | None = None) -> str:
    """Return the plugin author for new plugins.

    Order of precedence:
    1. Owner segment of `git remote get-url origin` (for github.com/OWNER/repo).
    2. `git config user.name`.
    3. The sentinel string "unknown".

    The result is cached for the life of the process. Pass an explicit cwd
    only in tests.
    """
    remote_url = _run_git("remote", "get-url", "origin", cwd=cwd)
    if remote_url:
        owner = parse_remote_owner(remote_url)
        if owner:
            return owner
    config_name = _run_git("config", "user.name", cwd=cwd)
    if config_name:
        return config_name
    return "unknown"
