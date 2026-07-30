# Apipos — API de impresión (guía de integración)

Apipos es un agente local que expone impresoras térmicas (tickets) y de etiquetas
por HTTP. Corre en la misma máquina que la impresora.

- **Base URL:** `http://127.0.0.1:50432`
- **Formato:** JSON (`Content-Type: application/json`). Sin autenticación. CORS habilitado.
- Los PDF se envían **embebidos en el JSON como base64** (no multipart, no URL).

## Formato de respuesta (todos los endpoints)

```json
{ "status": "success" | "error", "data": <objeto o null>, "message": "texto" }
```

HTTP `200` = éxito, `400` = error de negocio/validación, `500` = error inesperado.
Evalúa siempre el campo `status`, no solo el código HTTP.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET | `/printers` | Lista los nombres de impresoras instaladas |
| GET | `/printers/selected` | Impresora seleccionada por defecto (o `null`) |
| POST | `/printers/selected` | Fija la impresora por defecto: `{"printer": "NOMBRE"}` |
| POST | `/print` | Imprime un trabajo RAW (ticket) o PDF |
| GET/POST | `/print/test` | Imprime el ticket de prueba integrado |
| GET/POST | `/print/test-label` | Imprime la etiqueta de prueba integrada (60×30 mm) |
| POST | `/open-withdrawer` | Abre el cajón de dinero: `{"printer": "NOMBRE"}` (opcional) |

## Reglas generales

1. **Manda siempre `"printer"` explícito.** Si se omite se usa la impresora
   seleccionada, que puede no ser la que esperas. Los nombres exactos vienen de
   `GET /printers` (ej. `"AiYin_AS240_BT"` — respeta guiones bajos).
2. Si la impresora no existe, la respuesta es `400` con
   `message: "Printer 'X' not found."` y `data.available` = lista de impresoras
   válidas. Úsala para corregir el nombre.
3. `message: "No printer selected."` significa que omitiste `"printer"` y no hay
   impresora por defecto configurada.

---

## Imprimir un PDF — `POST /print` con `type: "PDF"`

```json
{
  "printer": "AiYin_AS240_BT",
  "type": "PDF",
  "data": "<PDF en base64>",
  "settings": {
    "pdf_mode": "driver",
    "label_settings": { "width": 60, "height": 30, "unit": "mm" }
  }
}
```

### Campos

- `data` (requerido): el PDF en base64. Se acepta base64 puro o data URI
  (`"data:application/pdf;base64,..."`).
- `settings.pdf_mode`: **`"driver"` o `"raw"`**.
  - `"driver"`: el driver de la impresora renderiza el PDF (vía el sistema de
    impresión del SO). **Es el modo correcto para impresoras de etiquetas con
    driver instalado (ej. AiYin)** — su firmware ignora los trabajos raw genéricos.
  - `"raw"`: rasteriza el PDF a imagen ESC/POS y lo manda crudo. Para
    tiqueteras térmicas de recibos o impresoras sin driver.
- `settings.label_settings` (para etiquetas): `{ "width", "height", "unit" }`.
  `unit` es `"mm"` (default) o `"inch"`. En modo driver define el tamaño del
  media (ej. `media=Custom.60x30mm`); en modo raw define el ancho de
  rasterización (8 dots/mm ≈ 203 DPI).

### Defaults (si omites `pdf_mode`)

- Con `label_settings` → `"driver"`.
- Sin `label_settings` → `"raw"` (comportamiento de recibo).

### Reglas para etiquetas

- La **página del PDF debe medir lo mismo que la etiqueta** (ej. 60×30 mm =
  170×85 pt). El driver escala al media: un PDF tamaño carta saldría deforme.
- Un PDF de varias páginas imprime **una etiqueta por página**.
- Ejemplo de respuesta exitosa en modo driver:
  `{"status":"success","data":{"strategy":"driver","media":"Custom.60x30mm",...}}`

---

## Imprimir un ticket — `POST /print` con `type: "RAW"`

Construye el ticket como una lista de items en `content`; el corte de papel se
agrega automáticamente al final.

```json
{
  "printer": "POS80_Kinwodon",
  "type": "RAW",
  "settings": { "paper_size": 80 },
  "content": [
    { "type": "image", "data": "<PNG/JPG en base64>" },
    { "type": "text", "data": "MI TIENDA S.A.", "align": "center", "font_size": "md", "font_weight": "bold" },
    { "type": "text", "data": "Av. Principal 123", "align": "center" },
    { "type": "text", "data": "RFC ABC010101XYZ", "align": "center", "font_weight": "thin" },
    { "type": "separator" },
    { "type": "table", "data": { "rows": [
        [2, "Coca Cola 600ml", "$18.00", "$36.00"],
        [1, "Pan Bimbo", "$45.50", "$45.50"]
    ]}},
    { "type": "separator" },
    { "type": "text", "data": "PEDIDO #42", "align": "center", "high_contrast": true },
    { "type": "special_text", "data": { "text1": "TOTAL", "text2": "$81.50" }, "font_weight": "bold", "high_contrast": true },
    { "type": "text", "data": "¡Gracias por su compra!", "align": "center" },
    { "type": "open_withdrawer" }
  ]
}
```

### Items de `content`

| `type` | Campos | Notas |
|---|---|---|
| `text` | `data` (string), `align`: `left`\|`center`\|`right`, `font_size`: `normal`\|`md`\|`lg`, `font_weight`: `normal`\|`bold`\|`thin` (opcional, default `normal`), `high_contrast`: bool (opcional, default `false`) | `md` = doble tamaño, `lg` = triple. `font_weight: "bold"` imprime en negrita; `"thin"` usa la Fuente B de la impresora (más pequeña y ligera) y recalcula el ancho del renglón a 64 columnas en 80mm (42 en 58mm). `high_contrast: true` imprime el texto en alto contraste (fondo negro / texto blanco) con un margen de 1 espacio; el relleno de alineación queda fuera del bloque. Las tres opciones son combinables |
| `special_text` | `data: {"text1", "text2"}`, `font_weight`: `normal`\|`bold`\|`thin` (opcional, default `normal`), `high_contrast`: bool (opcional, default `false`) | text1 a la izquierda, text2 a la derecha (para TOTAL, CAMBIO, etc.). `font_weight` aplica al renglón completo. `high_contrast: true` invierte la línea completa (fondo negro / texto blanco) |
| `table` | `data: {"rows": [[cant, producto, precio, importe], ...]}` | Imprime encabezado Cant./Producto/Precio/Importe |
| `separator` | — | Línea de guiones |
| `image` | `data` (imagen base64) | Se convierte a B/N y se centra |
| `open_withdrawer` | — | Abre el cajón al final del ticket |

> **Nota de compatibilidad de `font_weight: "thin"`.** ESC/POS no tiene un peso
> "light" real: `thin` se aproxima con la Fuente B de la impresora (`ESC M`).
> `bold` (`ESC E`) es prácticamente universal, pero el soporte de la Fuente B
> depende del firmware: hay impresoras donde su ancho de columna difiere (la
> alineación puede quedar levemente desviada) y otras donde se ignora y el
> texto sale normal. Es una degradación aceptable, no un error del API.

### `settings` (opcional, modo RAW)

- `paper_size`: `80` (default, 48 columnas) o `58` (32 columnas), en mm.
- `char_width`: columnas explícitas (`48`/`32`); tiene prioridad sobre `paper_size`.

---

## Pruebas rápidas

```
GET /print/test?printer=POS80_Kinwodon            → ticket de prueba
GET /print/test-label?printer=AiYin_AS240_BT      → etiqueta de prueba 60×30 mm (modo driver)
GET /print/test-label?printer=X&mode=raw&width=50&height=25&unit=mm
```

## Errores comunes

| `message` | Causa | Corrección |
|---|---|---|
| `Printer 'X' not found.` | Nombre mal escrito | Usa un nombre de `data.available` |
| `No printer selected.` | Sin `printer` y sin default | Manda `"printer"` explícito |
| `Invalid base64 PDF data.` / `Provided data is not a valid PDF.` | `data` corrupto o no es PDF | Verifica la codificación base64 |
| `Unsupported pdf_mode 'X'. Use 'driver' or 'raw'.` | Modo inválido | Solo `driver` o `raw` |
| `Unsupported unit 'X'. Use 'mm' or 'inch'.` | Unidad inválida | Solo `mm` o `inch` |
| `label_settings requires a numeric 'width'.` | Falta ancho | Incluye `width` numérico |
| No imprime pero responde `success` | Etiquetera con job raw genérico | Usa `pdf_mode: "driver"` |
