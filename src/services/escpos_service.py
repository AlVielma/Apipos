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

def image_base64_to_bitmap(image_base64, threshold=200):
    try:
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))

        # Handle transparency by flattening it onto a white background
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, (0, 0), image)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        image_gray = image.convert('L')

        def apply_threshold(p):
            return 255 if p > threshold else 0

        image_bw = image_gray.point(apply_threshold)
        return image_bw.convert('1')

    except Exception as e:
        print(f"Error al convertir la imagen base64: {e}")
        return None


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
