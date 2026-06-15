"""Common interface every platform printer backend must implement.

A backend is responsible only for the OS-specific I/O:
  - discovering printers,
  - resolving a default character width,
  - writing a raw ESC/POS byte stream to a printer.

All ESC/POS *formatting* (images, tables, text) is platform independent and
lives in `src.services.escpos_service`.
"""


class PrinterBackend:
    def list_printers(self):
        """Return a list of available printer names (list[str])."""
        raise NotImplementedError

    def get_printer_width(self, printer_name):
        """Return the printer's width in characters (e.g. 32 for 58mm, 48 for 80mm)."""
        raise NotImplementedError

    def send_raw(self, printer_name, data):
        """Send a raw ESC/POS byte stream (bytes) to the printer as a single job."""
        raise NotImplementedError
