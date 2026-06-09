# -*- coding: utf-8 -*-
from odoo import models, fields, _

class StockLabelPreviewWizard(models.TransientModel):
    _name = 'stock.label.preview.wizard'
    _description = 'Asistente de Vista Previa para Etiquetas Zebra'

    move_line_id = fields.Many2one('stock.move.line', string="Línea de Movimiento", readonly=True)
    preview_image = fields.Binary(string="Etiqueta Renderizada", readonly=True)
    zpl_code = fields.Text(string="Código Fuente ZPL", readonly=True)

    def action_print_physical_label(self):
        """ Ejecuta la acción nativa de impresión que envía el archivo QWeb-Text a la Zebra """
        self.ensure_one()
        return self.env.ref('zebra_label_preview.action_report_zebra_jkkpack').report_action(self.move_line_id.ids)
