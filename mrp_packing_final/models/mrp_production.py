from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = "mrp.production"
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Orden de Venta",
        compute="_compute_sale_info",
        store=True,
        readonly=False,
    )
    customer_code = fields.Char(
        string="Código Cliente",
        compute="_compute_sale_info",
        store=True,
        readonly=False,
    )
    customer_name = fields.Char(
        string="Nombre Cliente",
        compute="_compute_sale_info",
        store=True,
        readonly=False,
    )
    customer_order_ref = fields.Char(string="Pedido Cliente")
    customer_item_no = fields.Char(string="Customer Item # / Destiny #")
    pallet_ids = fields.One2many("mrp.pallet", "production_id", string="Tarimas")
    pallet_count = fields.Integer(compute="_compute_pallet_count")

    @api.depends("origin")
    def _compute_sale_info(self):
        for rec in self:
            if not rec.sale_order_id and rec.origin:
                so = self.env["sale.order"].search([("name", "=", rec.origin)], limit=1)
                if so:
                    rec.sale_order_id = so
            if rec.sale_order_id:
                rec.customer_code = rec.sale_order_id.partner_id.ref or str(
                    rec.sale_order_id.partner_id.id
                )
                rec.customer_name = rec.sale_order_id.partner_id.name
                rec.customer_order_ref = (
                    rec.sale_order_id.client_order_ref or rec.sale_order_id.name
                )

    def _compute_pallet_count(self):
        for r in self:
            r.pallet_count = len(r.pallet_ids)

    def action_start_packing(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Iniciar Empaquetado",
            "res_model": "pallet.start.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_production_id": self.id},
        }

    def action_view_pallets(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Tarimas",
            "res_model": "mrp.pallet",
            "view_mode": "list,form",
            "domain": [("production_id", "=", self.id)],
        }
