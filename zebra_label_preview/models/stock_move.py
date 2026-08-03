# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import base64
import json

class StockMove(models.Model):
    _inherit = 'stock.move'

    def action_print_all_labels_from_move(self):
        """
        Imprime todas las etiquetas asociadas a las líneas de movimiento.
        Este método es llamado desde la vista de stock.move.
        """
        # Obtener todas las líneas de movimiento
        move_lines = self.move_line_ids.filtered(lambda l: l.product_id)
        
        if not move_lines:
            raise UserError(_("Este movimiento no tiene líneas para imprimir"))
        
        # Llamar al método de impresión desde las líneas de movimiento
        return move_lines.action_open_label_preview()

    def action_print_physical_label_from_move(self):
        """
        Envía directamente a impresión todas las etiquetas sin previsualización.
        """
        # Obtener todas las líneas de movimiento
        move_lines = self.move_line_ids.filtered(lambda l: l.product_id)
        
        if not move_lines:
            raise UserError(_("Este movimiento no tiene líneas para imprimir"))
        
        # XML ID de nuestro reporte personalizado
        report_ref = 'zebra_label_preview.action_report_zebra_jkkpack'
        
        # Retornar la acción de reporte con TODOS los IDs de las líneas
        return self.env.ref(report_ref).report_action(move_lines.ids)
