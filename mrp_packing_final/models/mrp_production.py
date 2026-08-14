from odoo import api, fields, models


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
    customer_order_ref = fields.Char(
        string="Pedido Cliente",
        compute="_compute_sale_info",
        store=True,
        readonly=False,
    )
    customer_label_text = fields.Char(
        string="Texto cliente para etiqueta",
        compute="_compute_sale_info",
        store=True,
        readonly=False,
        help="Texto capturado por CRM/Ventas que se imprime en la etiqueta.",
    )
    customer_item_no = fields.Char(string="Customer Item # / Destiny Item #")
    pallet_ids = fields.One2many("mrp.pallet", "production_id", string="Tarimas")
    pallet_count = fields.Integer(compute="_compute_pallet_count")

    @api.depends(
        "origin",
        "sale_order_id",
        "sale_order_id.partner_id",
        "sale_order_id.client_order_ref",
        "sale_order_id.packing_label_text",
    )
    def _compute_sale_info(self):
        SaleOrder = self.env["sale.order"]
        for rec in self:
            so = rec.sale_order_id
            if not so and rec.origin:
                # origin can contain several references; prefer an exact SO name.
                so = SaleOrder.search([("name", "=", rec.origin)], limit=1)
            if so:
                rec.sale_order_id = so
                rec.customer_code = so.partner_id.ref or str(so.partner_id.id)
                rec.customer_name = so.partner_id.name
                rec.customer_order_ref = so.client_order_ref or so.name
                rec.customer_label_text = so.packing_label_text or rec.customer_label_text
            else:
                rec.sale_order_id = False
                rec.customer_code = rec.customer_code or False
                rec.customer_name = rec.customer_name or False
                rec.customer_order_ref = rec.customer_order_ref or False
                rec.customer_label_text = rec.customer_label_text or False

    def _compute_pallet_count(self):
        for rec in self:
            rec.pallet_count = len(rec.pallet_ids)

    def _packing_lots(self):
        self.ensure_one()
        distribution = self.lot_distribution_id
        return distribution.line_ids.mapped("lot_id") if distribution else self.env["stock.lot"]

    def _available_packing_lots(self):
        self.ensure_one()
        lots = self._packing_lots()
        boxes = self.env["mrp.box"].search([("production_id", "=", self.id)])
        used = boxes.filtered("lot_id").mapped("lot_id")
        legacy_names = set(
            name.strip()
            for box in boxes.filtered(lambda b: not b.lot_id and b.master_lot)
            for name in box.master_lot.split(",")
            if name.strip()
        )
        if legacy_names:
            used |= lots.filtered(lambda lot: lot.name in legacy_names)
        return lots - used

    def _packing_workcenter(self):
        self.ensure_one()
        workcenters = self.workorder_ids.mapped("workcenter_id").filtered(
            "is_finished_product"
        )
        return workcenters[:1]

    def action_start_packing(self):
        self.ensure_one()
        available_lots = self._available_packing_lots()
        workcenter = self._packing_workcenter()
        employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Iniciar Empaquetado",
            "res_model": "pallet.start.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_production_id": self.id,
                "default_num_boxes": len(available_lots) or 1,
                "default_machine": workcenter.name if workcenter else False,
                "default_workcenter_id": workcenter.id if workcenter else False,
                "default_operator_id": employee.id if employee else False,
            },
        }

    def action_view_pallets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Tarimas",
            "res_model": "mrp.pallet",
            "view_mode": "kanban,list,form",
            "domain": [("production_id", "=", self.id)],
            "context": {"default_production_id": self.id},
        }
