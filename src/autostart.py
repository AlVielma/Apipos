"""Self-register the app so it launches automatically when the user logs in.

`enable_autostart()` is idempotent and safe to call on every launch. It only
acts when the app is *frozen* (running from a PyInstaller bundle), so running
from source during development never touches the OS login items.

  - Windows: writes an HKCU\\...\\Run registry value pointing at the .exe.
  - macOS:   writes a LaunchAgent plist under ~/Library/LaunchAgents.

Because the app distributes both via installer (Windows) and drag-and-drop DMG
(macOS), registering from inside the app guarantees autostart regardless of how
it was installed.
"""
import os
import sys

from src.config import APP_NAME, APP_BUNDLE_ID


def _is_frozen():
    return getattr(sys, 'frozen', False)


def _executable_path():
    # In a PyInstaller bundle sys.executable IS the app's own binary.
    return sys.executable


def enable_autostart():
    """Register the app to start on login. Never raises (autostart is best-effort)."""
    if not _is_frozen():
        return  # don't register the development interpreter
    try:
        if sys.platform == 'win32':
            _enable_windows()
        elif sys.platform == 'darwin':
            _enable_macos()
    except Exception as exc:  # noqa: BLE001 - autostart must never crash the app
        print(f"[autostart] no se pudo registrar el inicio automatico: {exc}")


def disable_autostart():
    """Remove the autostart registration. Best-effort, never raises."""
    try:
        if sys.platform == 'win32':
            _disable_windows()
        elif sys.platform == 'darwin':
            _disable_macos()
    except Exception as exc:  # noqa: BLE001
        print(f"[autostart] no se pudo quitar el inicio automatico: {exc}")


# --------------------------------------------------------------------------- #
# Windows                                                                      #
# --------------------------------------------------------------------------- #
_RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _enable_windows():
    import winreg

    exe = _executable_path()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_SUBKEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe}"')


def _disable_windows():
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_SUBKEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass  # already absent


# --------------------------------------------------------------------------- #
# macOS                                                                        #
# --------------------------------------------------------------------------- #
_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""


def _launch_agent_path():
    return os.path.expanduser(f"~/Library/LaunchAgents/{APP_BUNDLE_ID}.plist")


def _enable_macos():
    exe = _executable_path()
    path = _launch_agent_path()
    content = _PLIST_TEMPLATE.format(label=APP_BUNDLE_ID, exe=exe)

    # Only rewrite when the content actually changed (e.g. app moved/updated).
    if os.path.exists(path):
        with open(path, encoding='utf-8') as fh:
            if fh.read() == content:
                return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    # NOTE: we deliberately do NOT `launchctl load` here. launchd loads agents
    # at the next login, which is exactly what we want. Loading now (with
    # RunAtLoad) would spawn a second instance that fights for the API port.


def _disable_macos():
    import subprocess

    path = _launch_agent_path()
    if os.path.exists(path):
        subprocess.run(['launchctl', 'unload', path], capture_output=True)
        os.remove(path)
