# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import base64

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Campos de captura manual en la recepción
    x_calibre = fields.Float(string="Calibre", digits=(16, 2))
    x_ancho = fields.Float(string="Ancho (mm)", digits=(16, 2))
    x_factura_proveedor = fields.Char(string="Factura Proveedor")
    x_rollo_proveedor = fields.Char(string="Rollo Proveedor")
    x_lote_proveedor = fields.Char(string="Lote Proveedor")
    
    # Campo computado para la recolección del escáner en inventarios físicos
    x_qr_content = fields.Char(compute='_compute_qr_content', string="Contenido Código QR")

    @api.depends('product_id', 'lot_id', 'quantity')
    def _compute_qr_content(self):
        for line in self:
            product_code = line.product_id.default_code or ''
            lot_name = line.lot_id.name or ''
            qty = line.quantity or 0.0
            # Estructura requerida: CódigoArticulo|Lote|Cantidad
            line.x_qr_content = f"{product_code}|{lot_name}|{qty:.2f}"

    @api.onchange('quantity')
    def _onchange_quantity_validate(self):
        """ Valida en tiempo real que la cantidad total no exceda la demanda """
        for line in self:
            if line.move_id and line.move_id.product_uom_qty:
                # Sumar todas las líneas del movimiento incluyendo la actual
                total_qty = sum(line.move_id.move_line_ids.filtered(lambda l: l.product_id == line.product_id).mapped('quantity'))
                if total_qty > line.move_id.product_uom_qty:
                    return {
                        'warning': {
                            'title': _('Cantidad total excede la demanda'),
                            'message': _('La cantidad total (%s) no puede exceder la demanda (%s) para el producto %s') % (
                                total_qty,
                                line.move_id.product_uom_qty,
                                line.product_id.name
                            )
                        }
                    }

    @api.constrains('quantity')
    def _check_quantity_not_exceeds_demand(self):
        """ Valida que la cantidad total no exceda la demanda del movimiento al guardar """
        for line in self:
            if line.move_id and line.move_id.product_uom_qty:
                # Sumar todas las líneas del movimiento para el mismo producto
                total_qty = sum(line.move_id.move_line_ids.filtered(lambda l: l.product_id == line.product_id).mapped('quantity'))
                if total_qty > line.move_id.product_uom_qty:
                    raise UserError(
                        _("La cantidad total (%s) no puede exceder la demanda (%s) para el producto %s") % (
                            total_qty,
                            line.move_id.product_uom_qty,
                            line.product_id.name
                        )
                    )

    def action_open_label_preview(self):
        """ Procesa el QWeb en texto ZPL y solicita el render PNG a Labelary """
        self.ensure_one()
        
        # XML ID de nuestro reporte personalizado
        report_ref = 'zebra_label_preview.action_report_zebra_jkkpack'
        
        # 1. ADAPTADO PARA ODOO 19.0: Renderizar el QWeb a texto
        # Firma en Odoo 19: _render_qweb_text(report_ref, data, res_ids)
        zpl_content_bytes, report_type = self.env['ir.actions.report']._render_qweb_text(
            report_ref,
            data={},
            res_ids=self.ids
        )
        
        # Asegurar decodificación limpia de los comandos de texto nativos
        zpl_text = zpl_content_bytes.decode('utf-8') if isinstance(zpl_content_bytes, bytes) else zpl_content_bytes

        # 2. Enviar comandos ZPL a Labelary (Configurado a 300 DPI y lienzo de 4x6 pulgadas)
        # 300 DPI = 11.81 dpmm (12dpmm en Labelary)
        # Dimensiones: 1200 dots (ancho) x 1800 dots (alto)
        url = 'http://api.labelary.com/v1/printers/12dpmm/labels/4x6/0/'
        headers = {'Accept': 'image/png'}
        
        try:
            response = requests.post(url, headers=headers, data=zpl_text.encode('utf-8'), timeout=10)
            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                
                # 3. Crear el registro del asistente y retornar la ventana modal
                wizard = self.env['stock.label.preview.wizard'].create({
                    'move_line_id': self.id,
                    'preview_image': image_base64,
                    'zpl_code': zpl_text,
                })
                
                return {
                    'name': _('Vista Previa de Etiqueta - Zebra ZT411'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.label.preview.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new',
                }
            else:
                raise UserError(_("Error de Labelary (%s): %s") % (response.status_code, response.text))
        except requests.exceptions.RequestException as e:
            raise UserError(_("No se pudo conectar con el servicio de renderizado: %s") % str(e))

    def action_print_all_labels(self):
        """ Imprime todas las etiquetas en un único ZPL para impresora Zebra """
        if not self:
            raise UserError(_("Debe seleccionar al menos una línea para imprimir"))
        
        # XML ID de nuestro reporte personalizado
        report_ref = 'zebra_label_preview.action_report_zebra_jkkpack'
        
        # 1. Renderizar todas las líneas a texto ZPL
        zpl_content_bytes, report_type = self.env['ir.actions.report']._render_qweb_text(
            report_ref,
            data={},
            res_ids=self.ids
        )
        
        # Asegurar decodificación limpia de los comandos de texto nativos
        zpl_text = zpl_content_bytes.decode('utf-8') if isinstance(zpl_content_bytes, bytes) else zpl_content_bytes

        # 2. Enviar comandos ZPL a Labelary para previsualización
        url = 'http://api.labelary.com/v1/printers/12dpmm/labels/4x6/0/'
        headers = {'Accept': 'image/png'}
        
        try:
            response = requests.post(url, headers=headers, data=zpl_text.encode('utf-8'), timeout=10)
            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                
                # 3. Crear el registro del asistente y retornar la ventana modal
                wizard = self.env['stock.label.preview.wizard'].create({
                    'move_line_id': self[0].id if len(self) == 1 else False,
                    'preview_image': image_base64,
                    'zpl_code': zpl_text,
                })
                
                return {
                    'name': _('Vista Previa de Etiquetas - Zebra ZT411 (%d líneas)') % len(self),
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.label.preview.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new',
                }
            else:
                raise UserError(_("Error de Labelary (%s): %s") % (response.status_code, response.text))
        except requests.exceptions.RequestException as e:
            raise UserError(_("No se pudo conectar con el servicio de renderizado: %s") % str(e))
