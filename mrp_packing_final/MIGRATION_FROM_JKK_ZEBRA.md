# Migración desde jkk_report y zebra_label_preview

Esta versión incorpora las funciones de los módulos `jkk_report` y `zebra_label_preview`.

## Orden seguro de migración

1. Mantener instalados temporalmente `jkk_report` y `zebra_label_preview`.
2. Reemplazar/actualizar `mrp_packing_final` a la versión 19.0.1.8.0.
3. Reiniciar Odoo y comprobar que `mrp_packing_final` cargó correctamente.
4. Desinstalar `jkk_report` y `zebra_label_preview`.
5. Reiniciar Odoo y actualizar nuevamente `mrp_packing_final`.

Este orden hace que los campos persistentes de los módulos anteriores ya estén declarados por
`mrp_packing_final` antes de retirar los addons antiguos, preservando sus columnas y valores.

## Funciones absorbidas

### jkk_report
- Campos y datos adicionales en Órdenes de Fabricación.
- Reporte personalizado de Orden de Fabricación y componentes.
- Numeración y almacén en componentes.
- Fecha teórica de pago en Orden de Compra.
- Fecha de entrega en líneas y reporte de compra.
- Validación para impedir recepciones de compra por encima de la cantidad solicitada.

### zebra_label_preview
- Campos de proveedor/calibre/ancho en `stock.move.line`.
- QR de recepción.
- Etiqueta Zebra ZT411 4x6 en QWeb-text.
- Vista previa Labelary.
- Impresión individual y masiva desde operaciones de inventario.
