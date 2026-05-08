from unittest.mock import patch, MagicMock
from app_filter import AppFilter
from config import Config


def test_no_exclusions():
    cfg = Config(path="/nonexistent")
    af = AppFilter(cfg)
    assert af.is_excluded("Terminal") is False
    assert af.is_excluded("Safari") is False


def test_with_exclusions():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("excluded_apps:\n  - Terminal\n  - iTerm2\n")
        f.flush()
        cfg = Config(path=f.name)
    os.unlink(f.name)
    af = AppFilter(cfg)
    assert af.is_excluded("Terminal") is True
    assert af.is_excluded("iTerm2") is True
    assert af.is_excluded("Safari") is False


def test_case_insensitive():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("excluded_apps:\n  - terminal\n")
        f.flush()
        cfg = Config(path=f.name)
    os.unlink(f.name)
    af = AppFilter(cfg)
    assert af.is_excluded("Terminal") is True
    assert af.is_excluded("TERMINAL") is True


def test_get_active_app_returns_string():
    af = AppFilter(Config(path="/nonexistent"))
    app_name = af.get_active_app()
    assert isinstance(app_name, str)
    assert len(app_name) > 0


# ────────────────────────────────────────────────────────────────────────────
# PR-J: Group C — should_process() with mocked frontmostApplication
#
# The existing tests verify is_excluded() and get_active_app() return type.
# These tests add: should_process() integration with a mocked frontmost app,
# covering excluded, allowed, case-insensitive, and None-app edge cases.
# ────────────────────────────────────────────────────────────────────────────


def _make_filter_with_excluded(excluded_apps):
    """Build an AppFilter whose config has the given excluded_apps list."""
    cfg = MagicMock(spec=Config)
    cfg.excluded_apps = excluded_apps
    return AppFilter(cfg)


def _patch_frontmost(app_name_or_none):
    """Return a patch context for app_filter.NSWorkspace that returns the given app name.

    If app_name_or_none is None, frontmostApplication() returns None (rare edge case).
    """
    mock_ws = MagicMock()
    if app_name_or_none is None:
        mock_ws.sharedWorkspace.return_value.frontmostApplication.return_value = None
    else:
        mock_app = MagicMock()
        mock_app.localizedName.return_value = app_name_or_none
        mock_ws.sharedWorkspace.return_value.frontmostApplication.return_value = mock_app
    return patch("app_filter.NSWorkspace", mock_ws)


def test_should_process_with_frontmost_excluded():
    """should_process() returns False when frontmost app is in the exclusion list."""
    af = _make_filter_with_excluded(["BlockedApp"])
    with _patch_frontmost("BlockedApp"):
        result = af.should_process()
    assert result is False, "should_process() must return False when app is excluded"


def test_should_process_with_frontmost_allowed():
    """should_process() returns True when frontmost app is not in the exclusion list."""
    af = _make_filter_with_excluded(["BlockedApp"])
    with _patch_frontmost("Notes"):
        result = af.should_process()
    assert result is True, "should_process() must return True when app is not excluded"


def test_should_process_case_insensitive_matching():
    """should_process() honors case-insensitive exclusion matching.

    Exclusion list has lowercase "blockedapp"; frontmost returns mixed-case "BlockedApp".
    is_excluded() lowercases both sides, so should_process() must return False.
    """
    af = _make_filter_with_excluded(["blockedapp"])
    with _patch_frontmost("BlockedApp"):
        result = af.should_process()
    assert result is False, (
        "should_process() must return False for case-insensitive match of excluded app"
    )


def test_should_process_no_frontmost_app():
    """should_process() returns True when frontmostApplication() returns None.

    get_active_app() returns '' when app is None. is_excluded('') returns False
    (empty string is not in any exclusion list), so should_process() allows through.
    This matches the graceful behavior during app launch / lock-screen transitions.
    """
    af = _make_filter_with_excluded(["BlockedApp"])
    with _patch_frontmost(None):
        result = af.should_process()
    assert result is True, (
        "should_process() must return True (allow) when no frontmost app is available"
    )
