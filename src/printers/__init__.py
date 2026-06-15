"""Platform printer backends.

The rest of the app talks to printers only through a `PrinterBackend`. The
concrete implementation (Windows / macOS-CUPS) is chosen at runtime here, so the
same codebase can be packaged into installers for both operating systems.

Platform-specific libraries (win32print, escpos.printer.Lp) are imported lazily
inside each backend module, so importing this package never fails on the "wrong"
OS.
"""
import sys

_backend = None


def get_backend():
    """Return the singleton printer backend for the current platform."""
    global _backend
    if _backend is not None:
        return _backend

    if sys.platform.startswith('win'):
        from src.printers.windows_backend import WindowsPrinterBackend
        _backend = WindowsPrinterBackend()
    else:
        # macOS and Linux both print through CUPS / the `lp` command.
        from src.printers.macos_backend import MacPrinterBackend
        _backend = MacPrinterBackend()

    return _backend
