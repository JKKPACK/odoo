# MRP Empaquetado Final - Odoo 19

Versión mejorada conforme al documento **Etiquetado Cajas/Bobinas y Tarima**.

## Cambios principales

- Etiqueta ZPL de caja/bobina 4x6 vertical a 12 dpmm (300 dpi), con los campos del lineamiento, Code128 y QR `Articulo/Lote/Cantidad`.
- Etiqueta ZPL Master 6x4 horizontal a 12 dpmm, con acumulados de tarima, Code128 y QR `Articulo/Tarima/Cantidad`.
- Un lote de producción solo puede ser usado una vez en la misma OF; se selecciona exactamente un lote por caja/bobina.
- Lista de empaque alineada con el ejemplo del documento: número, lote, peso bruto, peso neto y cantidad por caja.
- Texto comercial de etiqueta capturable desde la Orden de Venta (`packing_label_text`).
- Centro de trabajo de producto terminado y operador integrados al inicio del proceso.
- Eliminación de archivos duplicados, hardcodes de cliente/producto y rutas de impresión HTML con dependencias CDN.
- Validaciones de pesos, cantidades y duplicidad de lotes.

## Nota

Todas las etiquetas ZPL (Master 6x4 y Caja/Bobina 4x6) se previsualizan con Labelary antes de imprimir. La salida real se mantiene como ZPL nativo mediante reportes `qweb-text`.


### Empaque agrupado de producciones parciales
Desde la producción principal, el asistente **Iniciar Empaquetado** puede activar **Incluir todas las producciones parciales**. Al hacerlo, la tarima reúne los lotes disponibles de la producción principal y de sus backorders/parcialidades. Cada caja conserva la producción origen de su lote. Si la opción no se activa, el comportamiento individual por OF sigue siendo el mismo.
