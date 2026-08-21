## 19.0.1.8.7
- Master ZPL 6x4: vuelve a mostrar Fecha de Caducidad, tomada directamente de `mrp.production.expiration_date`.
- Master: redistribuida la fila de fecha/caducidad/peso neto/tarima para aprovechar mejor el espacio.


## 19.0.1.7.4
- Limpieza técnica de código muerto y artefactos generados.
- Eliminada la lógica antigua de reimpresión desde `pallet.start.wizard`; la reimpresión se realiza desde la tarima.
- Eliminados campos antiguos `include_partial_productions` y `partial_production_ids`; la selección de parcialidades usa únicamente `production_selection_line_ids`.
- Eliminado `production_lot_ids` del wizard de captura por no ser consumido por ninguna vista ni proceso.
- Eliminados wrappers ZPL Python sin referencias internas (`generate_*_zpl`) y la ruta HTTP Master sin consumidores.
- Se conservan todos los modelos funcionales y las rutas/acciones activas.

## 19.0.1.7.3
- Control de previsualización masiva: hasta 50 etiquetas Caja/Bobina se muestran con Labelary.
- Cuando la selección supera 50 etiquetas, no se solicita ninguna previsualización a Labelary y se genera directamente el ZPL completo mediante `qweb-text`.
- El control conserva todas las cajas seleccionadas en la salida ZPL; únicamente se omite la vista previa.

## 19.0.1.7.2
- La etiqueta Master 6x4 ya no muestra fecha de caducidad.
- La fecha de caducidad se conserva únicamente en la etiqueta Caja/Bobina 4x6 cuando el lote la tiene.


## 19.0.1.7.1
- Ajuste de etiquetas Caja/Bobina y Master según Observaciones Etiquetas General.
- Leyenda de cliente se imprime únicamente cuando existe en la Orden de Venta; se elimina el fallback al nombre de producto.
- Campos opcionales de cliente/pedido/máquina no consumen contenido cuando están vacíos.
- Fecha de caducidad tomada dinámicamente del lote cuando Odoo tiene control de expiración.
- Master muestra una fecha común; si los lotes tienen fechas distintas indica VARIAS / MULTIPLE.
- Master 6x4 mantiene 1800x1200, fuerza orientación normal (^FWN/^PON), reduce velocidad/oscuridad y separa barcode/QR de líneas para mejorar impresión física.
- Código de barras Master reducido a ^BY3 y sin líneas atravesando su área.
# 19.0.1.7.0
- Arquitectura ZPL migrada a plantillas QWeb-text reales.
- Master 6x4 definida completamente en `report_pallet_zpl`.
- Caja/Bobina 4x6 definida completamente en `report_box_labels_zpl`.
- Python conserva solo datos, validaciones, helpers de saneamiento y renderizado.
- Vista previa, descarga y reporte utilizan la misma plantilla QWeb-text, evitando diferencias entre preview e impresión.
- Se mantienen wrappers `generate_*_zpl()` solo por compatibilidad con integraciones antiguas.

## 19.0.1.5.0

- Corrige la impresión física de la Master 6x4 en Zebra de 4 pulgadas: se imprime sobre media 4x6 con contenido rotado 90°, evitando cortes.
- Mantiene la vista previa Master en formato 6x4 horizontal.
- Elimina el texto debajo del QR para evitar superposición.
- Refuerza Pedido Cliente desde sale.order.client_order_ref.
- Cambia la leyenda de empaque a texto multilínea y la muestra en Master y Caja/Bobina.
- La etiqueta de caja incluye también Pedido Cliente.
- Peso Bruto Master sigue siendo la suma de los pesos brutos de todas las cajas.


## 19.0.1.4.1
- Wizards revisados para cargar automáticamente OF, operador, centro de trabajo, máquina, número de cajas y lotes cuando pueden inferirse.
- Los lotes de la OF se proponen automáticamente en cada línea de captura, manteniendo la posibilidad de cambiarlos.
- Campos opcionales/informativos de los asistentes se ocultan cuando no tienen valor; el código ZPL técnico ya no se muestra al operador.
- `box.entry.wizard` queda preparado también para tarimas manuales: usa lotes del producto cuando no existe OF.
- Los campos que son obligatorios por lógica de negocio (lote, peso bruto, tara y cantidad) ahora están marcados como requeridos en modelo/vista.
- Al crear una tarima manual se propone automáticamente el empleado vinculado al usuario actual como operador.

## 19.0.1.3.2
- Icono de impresora (`fa-print`) en todos los botones de impresión y ZPL.
- Se eliminan textos "Previsualizar / Imprimir" de los botones; se usan nombres cortos Master ZPL, Cajas/Bobinas ZPL y ZPL.
- Se eliminan los botones redundantes "Ver Cajas/Bobinas" de tarimas; las cajas siguen accesibles desde su menú y pestaña.
- Se corrige la superposición del encabezado en el Packing List PDF aumentando el margen superior y el espaciado del encabezado.

# Changelog

## 19.0.1.3.0
- Rediseño profesional del PDF Lista de Empaque: cabecera, trazabilidad, resumen, detalle, totales y firmas.
- Etiqueta Master ajustada a 6x4 pulgadas horizontal (1800x1200 dots, 300 dpi).
- Etiqueta Caja/Bobina ajustada a 4x6 pulgadas vertical (1200x1800 dots, 300 dpi).
- Redistribución completa de campos, códigos de barras y QR para mejorar legibilidad y escaneo.
- Nombres de reportes actualizados con el tamaño físico de cada etiqueta.

## 19.0.1.1.0

- Ajuste de etiqueta de caja/bobina al lineamiento recibido: 6x4, 300 dpi, campos operativos, tres Code128 y QR Articulo/Lote/Cantidad.
- Ajuste de etiqueta Master: acumulados de tarima, Code128 de tarima y QR Articulo/Tarima/Cantidad.
- Control relacional de lotes para impedir reutilización dentro de la misma orden de fabricación.
- Compatibilidad de control con registros históricos que solo tengan `master_lot` en texto.
- Lista de empaque alineada con el formato de referencia.
- Campo de texto de etiqueta en Orden de Venta para captura desde CRM/Ventas.
- Integración de centro de trabajo terminado y operador.
- Eliminación de archivos duplicados, hardcodes y previsualizaciones HTML dependientes de CDN.
- Corrección del error de ZPL de caja que referenciaba un campo inexistente (`operador`).
- Validaciones de peso, tara y cantidades.

## 19.0.1.3.1
- Todas las acciones de impresión ZPL abren primero una previsualización Labelary.
- La etiqueta Master 6x4 se previsualiza desde el mismo botón de impresión.
- Eliminado el botón independiente "Vista previa Master".
- Las etiquetas Caja/Bobina 4x6 se previsualizan individualmente o en lote antes de imprimir.
- El asistente de previsualización soporta múltiples etiquetas y muestra el ZPL completo.

## 19.0.1.3.5
- Corrige la compilación SCSS en Odoo 19 eliminando `min()` con unidades incompatibles (`vw` y `px`).
- Mantiene el modal ZPL ancho usando `width: 94%` y `max-width: 1180px`, compatible con el compilador de assets.
- Las etiquetas ZPL se muestran una por fila, centradas y sin recorte horizontal cuando los assets cargan correctamente.
- Se mantienen los botones Kanban identificados como `Cajas 4x6`, `Master 6x4` y `PDF`, todos con icono de impresora.
- Se eliminan textos internos de "Previsualización" visibles en nombres de campos del asistente.

## 19.0.1.6.0
- Nueva opción en **Iniciar Empaquetado** para agrupar la producción principal con todas sus producciones parciales/backorders.
- La opción solo aparece en la producción principal cuando Odoo detecta más de una producción en el mismo `production_group_id`.
- La captura carga automáticamente todos los lotes disponibles de la producción principal y sus parcialidades.
- Cada caja/bobina conserva la **Producción origen** que generó su lote.
- El flujo individual existente se mantiene sin cambios cuando el check no está activo.
- Se evita reutilizar lotes ya empacados, incluyendo registros históricos sin `source_production_id`.

## 19.0.1.8.0
- Integra completamente las funciones de `jkk_report` dentro de `mrp_packing_final`.
- Integra completamente las funciones de `zebra_label_preview` dentro de `mrp_packing_final`.
- Conserva los mismos nombres técnicos de campos persistentes para que sus valores no cambien de columna.
- Migra reportes MRP, reporte de componentes, personalización de compras y validación de sobre-recepción.
- Migra campos de recepción Zebra, vista previa Labelary, impresión masiva y reporte ZPL 4x6 QWeb-text.
- El reporte Zebra de recepción ahora usa el XML ID `mrp_packing_final.action_report_zebra_jkkpack`.
- Se conserva el script de validación ZPL en `scripts/validate_zpl_params.py`.

## 19.0.1.8.6
- Caja/Bobina: la fecha de caducidad se toma primero de la producción origen (`mrp.production.expiration_date`), respetando parcialidades.
- Tarimas manuales: se conserva como respaldo la fecha disponible en el lote cuando no existe una OF.
- Master 6x4: redistribución del layout rotado para aprovechar mejor el área física 4x6, aumentar tipografías y reducir espacios en blanco.
- Master: se mantiene sin fecha de caducidad.

## 19.0.1.9.0
- Rediseño completo de Master ZPL 6x4 siguiendo el formato visual aprobado.
- Una única plantilla QWeb-text para vista previa Labelary e impresión Zebra.
- Papel físico 4x6 (1200x1800 a 300 dpi) con contenido rotado 90°.
- Rejilla compacta y proporcional: OF, producto, cantidad, pedido cliente, cajas, pesos, fechas y tarima.
- Bloque de información del cliente con wrapping controlado para evitar textos sobrepuestos.
- Zona inferior reservada para barcode y QR, sin líneas divisorias que crucen los códigos.
