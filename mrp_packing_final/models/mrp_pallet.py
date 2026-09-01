import base64

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .zpl_utils import qty_text, zpl_safe


class MrpPallet(models.Model):
    _name = "mrp.pallet"
    _description = "Tarima / Pallet - Master"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="LOTE TARIMA",
        required=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("mrp.pallet") or "TR/NEW",
        copy=False,
        index=True,
        tracking=True,
    )
    production_id = fields.Many2one(
        "mrp.production",
        string="Orden de Fabricación",
        required=False,
        ondelete="set null",
        index=True,
        help="Opcional. La tarima también puede crearse manualmente sin una orden de fabricación.",
        tracking=True,
    )
    is_grouped_production_packing = fields.Boolean(
        string="Tarima de producción principal + parcialidades",
        default=False,
        copy=False,
        help="Indica que esta tarima reúne lotes de la producción principal y de sus producciones parciales.",
        tracking=True,
    )
    packing_production_ids = fields.Many2many(
        "mrp.production",
        "mrp_pallet_packing_production_rel",
        "pallet_id",
        "production_id",
        string="Producciones incluidas",
        copy=False,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        required=True,
        index=True,
        help="Producto contenido en la tarima. En tarimas ligadas a una OF se toma automáticamente de la orden.",
        tracking=True,
    )
    available_lot_ids = fields.Many2many(
        "stock.lot",
        compute="_compute_available_lot_ids",
        string="Lotes disponibles",
        help="Lotes del producto que todavía pueden seleccionarse en esta tarima manual.",
    )
    sale_order_id = fields.Many2one(related="production_id.sale_order_id", store=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Centro de Trabajo", tracking=True)
    operator_id = fields.Many2one("hr.employee", string="Operador", index=True, tracking=True)
    machine = fields.Char(string="Máquina", tracking=True)
    date_packing = fields.Datetime(string="Fecha Empaquetado", default=fields.Datetime.now, required=True, tracking=True)
    box_ids = fields.One2many("mrp.box", "pallet_id", string="Cajas/Bobinas")
    box_count = fields.Integer(compute="_compute_totals", store=True)
    box_lot_summary = fields.Text(string="Cajas / Lotes", compute="_compute_box_lot_summary")
    total_gross_weight = fields.Float(string="Peso Bruto Total (KG)", compute="_compute_totals", store=True)
    total_net_weight = fields.Float(string="Peso Neto Total (KG)", compute="_compute_totals", store=True)
    total_qty = fields.Float(string="Cant. Total / QtyPerPallet", compute="_compute_totals", store=True)
    total_tara = fields.Float(string="TARA Total", compute="_compute_totals", store=True)
    customer_code = fields.Char(related="production_id.customer_code")
    customer_name = fields.Char(related="production_id.customer_name")
    customer_order_ref = fields.Char(related="production_id.customer_order_ref")
    customer_label_text = fields.Text(related="production_id.customer_label_text")
    expiration_date = fields.Date(
        related="production_id.expiration_date",
        string="Fecha de Caducidad",
        readonly=True,
        help="Fecha de caducidad tomada de la orden de fabricación principal de la tarima.",
    )
    qr_payload = fields.Char(compute="_compute_qr_payload", string="Contenido QR Master")
    zpl_pallet = fields.Text(string="ZPL Master Tarima", compute="_compute_zpl")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "operator_id" in fields_list and not values.get("operator_id"):
            employee = self.env["hr.employee"].search(
                [("user_id", "=", self.env.user.id)], limit=1
            )
            if employee:
                values["operator_id"] = employee.id
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            production_id = vals.get("production_id")
            if production_id:
                production = self.env["mrp.production"].browse(production_id)
                if not vals.get("product_id"):
                    vals["product_id"] = production.product_id.id
                if not vals.get("packing_production_ids"):
                    vals["packing_production_ids"] = [(6, 0, [production.id])]
        return super().create(vals_list)

    @api.onchange("production_id")
    def _onchange_production_id(self):
        if self.production_id:
            self.product_id = self.production_id.product_id
            if not self.operator_id:
                self.operator_id = self.env["hr.employee"].search(
                    [("user_id", "=", self.env.user.id)], limit=1
                )
            if not self.workcenter_id:
                workcenter = self.production_id._packing_workcenter()
                self.workcenter_id = workcenter
                self.machine = workcenter.name if workcenter else self.machine

    @api.constrains("production_id", "product_id")
    def _check_production_product(self):
        for rec in self:
            if rec.production_id and rec.product_id != rec.production_id.product_id:
                raise ValidationError(_(
                    "El producto de la tarima debe coincidir con el producto de la orden de fabricación."
                ))

    @api.constrains("product_id", "box_ids")
    def _check_box_lot_products(self):
        for rec in self:
            invalid = rec.box_ids.filtered(
                lambda box: box.lot_id and box.lot_id.product_id != rec.product_id
            )
            if invalid:
                raise ValidationError(_(
                    "Todos los lotes de la tarima deben pertenecer al producto %s."
                ) % rec.product_id.display_name)

    @api.depends("product_id", "production_id", "box_ids.lot_id")
    def _compute_available_lot_ids(self):
        Lot = self.env["stock.lot"]
        Box = self.env["mrp.box"]
        for rec in self:
            if not rec.product_id:
                rec.available_lot_ids = Lot
                continue

            if rec.production_id and rec.is_grouped_production_packing:
                productions = rec.packing_production_ids or rec.production_id._packing_family_productions()
                lots = Lot.browse()
                for production in productions:
                    lots |= production._packing_lots()
                used_boxes = Box.search([
                    ("pallet_id", "!=", rec.id),
                    ("lot_id", "!=", False),
                    "|",
                    ("source_production_id", "in", productions.ids),
                    "&", ("source_production_id", "=", False), ("production_id", "in", productions.ids),
                ])
            elif rec.production_id:
                # Flujo individual original: solo lotes de esta OF.
                lots = rec.production_id._packing_lots()
                used_boxes = Box.search([
                    ("pallet_id", "!=", rec.id),
                    ("lot_id", "!=", False),
                    "|",
                    ("source_production_id", "=", rec.production_id.id),
                    "&", ("source_production_id", "=", False), ("production_id", "=", rec.production_id.id),
                ])
            else:
                # Tarima manual: todos los lotes pertenecientes al producto seleccionado.
                lots = Lot.search([("product_id", "=", rec.product_id.id)])
                used_boxes = Box.search([
                    ("pallet_id.product_id", "=", rec.product_id.id),
                    ("pallet_id", "!=", rec.id),
                    ("lot_id", "!=", False),
                ])

            used_lots = used_boxes.mapped("lot_id")
            # Los lotes ya presentes en la tarima actual deben seguir visibles al editarla.
            rec.available_lot_ids = (lots - used_lots) | rec.box_ids.mapped("lot_id")

    @api.depends("box_ids", "box_ids.peso_bruto", "box_ids.peso_neto", "box_ids.qty_per_box", "box_ids.tara")
    def _compute_totals(self):
        for rec in self:
            rec.box_count = len(rec.box_ids)
            rec.total_gross_weight = sum(rec.box_ids.mapped("peso_bruto"))
            rec.total_net_weight = sum(rec.box_ids.mapped("peso_neto"))
            rec.total_qty = sum(rec.box_ids.mapped("qty_per_box"))
            rec.total_tara = sum(rec.box_ids.mapped("tara"))

    @api.depends("product_id.default_code", "name", "total_qty")
    def _compute_qr_payload(self):
        for rec in self:
            rec.qr_payload = f"{rec.product_id.default_code or ''}/{rec.name or ''}/{qty_text(rec.total_qty)}"

    @api.depends(
        "name", "production_id.name", "product_id.default_code", "product_id.name", "sale_order_id.name",
        "customer_order_ref", "customer_name", "customer_code", "customer_label_text", "expiration_date",
        "date_packing", "box_count", "total_gross_weight", "total_net_weight", "total_qty",
    )
    def _compute_zpl(self):
        for rec in self:
            rec.zpl_pallet = rec.render_pallet_zpl()

    @api.constrains("box_ids")
    def _check_pallet_has_unique_lots(self):
        for rec in self:
            lots = rec.box_ids.filtered("lot_id").mapped("lot_id")
            if len(lots) != len(set(lots.ids)):
                raise ValidationError(_("No se puede repetir un lote dentro de la misma tarima."))

    def _zpl_safe(self, value):
        """Sanitiza únicamente datos variables; el layout ZPL vive en QWeb-text."""
        return zpl_safe(value)

    def _zpl_qty(self, value):
        return qty_text(value)

    def _zpl_date(self, value):
        return value.strftime("%d/%m/%Y") if value else ""

    def _zpl_wrap_lines(self, value, width=62, max_lines=3):
        """Divide texto variable en líneas cortas para layouts ZPL rotados.

        El diseño permanece en QWeb-text; este helper únicamente prepara los
        datos para evitar que una leyenda larga invada otros bloques.
        """
        import textwrap

        text = zpl_safe(value)
        if not text:
            return []
        lines = textwrap.wrap(
            text,
            width=int(width or 62),
            break_long_words=True,
            break_on_hyphens=False,
        )
        max_lines = max(int(max_lines or 1), 1)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            lines[-1] = (last[:-3] + "...") if len(last) > 3 else last
        return lines

    def render_pallet_zpl(self):
        """Renderiza la Master desde la plantilla QWeb-text real."""
        self.ensure_one()
        content = self.env["ir.actions.report"]._render_template(
            "mrp_packing_final.report_pallet_zpl",
            {
                "doc_ids": self.ids,
                "doc_model": self._name,
                "docs": self,
            },
        )
        return content.decode("utf-8") if isinstance(content, bytes) else str(content)

    # Compatibilidad con integraciones antiguas. El ZPL ya no está definido en Python.
    @api.depends("box_ids.sequence", "box_ids.name", "box_ids.lot_id.name", "box_ids.master_lot")
    def _compute_box_lot_summary(self):
        for rec in self:
            lines = []
            for box in rec.box_ids.sorted(lambda b: (b.sequence, b.id)):
                lot = box.lot_id.name or box.master_lot or box.name or "Sin lote"
                lines.append(_("Caja/Bobina %(seq)s — Lote %(lot)s") % {
                    "seq": box.sequence or 0,
                    "lot": lot,
                })
            rec.box_lot_summary = "\n".join(lines) or _("Sin cajas/bobinas")

    def action_print_packing_list(self):
        self.ensure_one()
        return self.env.ref("mrp_packing_final.action_report_packing_list").report_action(self)

    def _open_master_zpl_preview(self):
        """Genera la previsualización de la etiqueta Master 6x4 y abre el asistente."""
        self.ensure_one()
        # La vista previa usa exactamente el mismo ZPL que se envía a la Zebra.
        # Así Labelary muestra la orientación física 4x6 y el contenido rotado 6x4.
        zpl_code = self.render_pallet_zpl()
        try:
            response = requests.post(
                "https://api.labelary.com/v1/printers/12dpmm/labels/4x6/0/",
                headers={"Accept": "image/png"},
                data=zpl_code.encode("utf-8"),
                timeout=15,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise UserError(_(
                "No se pudo generar la previsualización de la etiqueta Master con Labelary.\n%s"
            ) % str(exc)) from exc

        preview = self.env["pallet.label.preview.wizard"].create({
            "label_type": "master",
            "pallet_id": self.id,
            "zpl_code": zpl_code,
            "preview_line_ids": [(0, 0, {
                "sequence": 1,
                "name": _("Master - %s") % self.name,
                "preview_image": base64.b64encode(response.content),
                "zpl_code": zpl_code,
            })],
        })
        return {
            "name": _("Master ZPL 6x4"),
            "type": "ir.actions.act_window",
            "res_model": "pallet.label.preview.wizard",
            "view_mode": "form",
            "res_id": preview.id,
            "target": "new",
        }

    def action_print_browser_master(self):
        # La impresión siempre pasa primero por la previsualización.
        return self._open_master_zpl_preview()

    def action_print_all_boxes(self):
        self.ensure_one()
        if not self.box_ids:
            raise UserError(_("La tarima no tiene cajas/bobinas para imprimir."))
        return self.box_ids.action_preview_zpl_boxes(pallet=self)

    def action_reprint_master_label(self):
        return self._open_master_zpl_preview()
