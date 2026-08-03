# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

class StockLabelPreviewWizard(models.TransientModel):
    _name = 'stock.label.preview.wizard'
    _description = 'Asistente de Vista Previa para Etiquetas Zebra'

    move_line_id = fields.Many2one('stock.move.line', string="Línea de Movimiento", readonly=True)
    preview_image = fields.Binary(string="Etiqueta Renderizada", readonly=True)
    zpl_code = fields.Text(string="Código Fuente ZPL", readonly=True)

    def action_print_physical_label(self):
        """ Ejecuta la acción nativa de impresión que envía TODOS los archivos QWeb-Text a la Zebra """
        import json
        self.ensure_one()
        
        # Extraer los IDs almacenados en el código ZPL como comentario al inicio
        # Formato: {{IDS:[1,2,3]}}
        line_ids = []
        if self.zpl_code:
            try:
                # Buscar patrón {{IDS:[...]}} al inicio del zpl_code
                import re
                match = re.search(r'\{\{IDS:\[(.*?)\]\}\}', self.zpl_code)
                if match:
                    ids_str = match.group(1)
                    line_ids = [int(id_str.strip()) for id_str in ids_str.split(',')]
            except (ValueError, AttributeError):
                pass
        
        # Si no se encontraron IDs, usar el move_line_id
        if not line_ids and self.move_line_id:
            line_ids = [self.move_line_id.id]
        
        # Si no hay IDs, lanzar error
        if not line_ids:
            raise UserError(_("No hay líneas para imprimir"))
        
        # Retornar la acción de reporte con TODOS los IDs
        return self.env.ref('zebra_label_preview.action_report_zebra_jkkpack').report_action(line_ids)
