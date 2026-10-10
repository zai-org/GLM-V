"""Regression tests for the SSRF validation in fetch_ir.

Run from the scripts directory:
    python -m pytest tests/test_ssrf_validation.py -v
or standalone:
    python tests/test_ssrf_validation.py
"""

import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Stub the heavyweight optional dependency that fetch_ir imports at module
# level but that is irrelevant to URL validation (keeps these tests runnable
# in minimal environments, e.g. CI).
if "fitz" not in sys.modules:
    sys.modules["fitz"] = ModuleType("fitz")

from fetch_ir import _is_public_url  # noqa: E402


def test_parser_differential_bypass_blocked():
    """http://127.0.0.1\\@1.1.1.1 must be rejected even though urlparse
    extracts hostname 1.1.1.1 (urllib.request would connect to 127.0.0.1)."""
    ok, reason = _is_public_url(r"http://127.0.0.1\@1.1.1.1")
    assert not ok
    assert "disallowed" in reason


def test_plain_loopback_blocked():
    ok, reason = _is_public_url("http://127.0.0.1:6666/")
    assert not ok
    assert "non-public IP" in reason or "Localhost" in reason


def test_private_range_blocked():
    ok, _ = _is_public_url("http://192.168.1.10/report.pdf")
    assert not ok


def test_cloud_metadata_blocked():
    ok, _ = _is_public_url("http://169.254.169.254/latest/meta-data/")
    assert not ok


def test_backslash_variants_blocked():
    for url in (
        r"http://internal-host\@example.com",
        r"http://example.com\..\127.0.0.1",
    ):
        ok, _ = _is_public_url(url)
        assert not ok, url


def test_percent_encoded_backslash_blocked():
    ok, reason = _is_public_url("http://127.0.0.1%5c@example.com/x")
    assert not ok
    assert "disallowed" in reason


def test_whitespace_injection_blocked():
    ok, reason = _is_public_url("http://example.com\t@127.0.0.1")
    assert not ok
    assert "disallowed" in reason


def test_trailing_dot_host_blocked():
    """Trailing-dot hosts resolve inconsistently across parsers/resolvers."""
    ok, reason = _is_public_url("http://example.com./report.pdf")
    assert not ok
    assert "trailing dot" in reason


def test_non_http_scheme_blocked():
    ok, _ = _is_public_url("file:///etc/passwd")
    assert not ok
    ok, _ = _is_public_url("ftp://example.com/report.pdf")
    assert not ok


def test_valid_public_url_accepted_shape():
    """A syntactically clean public URL passes structural checks (network
    resolution may vary in sandboxed CI, so only assert rejection reasons
    are absent for structural rules)."""
    ok, reason = _is_public_url("https://example.com/report.pdf")
    # If DNS resolution is unavailable the call fails closed with a generic
    # error, which is still safe behavior.
    assert ok or "validation failed" in reason


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
