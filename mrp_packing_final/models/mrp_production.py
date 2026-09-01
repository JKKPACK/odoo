from dateutil.relativedelta import relativedelta

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
    customer_label_text = fields.Text(
        string="Texto cliente para etiqueta",
        compute="_compute_sale_info",
        store=True,
        readonly=False,
        help="Texto capturado por CRM/Ventas que se imprime en la etiqueta.",
    )
    # Campos heredados del antiguo módulo jkk_report. Se conservan con los
    # mismos nombres para mantener sus datos al retirar dicho módulo.
    expiration_date = fields.Date(
        string="Fecha de Caducidad",
        compute="_compute_expiration_date",
        store=True,
    )
    design_no = fields.Char(string="Diseño No")
    production_type = fields.Selection(
        [("standard", "Estándar"), ("special", "Especial")],
        string="Tipo",
        default="standard",
    )
    origin_type = fields.Selection(
        [("manual", "Manual"), ("reprocess", "Reproceso")],
        string="Origen",
        default="manual",
    )
    order_type = fields.Selection(
        [("normal", "Normal"), ("special", "Especial")],
        string="Tipo Orden",
        default="normal",
    )
    sale_reference = fields.Char(
        related="sale_order_id.name", string="Referencia SO", store=True
    )
    bom_reference = fields.Char(
        related="bom_id.display_name", string="Lista Materiales", store=True
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
                rec.customer_order_ref = so.client_order_ref or False
                rec.customer_label_text = so.packing_label_text or False
            else:
                rec.sale_order_id = False
                rec.customer_code = rec.customer_code or False
                rec.customer_name = rec.customer_name or False
                rec.customer_order_ref = rec.customer_order_ref or False
                rec.customer_label_text = rec.customer_label_text or False


    @api.depends("date_start", "date_finished")
    def _compute_expiration_date(self):
        for production in self:
            base_date = (
                production.date_finished
                or production.date_start
                or fields.Datetime.now()
            )
            production.expiration_date = (
                fields.Date.to_date(base_date) + relativedelta(years=1)
            )

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
        boxes = self.env["mrp.box"].search([
            "|",
            ("source_production_id", "=", self.id),
            "&", ("source_production_id", "=", False), ("production_id", "=", self.id),
        ])
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


    def _packing_family_productions(self):
        """Return this MO and its manufacturing backorders/partials.

        Odoo 19 groups manufacturing backorders in ``production_group_id`` and
        identifies the original MO with ``backorder_sequence == 0``.  We only
        aggregate productions of the same finished product and company so the
        normal per-MO packing flow remains untouched.
        """
        self.ensure_one()
        if not self.production_group_id:
            return self
        productions = self.production_group_id.production_ids.filtered(
            lambda mo: mo.product_id == self.product_id and mo.company_id == self.company_id
        )
        return productions.sorted(lambda mo: (mo.backorder_sequence, mo.id)) or self

    def _packing_main_production(self):
        """Return the original/main MO of a manufacturing backorder family.

        In Odoo 19, once an MO is split, the original production no longer keeps
        ``backorder_sequence == 0``: Odoo changes it to sequence 1 and renames it
        with the ``-001`` suffix.  Therefore the main production must be resolved
        as the first production in the group, not by testing sequence == 0.
        """
        self.ensure_one()
        family = self._packing_family_productions()
        if not family:
            return self
        return family.sorted(lambda mo: (mo.backorder_sequence or 0, mo.id))[:1]

    def _is_main_packing_production(self):
        self.ensure_one()
        family = self._packing_family_productions()
        return len(family) > 1 and self == self._packing_main_production()

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
