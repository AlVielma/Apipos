# Apipos (Api POS)

API local de impresión para puntos de venta. Corre como una pequeña aplicación
de bandeja (system tray / barra de menú) que expone una API HTTP en
`http://localhost:50432` para imprimir tickets ESC/POS, abrir el cajón de dinero
y listar/seleccionar impresoras.

El mismo código genera instaladores para **Windows** y **macOS**: la única parte
dependiente del sistema operativo (el I/O con la impresora) está aislada en una
capa de _backends_ intercambiable.

---

## Tabla de contenido

- [¿Cómo funciona?](#cómo-funciona)
- [Arquitectura](#arquitectura)
- [Endpoints de la API](#endpoints-de-la-api)
- [Formato de impresión](#formato-de-impresión)
- [Desarrollo local](#desarrollo-local)
- [Crear instalador según el SO](#crear-instalador-según-el-so)
- [Notas](#notas)

---

## ¿Cómo funciona?

1. Al iniciar, [apipos.py](apipos.py) levanta el servidor Flask en un hilo
   secundario (puerto `50432`) y muestra un ícono en la bandeja del sistema.
2. Desde la bandeja el usuario puede elegir la **impresora por defecto**, que se
   guarda en disco (`%APPDATA%\Apipos` en Windows, `~/Apipos` en macOS/Linux).
3. El POS (web/escritorio) hace peticiones HTTP a la API para imprimir. Cada
   petición puede:
   - usar la impresora por defecto, **o**
   - especificar otra impresora y sus _settings_ (tamaño de papel), permitiendo
     **manejar varias impresoras** desde un mismo servicio.
4. La API traduce el contenido recibido a comandos **ESC/POS** y los envía a la
   impresora a través del backend correspondiente al sistema operativo.

El servicio corre 100% local; no envía datos a internet.

---

## Arquitectura

El código está organizado por capas para mantener responsabilidades separadas:

```
apipos.py                      # Entry point: levanta Flask (hilo) + ícono de bandeja
src/
├── app.py                     # create_app(): factory de Flask, registra blueprints
├── config.py                  # Rutas, constantes, puerto, resource_path
├── routes/                    # Definición de endpoints (importan controladores)
│   ├── printer_routes.py
│   └── system_routes.py
├── controllers/               # Solo try/catch → llaman al servicio → responden
│   ├── printer_controller.py
│   └── system_controller.py
├── services/                  # Lógica de negocio + respuesta estandarizada
│   ├── printer_service.py     #   orquesta impresión / cajón / selección
│   ├── escpos_service.py      #   formateo ESC/POS (imágenes, tablas, texto)
│   ├── storage_service.py     #   persiste la impresora por defecto (pickle)
│   └── system_service.py      #   diagnóstico (SO + backend activo)
├── printers/                  # Capa de plataforma (I/O con la impresora)
│   ├── __init__.py            #   get_backend(): elige backend según el SO
│   ├── base.py                #   interfaz PrinterBackend
│   ├── windows_backend.py     #   Windows (win32print / RAW spooler)
│   └── macos_backend.py       #   macOS / Linux (CUPS: lp / lpstat)
├── tray.py                    # Ícono de bandeja (wxPython) — multiplataforma
└── utils/
    └── response.py            # Helpers de respuesta genérica
```

**Flujo de una petición:** `route → controller → service → escpos_service → backend`

- **routes**: declaran la URL y el método; delegan al controlador.
- **controllers**: un único `try/catch`, llaman al servicio y serializan la
  respuesta (mapean `status` → código HTTP). No tienen lógica de negocio.
- **services**: toda la lógica; devuelven siempre la **respuesta estandarizada**.
- **printers** (capa de plataforma): cada backend implementa `list_printers()`,
  `get_printer_width()` y `send_raw()`. `get_backend()` elige el correcto en
  tiempo de ejecución, y las librerías específicas de cada SO (`win32print`, CUPS)
  se importan de forma diferida para que el código nunca falle en el SO contrario.

### Respuesta estandarizada

Todos los servicios devuelven la misma forma:

```json
{
  "status": "success" | "error",
  "data": <T> | null,
  "message": "mensaje específico"
}
```

El controlador mapea: `success` → `200`, error de negocio → `400`, excepción no
controlada → `500`.

---

## Endpoints de la API

Base URL: `http://localhost:50432`

| Método | Ruta                  | Descripción                                        |
|--------|-----------------------|----------------------------------------------------|
| `GET`  | `/health`             | Estado del servicio, SO y backend de impresión activo |
| `GET`  | `/printers`           | Lista las impresoras disponibles en la máquina     |
| `GET`  | `/printers/selected`  | Devuelve la impresora por defecto actual           |
| `POST` | `/printers/selected`  | Cambia la impresora por defecto                    |
| `POST` | `/print`              | Imprime un ticket                                  |
| `POST` | `/open-withdrawer`    | Abre el cajón de dinero                            |

### `GET /health`

```json
{
  "status": "success",
  "data": {
    "status": "ok",
    "os": "Darwin",
    "platform": "darwin",
    "backend": "MacPrinterBackend",
    "port": 50432
  },
  "message": "Service is running."
}
```

### `POST /printers/selected`

```json
{ "printer": "EPSON TM-T20" }
```

### `POST /print`

Formato recomendado (objeto): permite elegir impresora y settings por petición.

```json
{
  "printer": "EPSON TM-T20",
  "settings": { "paper_size": 80 },
  "content": [
    { "type": "text", "data": "MI TIENDA", "align": "center", "font_size": "lg" },
    { "type": "separator" },
    {
      "type": "table",
      "data": { "rows": [["2", "Café", "30.00", "60.00"]] }
    },
    { "type": "special_text", "data": { "text1": "Total", "text2": "$60.00" } },
    { "type": "image", "data": "<base64>" },
    { "type": "open_withdrawer" }
  ]
}
```

- `printer` *(opcional)*: a qué impresora va el trabajo. Si se omite, usa la
  impresora por defecto seleccionada en la bandeja.
- `settings` *(opcional)*:
  - `paper_size`: ancho del papel en mm (`80` → 48 columnas, `58` → 32 columnas).
  - `char_width`: número exacto de columnas (sobrescribe a `paper_size`).
  - Si no se envía, se consulta el ancho directamente a la impresora.
- `content`: lista de elementos a imprimir.

**Tipos de elemento (`type`)**

| `type`           | `data`                                             | Notas                                  |
|------------------|----------------------------------------------------|----------------------------------------|
| `text`           | string                                             | `align`: left/center/right; `font_size`: normal/md/lg |
| `special_text`   | `{ "text1": "...", "text2": "..." }`               | Dos textos justificados a los extremos |
| `table`          | `{ "rows": [[cant, prod, precio, importe], ...] }` | Encabezado fijo Cant./Producto/Precio/Importe |
| `separator`      | —                                                  | Línea de guiones a lo ancho            |
| `image`          | string base64                                      | Se convierte a B/N y ESC/POS           |
| `open_withdrawer`| —                                                  | Abre el cajón al final del ticket      |

> Compatibilidad: `POST /print` también acepta el formato antiguo (una lista de
> elementos directamente, sin objeto envolvente), usando la impresora por defecto.

### `POST /open-withdrawer`

Body opcional `{ "printer": "..." }`; si se omite usa la impresora por defecto.

---

## Formato de impresión

Apipos genera comandos **ESC/POS** (estándar de impresoras térmicas de tickets).
El ancho del ticket se mide en columnas de caracteres: típicamente **32** para
papel de 58 mm y **48** para papel de 80 mm.

---

## Desarrollo local

Requisitos: **Python 3.9+**.

```bash
# 1. Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Instalar dependencias según el SO
pip install -r requirements-macos.txt     # macOS / Linux
pip install -r requirements-windows.txt   # Windows

# 3. Ejecutar
python apipos.py
```

Verificar que el servicio está arriba:

```bash
curl http://localhost:50432/health
```

### Dependencias

| Archivo                     | Plataforma | Incluye                                   |
|-----------------------------|------------|-------------------------------------------|
| `requirements.txt`          | común      | Flask, Flask-Cors, Pillow, wxPython       |
| `requirements-windows.txt`  | Windows    | + `pywin32`                               |
| `requirements-macos.txt`    | macOS/Linux| solo CUPS del sistema (`lp` / `lpstat`)   |

> En macOS/Linux no se requiere ninguna librería extra para imprimir: se usa
> CUPS, que viene con el sistema. (Opcionalmente, si `python-escpos` está
> instalado, el backend usa su wrapper `Lp`.)

---

## Crear instalador según el SO

El empaquetado se hace con **PyInstaller** usando un `.spec` por plataforma.
Cada build debe hacerse **en su propio sistema operativo** (PyInstaller no hace
cross-compilation).

```bash
pip install pyinstaller
```

### Windows (.exe)

```powershell
pip install -r requirements-windows.txt
pyinstaller apipos.spec
```

Genera un ejecutable único en `dist\Apipos.exe`. Es una app sin consola que vive
en la bandeja del sistema.

> Para un instalador propiamente dicho (con accesos directos, inicio automático,
> desinstalador), envuelve el `.exe` con [Inno Setup](https://jrsoftware.org/isinfo.php)
> o NSIS.

### macOS (.app)

```bash
pip install -r requirements-macos.txt
pyinstaller apipos-macos.spec
```

Genera `dist/Apipos.app` (app de barra de menú, sin ícono en el Dock gracias a
`LSUIElement`).

Para distribuirla como **.dmg**:

```bash
hdiutil create -volname "Apipos" -srcfolder "dist/Apipos.app" -ov -format UDZO Apipos.dmg
```

> Para distribución fuera de tu equipo, macOS requiere **firmar** (`codesign`) y
> **notarizar** la app con una cuenta de Apple Developer; de lo contrario
> Gatekeeper la bloqueará. Configura `codesign_identity` en `apipos-macos.spec`.

### Resumen de archivos de build

| Archivo               | Plataforma | Salida                |
|-----------------------|------------|-----------------------|
| `apipos.spec`         | Windows    | `dist/Apipos.exe`     |
| `apipos-macos.spec`   | macOS      | `dist/Apipos.app`     |

---

## Notas

- **Puerto:** `50432` (configurable en [src/config.py](src/config.py)).
- **Impresora por defecto:** se guarda en `selected_printer.pkl` dentro de
  `%APPDATA%\Apipos` (Windows) o `~/Apipos` (macOS/Linux).
- **CORS** está habilitado para que el POS web pueda llamar a la API.
- El ícono de la bandeja es `assets/app-icon.png`.
