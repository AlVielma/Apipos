"""Intermediate layer that assembles a whole ticket into a single ESC/POS byte
stream, so the entire job is sent to the printer in ONE call (one spooler job).

Text/tables/separators are appended as latin1 bytes; images are appended as raw
ESC/POS bytes. Each piece carries its own control commands inline, which is
harmless mid-stream. Call `to_bytes()` once and send it with a single send_raw.
"""
from src.services import escpos_service as escpos

# Control commands
LINE_HEIGHT_TEXT = b'\x1b\x33\x42'   # ESC 3 n -> line height for text
LINE_HEIGHT_IMAGE = b'\x1b\x33\x00'  # ESC 3 0 -> tight line height for images
ALIGN_LEFT = b'\x1b\x61\x00'
ALIGN_CENTER = b'\x1b\x61\x01'
FONT_NORMAL = b'\x1D\x21\x00'
FONT_MD = b'\x1D\x21\x11'  # double width and height
FONT_LG = b'\x1D\x21\x22'  # triple width and height
FULL_CUT = b'\x1d\x56\x00'
OPEN_DRAWER = b'\x1B\x70\x00\x19\xFA'


class PrintJobBuilder:
    def __init__(self, width):
        self.width = width
        self._buf = bytearray()
        # Set the text line height once at the start of the job.
        self._buf += LINE_HEIGHT_TEXT

    # -- low level -------------------------------------------------------
    def _add_str(self, text):
        # latin1 preserves accented characters / ñ
        self._buf += text.encode('latin1')

    # -- content pieces --------------------------------------------------
    def add_text(self, text, align='left', font_size='normal'):
        if font_size == 'md':
            self._buf += FONT_MD
            scale = 2  # 'md' = doble ancho: cada carácter ocupa 2 columnas
        elif font_size == 'lg':
            self._buf += FONT_LG
            scale = 3  # 'lg' = triple ancho
        else:
            self._buf += FONT_NORMAL
            scale = 1

        # El ancho efectivo en caracteres se reduce según el tamaño de fuente,
        # porque el relleno (espacios) también se imprime a ese ancho. Si se
        # usara self.width sin escalar, el texto en 'md'/'lg' se desborda y salta
        # de línea (aparece corrido a la derecha y parte se va al renglón de abajo).
        width = max(1, self.width // scale)

        if align == 'center':
            text = text.center(width)
        elif align == 'right':
            text = text.rjust(width)
        else:
            text = text.ljust(width)

        self._add_str(text)
        self._buf += FONT_NORMAL  # reset font size to normal
        self._add_str('\n')

    def add_special_text(self, text1, text2):
        self._add_str(escpos.format_special_text(text1, text2, self.width) + '\n')

    def add_table(self, rows):
        width = self.width
        header = (
            "Cant.".ljust(int(width * 0.15))
            + "Producto".ljust(int(width * 0.45))
            + "Precio".rjust(int(width * 0.20))
            + "Importe".rjust(int(width * 0.20))
            + "\n"
            + "-" * width + "\n"
        )
        table_string = "\n" + header
        for row in rows:
            table_string += escpos.format_table_item(row[0], row[1], row[2], row[3], width) + "\n"
        self._add_str(table_string + "\n")

    def add_separator(self):
        self._add_str(escpos.get_separator(self.width))

    def add_image(self, image_data):
        # Switch to image mode (tight line height, centered), then restore text.
        self._buf += LINE_HEIGHT_IMAGE + ALIGN_CENTER
        self._buf += image_data
        self._add_str('\n')
        self._buf += LINE_HEIGHT_TEXT + ALIGN_LEFT

    def add_feed_and_cut(self):
        self._add_str("\n\n\n\n")  # advance paper before cutting
        self._buf += FULL_CUT

    def add_open_drawer(self):
        self._buf += OPEN_DRAWER

    # -- output ----------------------------------------------------------
    def to_bytes(self):
        return bytes(self._buf)
