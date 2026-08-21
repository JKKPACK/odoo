# Auditoría de etiquetas vs. Observaciones Etiquetas General

## Entrada de Mercancías
- Fecha de caducidad: incluida desde el lote (`stock.lot`) cuando existe.
- Artículo, recepción, código de barras, descripción, OC, tipo de material, calibre, ancho, cantidad, factura, rollo proveedor, lote proveedor, usuario, fecha, lote y QR: incluidos.
- Se eliminaron las líneas horizontales y el marco que invadían la zona del código de barras vertical del lote.

## Caja / Bobina
- La información extra de la Orden de Venta se toma de `sale.order.packing_label_text` y se imprime como Leyenda Cliente.
- Pedido Cliente se toma de `sale.order.client_order_ref`.
- Fecha de caducidad se imprime desde el lote cuando existe.

## Master
- Pedido Cliente, peso bruto acumulado y leyenda de cliente están incluidos.
- Por requerimiento, la Master NO imprime fecha de caducidad.
- Se mantiene 6x4 horizontal (1800x1200, 300 dpi).

## Impresión / Laminación
El archivo de observaciones indica “No tiene Formato solicitado”, pero no define un formato objetivo ni campos requeridos. No se inventó un nuevo layout sin especificación.
