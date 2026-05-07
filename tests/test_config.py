import os
import tempfile
from config import Config


def test_default_config():
    cfg = Config(path="/nonexistent/path/config.yaml")
    assert cfg.enabled is True
    assert cfg.hotkey == "ctrl+shift+space"
    assert cfg.excluded_apps == []
    assert "gg" in cfg.ignore_words
    assert cfg.log_errors is True


def test_load_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("enabled: false\nexcluded_apps:\n  - Terminal\nignore_words:\n  - test\n")
        f.flush()
        cfg = Config(path=f.name)
    os.unlink(f.name)
    assert cfg.enabled is False
    assert cfg.excluded_apps == ["Terminal"]
    assert "test" in cfg.ignore_words


def test_partial_config_uses_defaults():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("enabled: false\n")
        f.flush()
        cfg = Config(path=f.name)
    os.unlink(f.name)
    assert cfg.enabled is False
    assert cfg.hotkey == "ctrl+shift+space"
    assert cfg.ignore_words == Config.DEFAULT_IGNORE_WORDS


def test_save_creates_file():
    import tempfile, os
    path = os.path.join(tempfile.mkdtemp(), "config.yaml")
    cfg = Config(path=path)
    cfg.set_enabled(False)
    assert os.path.exists(path)
    cfg2 = Config(path=path)
    assert cfg2.enabled is False
    os.unlink(path)


def test_set_excluded_apps():
    import tempfile, os
    path = os.path.join(tempfile.mkdtemp(), "config.yaml")
    cfg = Config(path=path)
    cfg.set_excluded_apps(["Terminal", "iTerm2"])
    cfg2 = Config(path=path)
    assert cfg2.excluded_apps == ["Terminal", "iTerm2"]
    os.unlink(path)


def test_set_ignore_words():
    import tempfile, os
    path = os.path.join(tempfile.mkdtemp(), "config.yaml")
    cfg = Config(path=path)
    cfg.set_ignore_words(["test", "foo"])
    cfg2 = Config(path=path)
    assert cfg2.ignore_words == ["test", "foo"]
    os.unlink(path)


def test_new_properties_defaults():
    cfg = Config(path="/nonexistent")
    assert cfg.show_notifications is False
    assert cfg.launch_at_login is False


def test_observer_called_on_change():
    import tempfile, os
    path = os.path.join(tempfile.mkdtemp(), "config.yaml")
    cfg = Config(path=path)
    calls = []
    cfg.add_observer(lambda: calls.append(1))
    cfg.set_enabled(False)
    assert len(calls) == 1
    cfg.set_ignore_words(["x"])
    assert len(calls) == 2
    os.unlink(path)


def test_multiple_observers():
    import tempfile, os
    path = os.path.join(tempfile.mkdtemp(), "config.yaml")
    cfg = Config(path=path)
    a, b = [], []
    cfg.add_observer(lambda: a.append(1))
    cfg.add_observer(lambda: b.append(1))
    cfg.set_enabled(True)
    assert len(a) == 1
    assert len(b) == 1
    os.unlink(path)


def test_debug_default_is_false():
    cfg = Config(path="/nonexistent/path/config.yaml")
    assert cfg.debug is False


def test_debug_key_loads_from_yaml():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("debug: true\n")
        f.flush()
        cfg = Config(path=f.name)
    os.unlink(f.name)
    assert cfg.debug is True


def test_debug_false_explicit():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("debug: false\n")
        f.flush()
        cfg = Config(path=f.name)
    os.unlink(f.name)
    assert cfg.debug is False
