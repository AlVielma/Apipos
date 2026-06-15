"""Windows printer backend (win32print / RAW spooler jobs)."""
import win32print

from src.printers.base import PrinterBackend


class WindowsPrinterBackend(PrinterBackend):
    native_pdf = False  # PDFs are rasterized to ESC/POS before sending

    def list_printers(self):
        printers = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
        return [printer[2] for printer in printers]  # printer[2] is the printer name

    def get_printer_width(self, printer_name):
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            dev_mode = win32print.GetPrinter(hprinter, 2)['pDevMode']
            if dev_mode.PaperWidth >= 700:  # 80mm width
                return 48  # Max width in characters
            return 32  # Default to 32 characters (common for 58mm paper)
        finally:
            win32print.ClosePrinter(hprinter)

    def send_raw(self, printer_name, data):
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(hprinter, 1, ("ESC/POS Print Job", None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, data)
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
            print(f"Data sent to printer: {printer_name}")
        finally:
            win32print.ClosePrinter(hprinter)

    def print_pdf(self, printer_name, pdf_bytes):
        # Optional/fallback path. By default the service rasterizes PDFs to
        # ESC/POS (native_pdf = False), so this is only used if invoked directly.
        # Hands the PDF to the registered Windows PDF viewer via the ShellExecute
        # "printto" verb, targeting the requested printer.
        import os
        import tempfile
        import win32api

        fd, path = tempfile.mkstemp(suffix='.pdf')
        with os.fdopen(fd, 'wb') as f:
            f.write(pdf_bytes)

        # "printto" expects the printer name (quoted) as the parameter.
        win32api.ShellExecute(0, 'printto', path, f'"{printer_name}"', '.', 0)
        # NOTE: ShellExecute returns immediately; the temp file is left in the
        # OS temp folder so the viewer can finish reading it.
        print(f"PDF sent to printer: {printer_name}")
