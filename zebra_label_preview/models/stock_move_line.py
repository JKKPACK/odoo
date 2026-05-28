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

    def action_open_label_preview(self):
        """ Procesa el QWeb en texto ZPL y solicita el render PNG a Labelary """
        self.ensure_one()
        
        # 1. CORREGIDO PARA ODOO 19: Pasar explícitamente el parámetro docids
        report_action = self.env.ref('zebra_label_preview.action_report_zebra_jkkpack')
        zpl_content_bytes, report_type = report_action._render_qweb_text(docids=self.ids)
        
        # Asegurar decodificación limpia de los comandos de texto nativos
        zpl_text = zpl_content_bytes.decode('utf-8') if isinstance(zpl_content_bytes, bytes) else zpl_content_bytes

        # 2. Enviar comandos ZPL a Labelary (Configurado a 203 DPI y lienzo de 4x6 pulgadas)
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/'
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
