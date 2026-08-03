# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import base64


class StockMove(models.Model):
    _inherit = 'stock.move'

    def action_print_all_labels_from_move(self):
        """ Imprime todas las etiquetas de las líneas de este movimiento en un único ZPL """
        # Obtener todas las líneas del movimiento
        move_lines = self.move_line_ids
        
        if not move_lines:
            raise UserError(_("Este movimiento no tiene líneas"))
        
        # XML ID de nuestro reporte personalizado
        report_ref = 'zebra_label_preview.action_report_zebra_jkkpack'
        
        # 1. Renderizar todas las líneas a texto ZPL
        zpl_content_bytes, report_type = self.env['ir.actions.report']._render_qweb_text(
            report_ref,
            data={},
            res_ids=move_lines.ids
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
                    'move_line_id': move_lines[0].id if move_lines else False,
                    'preview_image': image_base64,
                    'zpl_code': zpl_text,
                })
                
                return {
                    'name': _('Vista Previa de Etiquetas - Zebra ZT411 (%d líneas)') % len(move_lines),
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
