from odoo import models, fields, api

class StockMove(models.Model):
    super_model = 'stock.move'
    _inherit = 'stock.move'

    # Campos computados de solo lectura
    purchase_price_unit = fields.Float(
        string='Precio Unitario', 
        compute='_compute_purchase_fields'
    )
    purchase_subtotal = fields.Float(
        string='Subtotal', 
        compute='_compute_purchase_fields'
    )

    @api.depends('purchase_line_id', 'quantity')
    def _compute_purchase_fields(self):
        for move in self:
            # Verificamos si el movimiento proviene de una compra
            if move.purchase_line_id:
                line = move.purchase_line_id
                move.purchase_price_unit = line.price_unit
                # Calculamos el subtotal basado en la cantidad recibida/hecha
                move.purchase_subtotal = line.price_unit * move.quantity
            else:
                move.purchase_price_unit = 0.0
                move.purchase_subtotal = 0.0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_total = fields.Float(
        string='Total Compra (Recibido)', 
        compute='_compute_purchase_total'
    )

    @api.depends('move_ids.purchase_subtotal')
    def _compute_purchase_total(self):
        for picking in self:
            # Sumamos los subtotales de cada línea del albarán
            picking.purchase_total = sum(move.purchase_subtotal for move in picking.move_ids)