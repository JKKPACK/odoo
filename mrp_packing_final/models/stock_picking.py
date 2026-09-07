from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    jkk_production_id = fields.Many2one(
        "mrp.production", string="Orden de Fabricación", compute="_compute_jkk_report_origin"
    )
    jkk_sale_order_id = fields.Many2one(
        "sale.order", string="Orden de Venta", compute="_compute_jkk_report_origin"
    )
    jkk_process = fields.Char(string="Proceso", compute="_compute_jkk_report_origin")

    @api.depends("origin", "move_ids.raw_material_production_id", "move_ids.production_id")
    def _compute_jkk_report_origin(self):
        Production = self.env["mrp.production"]
        SaleOrder = self.env["sale.order"]
        for picking in self:
            production = (
                picking.move_ids.mapped("raw_material_production_id")
                | picking.move_ids.mapped("production_id")
            )[:1]
            if not production and picking.origin:
                production = Production.search([("name", "=", picking.origin)], limit=1)
            sale = production.sale_order_id if production else False
            if not sale and picking.origin:
                sale = SaleOrder.search([("name", "=", picking.origin)], limit=1)
            workcenter = production._packing_workcenter() if production else False
            picking.jkk_production_id = production
            picking.jkk_sale_order_id = sale
            picking.jkk_process = workcenter.name if workcenter else picking.picking_type_id.name
