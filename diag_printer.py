"""Diagnostico de impresion RAW para aislar por que un ticket sale en blanco.

Uso (en la maquina Windows, con el venv del proyecto activado):

    python diag_printer.py "BIXOLON SRP-330II"

Imprime UN solo ticket con varias pruebas etiquetadas. Segun que aparezca en
el papel sabremos el origen del problema:

  - No sale NADA (ni el texto):   los bytes RAW no llegan al interprete ESC/POS
                                  (problema de driver / puerto / print processor).
  - Solo sale el TEXTO:           el RAW funciona, falla el comando grafico.
  - Texto + barra ANGOSTA pero    la impresora descarta rasters mas anchos que
    NO la ancha:                  su cabezal -> es un tema de ancho (dots).
  - Texto + TODAS las barras:     el ESC @ (init) era lo que faltaba; hay que
                                  agregarlo al pipeline real.

No usa PIL: construye los rasters a mano.
"""
import sys
import win32print

ESC = b'\x1b'
GS = b'\x1d'
INIT = ESC + b'@'            # ESC @  -> reset a estado conocido
LINE_SPACING_0 = ESC + b'3\x00'
FEED_CUT = b'\n\n\n\n' + GS + b'V\x00'  # feed + corte total


def text(s):
    return s.encode('latin1', 'replace')


def gsv0_solid_bar(width, height):
    """Barra solida negra via GS v 0 (raster estandar)."""
    bpr = (width + 7) // 8
    xL, xH = bpr & 0xFF, (bpr >> 8) & 0xFF
    yL, yH = height & 0xFF, (height >> 8) & 0xFF
    return GS + b'v0\x00' + bytes([xL, xH, yL, yH]) + b'\xff' * (bpr * height)


def escstar_solid_bar(width, height):
    """Barra solida negra via ESC * 33 (bit-image legacy, 24 dots/strip)."""
    out = bytearray(LINE_SPACING_0)
    nL, nH = width & 0xFF, (width >> 8) & 0xFF
    strips = (height + 23) // 24
    for _ in range(strips):
        out += ESC + b'*\x21' + bytes([nL, nH])   # ESC * 33 nL nH
        out += b'\xff' * (width * 3)               # cada columna = 3 bytes (24 dots)
        out += b'\n'
    return bytes(out)


def build_job():
    out = bytearray()
    out += INIT
    out += text("=== DIAG APIPOS ===\n")
    out += text("1) Texto RAW = OK\n\n")

    out += text("2) GS v 0 angosta (200):\n")
    out += gsv0_solid_bar(200, 48)
    out += b'\n\n'

    out += text("3) GS v 0 ancha (576):\n")
    out += gsv0_solid_bar(576, 48)
    out += b'\n\n'

    out += text("4) ESC * angosta (200):\n")
    out += escstar_solid_bar(200, 48)
    out += b'\n\n'

    out += FEED_CUT
    return bytes(out)


def send_raw(printer_name, data):
    h = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(h, 1, ("APIPOS DIAG", None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, data)
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)


def main():
    if len(sys.argv) < 2:
        print("Impresoras disponibles:")
        for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        ):
            print("  -", p[2])
        print('\nUso: python diag_printer.py "NOMBRE EXACTO DE LA IMPRESORA"')
        return

    printer = sys.argv[1]
    job = build_job()
    print(f"Enviando {len(job)} bytes RAW a: {printer}")
    send_raw(printer, job)
    print("Enviado. Revisa el ticket y dime cuales secciones (1/2/3/4) se imprimieron.")


if __name__ == "__main__":
    main()
