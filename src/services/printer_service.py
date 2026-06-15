"""Business logic for the printer API.

Every public function returns the standardized response shape
(success_response / error_response). Controllers just forward these.

Multiple printers are supported per-request: a print/drawer request may target
any printer by name and override paper settings, instead of relying solely on
the single printer selected from the tray.
"""
from src.services import escpos_service as escpos
from src.services.print_job_builder import PrintJobBuilder
from src.services.storage_service import load_selected_printer, save_selected_printer
from src.utils.response import success_response, error_response


def _resolve_char_width(printer_name, settings):
    """Resolve the character width to use, honoring per-request settings.

    Priority:
      1. settings.char_width        -> explicit character columns (e.g. 32 / 48)
      2. settings.paper_size (mm)   -> 48 cols for >= 80mm, otherwise 32
      3. printer DevMode            -> queried from the printer itself
    """
    settings = settings or {}

    if settings.get('char_width'):
        return int(settings['char_width'])

    paper_size = settings.get('paper_size') or settings.get('paper_size_mm')
    if paper_size:
        return 48 if int(paper_size) >= 80 else 32

    return escpos.get_printer_width(printer_name)


def _parse_print_payload(payload):
    """Accept both the legacy (list of items) and the new (object) payloads.

    New shape:
        {
            "printer": "EPSON TM-T20",      # optional, falls back to selected printer
            "settings": {"paper_size": 80}, # optional
            "content": [ ...items... ]      # the items to print
        }

    Legacy shape: a bare list of items -> uses the selected printer.
    """
    if isinstance(payload, dict):
        printer_name = payload.get('printer') or payload.get('printer_name')
        settings = payload.get('settings') or {}
        content = payload.get('content') or payload.get('items') or []
    elif isinstance(payload, list):
        printer_name = None
        settings = {}
        content = payload
    else:
        raise ValueError("Invalid payload: expected an object or a list of items")

    if not printer_name:
        printer_name = load_selected_printer()

    return printer_name, settings, content


def get_printers():
    """List the printers available on this machine."""
    return success_response(data=escpos.list_printers(), message="Printers listed.")


def get_selected_printer():
    """Return the currently selected default printer."""
    return success_response(data=load_selected_printer())


def set_selected_printer(payload):
    """Set the default printer used when a request does not specify one."""
    payload = payload or {}
    printer_name = payload.get('printer') or payload.get('printer_name')
    if not printer_name:
        return error_response("Field 'printer' is required.")

    available = escpos.list_printers()
    if printer_name not in available:
        return error_response(f"Printer '{printer_name}' not found.", data={"available": available})

    save_selected_printer(printer_name)
    return success_response(data=printer_name, message="Selected printer updated.")


def open_drawer(payload=None):
    """Open the cash drawer of the given (or selected) printer."""
    printer_name = None
    if isinstance(payload, dict):
        printer_name = payload.get('printer') or payload.get('printer_name')
    if not printer_name:
        printer_name = load_selected_printer()

    if not printer_name:
        return error_response("No printer selected.")

    escpos.send_to_printer(printer_name, "\x1B\x70\x00\x19\xFA")  # Open the cash drawer
    return success_response(data={"printer": printer_name}, message="Cash drawer opened.")


def print_job(payload):
    """Render and send a print job to the target printer."""
    printer_name, settings, content = _parse_print_payload(payload)

    if not printer_name:
        return error_response("No printer selected.")
    if not content:
        return error_response("No content to print.")

    width = _resolve_char_width(printer_name, settings)
    builder = PrintJobBuilder(width)
    open_withdrawer = False

    for item in content:
        item_type = item.get('type')

        if item_type == 'image' and item.get('data'):
            image_bw = escpos.image_base64_to_bitmap(item['data'])
            if not image_bw:
                return error_response("Error converting image to black and white.")
            resized_image = escpos.resize_image(image_bw, target_width=int(384 * 1))
            image_data = escpos.convert_image_to_escpos_format(resized_image)
            builder.add_image(image_data)

        elif item_type == 'text':
            builder.add_text(
                item['data'],
                align=item.get('align', 'left'),
                font_size=item.get('font_size', 'normal'),
            )

        elif item_type == 'special_text':
            special_text_data = item['data']
            builder.add_special_text(special_text_data['text1'], special_text_data['text2'])

        elif item_type == 'table':
            builder.add_table(item['data'].get('rows', []))

        elif item_type == 'separator':
            builder.add_separator()

        elif item_type == 'open_withdrawer':
            open_withdrawer = True

    # Advance the paper and cut.
    builder.add_feed_and_cut()
    if open_withdrawer:
        builder.add_open_drawer()

    # Send the whole ticket as a SINGLE raw job.
    escpos.send_raw(printer_name, builder.to_bytes())

    return success_response(
        data={"printer": printer_name, "char_width": width},
        message="Print job completed.",
    )
