"""Tests for git remote author detection."""

from src.git_meta import parse_remote_owner


def test_parse_https_github():
    assert parse_remote_owner("https://github.com/BillSchumacher/claude_stuff.git") == "BillSchumacher"


def test_parse_https_github_no_suffix():
    assert parse_remote_owner("https://github.com/BillSchumacher/claude_stuff") == "BillSchumacher"


def test_parse_ssh_github():
    assert parse_remote_owner("git@github.com:BillSchumacher/claude_stuff.git") == "BillSchumacher"


def test_parse_ssh_github_no_suffix():
    assert parse_remote_owner("git@github.com:BillSchumacher/claude_stuff") == "BillSchumacher"


def test_parse_https_gitlab():
    assert parse_remote_owner("https://gitlab.com/foo/bar.git") == "foo"


def test_parse_ssh_gitlab():
    assert parse_remote_owner("git@gitlab.com:foo/bar.git") == "foo"


def test_parse_self_hosted_ssh():
    assert parse_remote_owner("git@git.internal.example.com:team-a/repo.git") == "team-a"


def test_parse_unrelated_string_returns_none():
    assert parse_remote_owner("not a url") is None


def test_parse_empty_returns_none():
    assert parse_remote_owner("") is None
