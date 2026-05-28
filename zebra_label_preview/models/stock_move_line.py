# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import base64

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Nuevos campos de captura para el almacenista en la recepción
    x_calibre = fields.Float(string="Calibre", digits=(16, 2))
    x_ancho = fields.Float(string="Ancho (mm)", digits=(16, 2))
    x_factura_proveedor = fields.Char(string="Factura Proveedor")
    x_rollo_proveedor = fields.Char(string="Rollo Proveedor")
    x_lote_proveedor = fields.Char(string="Lote Proveedor")
    
    # Campo computado indispensable para la lectura de inventario físico
    x_qr_content = fields.Char(compute='_compute_qr_content', string="Contenido Código QR")

    @api.depends('product_id', 'lot_id', 'quantity')
    def _compute_qr_content(self):
        for line in self:
            product_code = line.product_id.default_code or ''
            lot_name = line.lot_id.name or ''
            qty = line.quantity or 0.0
            # Formato estándar solicitado: CódigoArticulo|Lote|Cantidad
            line.x_qr_content = f"{product_code}|{lot_name}|{qty:.2f}"

    def action_open_label_preview(self):
        """ Procesa la plantilla QWeb text en ZPL y solicita el render en PNG a Labelary """
        self.ensure_one()
        
        # 1. Renderizar la plantilla QWeb Text para obtener el código ZPL puro
        report_action = self.env.ref('zebra_label_preview.action_report_zebra_jkkpack')
        # _render_qweb_text devuelve una tupla, el índice 0 contiene el String generado
        zpl_content_bytes, report_type = report_action._render_qweb_text(self.ids)
        zpl_text = zpl_content_bytes.decode('utf-8') if isinstance(zpl_content_bytes, bytes) else zpl_content_bytes

        # 2. Consumir la API de Labelary para simular una Zebra a 203 DPI (8 dpmm) en tamaño 4x6 pulgadas
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/'
        headers = {'Accept': 'image/png'}
        
        try:
            response = requests.post(url, headers=headers, data=zpl_text.encode('utf-8'), timeout=10)
            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                
                # 3. Crear el registro del asistente temporal y abrir el pop-up modal
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
                raise UserError(_("La API de Labelary respondió con un error (%s): %s") % (response.status_code, response.text))
        except requests.exceptions.RequestException as e:
            raise UserError(_("No se pudo conectar con el motor de vista previa externa (Labelary): %s") % str(e))
