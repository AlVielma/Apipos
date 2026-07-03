"""Windows printer backend: RAW spooler jobs (win32print) and driver/GDI
printing for PDFs (win32ui), the Windows equivalent of the CUPS document path."""
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

    def print_pdf(self, printer_name, pdf_bytes, options=None):
        """Render the PDF with PyMuPDF and print it through the printer DRIVER (GDI).

        Windows equivalent of the CUPS document path on macOS: the vendor
        driver receives rendered pages, so label printers whose firmware
        ignores generic raw jobs (e.g. AiYin) print correctly.

        options['media_mm'] = (width_mm, height_mm) sets a custom paper size
        in the DEVMODE (DMPAPER_USER, tenths of a millimeter), so the driver
        formats the job for the label media. Each PDF page = one page/label.
        """
        try:
            import fitz  # PyMuPDF (same optional dependency as the raster path)
        except ImportError as e:
            raise ImportError(
                "PDF printing requires PyMuPDF. Install it with: pip install PyMuPDF"
            ) from e
        import win32con
        import win32gui
        import win32ui
        from PIL import Image, ImageWin

        media_mm = (options or {}).get('media_mm')

        # DEVMODE: start from the printer defaults; apply the custom paper
        # size when printing on label media.
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            devmode = win32print.GetPrinter(hprinter, 2)['pDevMode']
            if devmode is not None and media_mm:
                width_mm, height_mm = media_mm
                devmode.PaperSize = win32con.DMPAPER_USER
                devmode.PaperWidth = int(round(width_mm * 10))    # 0.1 mm units
                devmode.PaperLength = int(round(height_mm * 10))
                devmode.Orientation = win32con.DMORIENT_PORTRAIT
                devmode.Fields = (
                    devmode.Fields
                    | win32con.DM_PAPERSIZE
                    | win32con.DM_PAPERWIDTH
                    | win32con.DM_PAPERLENGTH
                    | win32con.DM_ORIENTATION
                )
                # Let the driver validate/normalize the requested size.
                win32print.DocumentProperties(
                    0, hprinter, printer_name, devmode, devmode,
                    win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
                )
        finally:
            win32print.ClosePrinter(hprinter)

        hdc = win32gui.CreateDC('WINSPOOL', printer_name, devmode)
        dc = win32ui.CreateDCFromHandle(hdc)
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        try:
            printable_w = dc.GetDeviceCaps(win32con.HORZRES)
            printable_h = dc.GetDeviceCaps(win32con.VERTRES)
            zoom_x = dc.GetDeviceCaps(win32con.LOGPIXELSX) / 72.0
            zoom_y = dc.GetDeviceCaps(win32con.LOGPIXELSY) / 72.0

            dc.StartDoc('Apipos PDF')
            try:
                for page in doc:
                    # Render the page at the printer's real DPI.
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom_x, zoom_y), alpha=False)
                    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                    # Fit to the printable area preserving aspect ratio.
                    scale = min(printable_w / image.width, printable_h / image.height)
                    target_w = max(1, int(image.width * scale))
                    target_h = max(1, int(image.height * scale))
                    dc.StartPage()
                    ImageWin.Dib(image).draw(dc.GetHandleOutput(), (0, 0, target_w, target_h))
                    dc.EndPage()
                dc.EndDoc()
            except Exception:
                dc.AbortDoc()
                raise
        finally:
            doc.close()
            dc.DeleteDC()

        print(f"PDF sent to printer driver: {printer_name} (media_mm={media_mm})")
