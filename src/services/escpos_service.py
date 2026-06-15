"""Platform-independent ESC/POS helpers.

This module only builds ESC/POS byte streams and formats text/images. All
OS-specific I/O (discovering printers, writing raw bytes) is delegated to the
platform backend in `src.printers`, so the same code runs on Windows and macOS.
"""
import base64
import io

from PIL import Image

from src.printers import get_backend


# ---------------------------------------------------------------------------
# Platform I/O (delegated to the active backend)
# ---------------------------------------------------------------------------

def list_printers():
    """Return the names of the available printers on this machine."""
    return get_backend().list_printers()


def get_printer_width(printer_name):
    """Resolve the printer width in characters for the current platform."""
    return get_backend().get_printer_width(printer_name)


def send_raw(printer_name, data):
    """Send a pre-built ESC/POS byte stream as a single RAW job."""
    get_backend().send_raw(printer_name, data)


def print_pdf(printer_name, pdf_bytes):
    """Print a PDF document via the OS print system."""
    get_backend().print_pdf(printer_name, pdf_bytes)


def native_pdf_supported():
    """True if the current platform's print system renders PDFs natively."""
    return get_backend().native_pdf


def send_to_printer(printer_name, data):
    """Send text (str) to the printer as a RAW ESC/POS job."""
    line_height_command = b'\x1b\x33\x42'  # ESC 3 -> set line height
    # latin1 encoding preserves accented characters
    payload = line_height_command + data.encode('latin1')
    get_backend().send_raw(printer_name, payload)


def send_image_to_printer(printer_name, image_data):
    """Send an ESC/POS image byte stream to the printer as a RAW job."""
    line_height_command = b'\x1b\x33\x00'
    center_command = b'\x1b\x61\x01'
    payload = line_height_command + center_command + image_data
    get_backend().send_raw(printer_name, payload)


# ---------------------------------------------------------------------------
# Image conversion (pure)
# ---------------------------------------------------------------------------

def image_to_bw(image, threshold=200):
    """Flatten transparency and threshold a PIL image to a 1-bit bitmap ('1')."""
    # Handle transparency by flattening it onto a white background
    if image.mode == 'RGBA':
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, (0, 0), image)
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    image_gray = image.convert('L')
    image_bw = image_gray.point(lambda p: 255 if p > threshold else 0)
    return image_bw.convert('1')


def image_base64_to_bitmap(image_base64, threshold=200):
    try:
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        return image_to_bw(image, threshold)
    except Exception as e:
        print(f"Error al convertir la imagen base64: {e}")
        return None


def pdf_to_escpos(pdf_bytes, width_dots=576, threshold=200):
    """Rasterize a PDF into an ESC/POS image byte stream (one block per page).

    Used on platforms without native PDF printing (Windows): each page is
    rendered to `width_dots` wide, converted to black & white and emitted as an
    ESC/POS raster image. Requires PyMuPDF (`pip install PyMuPDF`).
    """
    try:
        import fitz  # PyMuPDF (optional dependency)
    except ImportError as e:
        raise ImportError(
            "PDF rasterization requires PyMuPDF. Install it with: pip install PyMuPDF"
        ) from e

    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    try:
        out = bytearray()
        out += b'\x1b\x33\x00'  # tight line height
        out += b'\x1b\x61\x01'  # center
        for page in doc:
            zoom = width_dots / page.rect.width if page.rect.width else 1
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
            image_bw = image_to_bw(image, threshold)
            if image_bw.width != width_dots:
                image_bw = resize_image(image_bw, width_dots)
            out += convert_image_to_escpos_format(image_bw)
            out += b'\n'
        return bytes(out)
    finally:
        doc.close()


def resize_image(image, target_width):
    aspect_ratio = image.height / image.width
    target_height = int(target_width * aspect_ratio)
    return image.resize((target_width, target_height), Image.NEAREST)


def convert_image_to_escpos_format(image_bw):
    width, height = image_bw.size
    pixels = image_bw.load()
    img_data = b""
    for y in range(0, height, 24):
        img_data += b'\x1b\x2a\x21' + bytes([width % 256, width // 256])
        for x in range(width):
            for k in range(3):
                byte = 0
                for bit in range(8):
                    if y + k * 8 + bit < height and pixels[x, y + k * 8 + bit] == 0:
                        byte |= 1 << (7 - bit)
                img_data += bytes([byte])
        img_data += b'\n'
    return img_data


def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Archivo no encontrado: {image_path}")
        return None
    except Exception as e:
        print(f"Error al leer la imagen: {e}")
        return None


# ---------------------------------------------------------------------------
# Text formatting (pure)
# ---------------------------------------------------------------------------

def format_table_item(qty, item, price, importe, width):
    qty = str(qty)
    item = str(item)
    price = str(price)
    importe = str(importe)

    qty_col_width = int(width * 0.15)
    item_col_width = int(width * 0.45)
    price_col_width = int(width * 0.20)
    importe_col_width = int(width * 0.20)

    qty_col = qty.ljust(qty_col_width)
    item_col = item.ljust(item_col_width)
    price_col = price.rjust(price_col_width)
    importe_col = importe.rjust(importe_col_width)

    return f"{qty_col}{item_col}{price_col}{importe_col}"


def format_special_text(text1, text2, width):
    total_length = len(text1) + len(text2)
    if total_length > width:
        text2 = text2[:width - len(text1)]

    space_between = width - len(text1) - len(text2)
    return text1 + (' ' * space_between) + text2


def get_separator(width):
    return "-" * width + "\n"
