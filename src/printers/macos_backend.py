"""macOS / Linux printer backend (CUPS).

Printing on macOS/Linux goes through CUPS. We send raw ESC/POS bytes with the
`lp` command (`lp -d <printer> -o raw`) and discover printers with `lpstat`.
Both ship with the OS, so no extra dependency is required.

If python-escpos is installed, its `Lp` printer is used instead (it wraps the
same `lp` command); otherwise we fall back to calling `lp` directly.
"""
import subprocess

from src.printers.base import PrinterBackend


class MacPrinterBackend(PrinterBackend):
    native_pdf = True  # CUPS renders PDFs natively

    def list_printers(self):
        # `lpstat -e` prints one CUPS destination (printer) name per line.
        result = subprocess.run(
            ['lpstat', '-e'], capture_output=True, text=True, check=False
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def get_printer_width(self, printer_name):
        # CUPS does not expose the paper width the way Windows' DevMode does.
        # Default to 80mm (48 chars); callers can override via request settings.
        return 48

    def send_raw(self, printer_name, data):
        try:
            from escpos.printer import Lp  # optional dependency
        except Exception:
            Lp = None

        if Lp is not None:
            printer = Lp(printer_name=printer_name)
            try:
                printer._raw(data)
            finally:
                try:
                    printer.close()
                except Exception:
                    pass
        else:
            # Send the raw ESC/POS byte stream straight to CUPS.
            subprocess.run(
                ['lp', '-d', printer_name, '-o', 'raw'],
                input=data,
                check=True,
            )

        print(f"Data sent to printer: {printer_name}")

    def print_pdf(self, printer_name, pdf_bytes, options=None):
        # CUPS handles PDF natively, so we send it WITHOUT `-o raw` and let the
        # printer driver rasterize it. options['media_mm'] = (w, h) selects a
        # custom media size (label printing); other options pass through as
        # `-o name=value`.
        options = dict(options or {})
        media_mm = options.pop('media_mm', None)

        command = ['lp', '-d', printer_name]
        if media_mm:
            command += ['-o', f'media=Custom.{media_mm[0]:g}x{media_mm[1]:g}mm']
        for name, value in options.items():
            command += ['-o', f'{name}={value}']
        subprocess.run(
            command,
            input=pdf_bytes,
            check=True,
        )
        print(f"PDF sent to printer: {printer_name} (media_mm={media_mm})")
