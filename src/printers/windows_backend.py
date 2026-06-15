"""Windows printer backend (win32print / RAW spooler jobs)."""
import win32print

from src.printers.base import PrinterBackend


class WindowsPrinterBackend(PrinterBackend):
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
