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
        "customer_order_ref", "customer_name", "customer_code", "customer_label_text",
        "date_packing", "box_count", "total_gross_weight", "total_net_weight", "total_qty",
    )
    def _compute_zpl(self):
        for rec in self:
            rec.zpl_pallet = rec.generate_pallet_zpl()

    @api.constrains("box_ids")
    def _check_pallet_has_unique_lots(self):
        for rec in self:
            lots = rec.box_ids.filtered("lot_id").mapped("lot_id")
            if len(lots) != len(set(lots.ids)):
                raise ValidationError(_("No se puede repetir un lote dentro de la misma tarima."))

    def _master_label_values(self):
        """Valores comunes para la vista previa y la impresión física de la Master."""
        self.ensure_one()
        return {
            "product_code": zpl_safe(self.product_id.default_code),
            "order_no": zpl_safe(self.sale_order_id.name or (self.production_id and self.production_id.name) or _("MANUAL")),
            "customer_order": zpl_safe(self.customer_order_ref),
            "label_text": zpl_safe(self.customer_label_text or self.product_id.display_name),
            "packed_date": self.date_packing.strftime("%d/%m/%Y") if self.date_packing else "",
            "qr": zpl_safe(self.qr_payload),
            "pallet": zpl_safe(self.name),
            "qty": qty_text(self.total_qty),
            "boxes": self.box_count,
            "gross": f"{self.total_gross_weight:.2f}",
            "net": f"{self.total_net_weight:.2f}",
        }

    def generate_pallet_preview_zpl(self):
        """Master 6x4 horizontal para pantalla/Labelary (1800x1200 @ 300 dpi)."""
        self.ensure_one()
        v = self._master_label_values()
        return f"""^XA
^CI28
^PW1800
^LL1200
^LH0,0
^LS0
^PR4
^MD10
^FO25,25^GB1750,1150,3^FS
^A0N,32,32^FO55,45^FDETIQUETA MASTER / MASTER PALLET LABEL^FS
^FO45,90^GB1710,2,2^FS

^A0N,27,27^FO60,120^FDPedido / Order No.^FS
^A0N,48,48^FO60,158^FD{v['order_no']}^FS
^A0N,27,27^FO560,120^FDCod. Producto / Product No.^FS
^A0N,48,48^FO560,158^FD{v['product_code']}^FS
^A0N,27,27^FO1230,120^FDCant X Tarima / Qty Per Pallet^FS
^A0N,52,52^FO1230,158^FD{v['qty']}^FS
^FO45,235^GB1710,2,2^FS

^A0N,27,27^FO60,265^FDPedido Cliente / Customer Order No.^FS
^A0N,43,43^FO60,305^FB500,1,48,L,0^FD{v['customer_order']}^FS
^A0N,27,27^FO610,265^FDCajas o Rollos por Tarima^FS
^A0N,26,26^FO610,300^FDBoxes or Rolls per Pallet^FS
^A0N,52,52^FO610,338^FD{v['boxes']}^FS
^A0N,27,27^FO1210,265^FDPeso Bruto / Gross Weight^FS
^A0N,52,52^FO1210,305^FD{v['gross']} KG^FS
^FO45,405^GB1710,2,2^FS

^A0N,27,27^FO60,435^FDFecha / Date^FS
^A0N,44,44^FO60,475^FD{v['packed_date']}^FS
^A0N,27,27^FO610,435^FDPeso Neto / Net Weight^FS
^A0N,52,52^FO610,475^FD{v['net']} KG^FS
^A0N,27,27^FO1210,435^FDTarima / Pallet ID^FS
^A0N,48,48^FO1210,475^FD{v['pallet']}^FS
^FO45,555^GB1710,2,2^FS

^A0N,27,27^FO60,585^FDLeyenda Cliente / Customer Label Text^FS
^A0N,34,34^FO60,625^FB1660,3,40,L,0^FD{v['label_text']}^FS
^FO45,770^GB1710,2,2^FS

^A0N,25,25^FO80,800^FDTarima / Pallet ID^FS
^BY4,2,145
^FO80,840^BCN,145,Y,N,N^FD{v['pallet']}^FS
^FO1430,830^BQN,2,7^FDLA,{v['qr']}^FS
^XZ"""

    def generate_pallet_zpl(self):
        """Master 6x4 para Zebra de 4 pulgadas.

        La etiqueta física es 6x4, pero una ZT411 imprime sobre 4 pulgadas de ancho y
        6 pulgadas de avance. Por eso se usa un lienzo 4x6 (1200x1800 dots) y todo el
        contenido se rota 90 grados. Al salir de la impresora, la Master queda 6x4
        horizontal sin recortar texto.
        """
        self.ensure_one()
        v = self._master_label_values()

        # Media física: 4 x 6 in @ 300 dpi. Campos rotados a la derecha (R).
        # Tras girar la etiqueta físicamente, el diseño corresponde a 6 x 4 horizontal.
        return f"""^XA
^CI28
^PW1200
^LL1800
^LH0,0
^LS0
^PR4
^MD10

^FO25,25^GB1150,1750,3^FS
^FO1085,45^GB2,1710,2^FS
^A0R,32,32^FO1125,55^FDETIQUETA MASTER / MASTER PALLET LABEL^FS

^A0R,27,27^FO1050,60^FDPedido / Order No.^FS
^A0R,48,48^FO1010,60^FD{v['order_no']}^FS
^A0R,27,27^FO1050,560^FDCod. Producto / Product No.^FS
^A0R,46,46^FO1010,560^FD{v['product_code']}^FS
^A0R,27,27^FO1050,1230^FDCant X Tarima / Qty Per Pallet^FS
^A0R,52,52^FO1010,1230^FD{v['qty']}^FS
^FO930,45^GB2,1710,2^FS

^A0R,27,27^FO895,60^FDPedido Cliente / Customer Order No.^FS
^A0R,40,40^FO850,60^FB500,1,44,L,0^FD{v['customer_order']}^FS
^A0R,27,27^FO895,610^FDCajas o Rollos por Tarima^FS
^A0R,25,25^FO860,610^FDBoxes or Rolls per Pallet^FS
^A0R,52,52^FO815,610^FD{v['boxes']}^FS
^A0R,27,27^FO895,1210^FDPeso Bruto / Gross Weight^FS
^A0R,52,52^FO850,1210^FD{v['gross']} KG^FS
^FO765,45^GB2,1710,2^FS

^A0R,27,27^FO730,60^FDFecha / Date^FS
^A0R,44,44^FO685,60^FD{v['packed_date']}^FS
^A0R,27,27^FO730,610^FDPeso Neto / Net Weight^FS
^A0R,52,52^FO685,610^FD{v['net']} KG^FS
^A0R,27,27^FO730,1210^FDTarima / Pallet ID^FS
^A0R,48,48^FO685,1210^FD{v['pallet']}^FS
^FO590,45^GB2,1710,2^FS

^A0R,27,27^FO555,60^FDLeyenda Cliente / Customer Label Text^FS
^A0R,33,33^FO510,60^FB1660,3,39,L,0^FD{v['label_text']}^FS
^FO370,45^GB2,1710,2^FS

^A0R,25,25^FO335,80^FDTarima / Pallet ID^FS
^BY4,2,145
^FO295,80^BCR,145,Y,N,N^FD{v['pallet']}^FS
^FO70,1370^BQR,2,7^FDLA,{v['qr']}^FS
^XZ"""

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
        zpl_code = self.generate_pallet_preview_zpl()
        try:
            response = requests.post(
                "https://api.labelary.com/v1/printers/12dpmm/labels/6x4/0/",
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

    def action_download_zpl_master(self):
        # Compatibilidad con acciones antiguas: ya no existe un botón separado.
        return self._open_master_zpl_preview()

    def action_print_all_boxes(self):
        self.ensure_one()
        if not self.box_ids:
            raise UserError(_("La tarima no tiene cajas/bobinas para imprimir."))
        return self.box_ids.action_preview_zpl_boxes(pallet=self)

    def action_reprint_master_label(self):
        return self._open_master_zpl_preview()
