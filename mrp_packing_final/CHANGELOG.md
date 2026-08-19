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
