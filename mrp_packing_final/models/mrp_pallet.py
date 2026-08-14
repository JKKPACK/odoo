import base64

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .zpl_utils import qty_text, zpl_safe


class MrpPallet(models.Model):
    _name = "mrp.pallet"
    _description = "Tarima / Pallet - Master"
    _order = "create_date desc"

    name = fields.Char(
        string="LOTE TARIMA",
        required=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("mrp.pallet") or "TR/NEW",
        copy=False,
        index=True,
    )
    production_id = fields.Many2one(
        "mrp.production", string="Orden de Fabricación", required=True, ondelete="cascade", index=True
    )
    product_id = fields.Many2one(related="production_id.product_id", store=True, readonly=True)
    sale_order_id = fields.Many2one(related="production_id.sale_order_id", store=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Centro de Trabajo")
    operator_id = fields.Many2one("hr.employee", string="Operador", index=True)
    machine = fields.Char(string="Máquina")
    date_packing = fields.Datetime(string="Fecha Empaquetado", default=fields.Datetime.now, required=True)
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
    customer_label_text = fields.Char(related="production_id.customer_label_text")
    qr_payload = fields.Char(compute="_compute_qr_payload", string="Contenido QR Master")
    zpl_pallet = fields.Text(string="ZPL Master Tarima", compute="_compute_zpl")

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
        "name", "product_id.default_code", "product_id.name", "sale_order_id.name",
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

    def generate_pallet_zpl(self):
        """Etiqueta Master 6x4 pulgadas, horizontal, 300 dpi (12 dpmm)."""
        self.ensure_one()
        product_code = zpl_safe(self.product_id.default_code)
        order_no = zpl_safe(self.sale_order_id.name)
        customer_order = zpl_safe(self.customer_order_ref)
        label_text = zpl_safe(self.customer_label_text or self.product_id.display_name)
        packed_date = self.date_packing.strftime("%d/%m/%Y") if self.date_packing else ""
        qr = zpl_safe(self.qr_payload)

        # 6 x 4 in @ 300 dpi: 1800 x 1200 dots. Landscape layout.
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
^A0N,48,48^FO60,158^FD{order_no}^FS
^A0N,27,27^FO560,120^FDCod. Producto / Product No.^FS
^A0N,48,48^FO560,158^FD{product_code}^FS
^A0N,27,27^FO1230,120^FDCant X Tarima / Qty Per Pallet^FS
^A0N,52,52^FO1230,158^FD{qty_text(self.total_qty)}^FS
^FO45,235^GB1710,2,2^FS

^A0N,27,27^FO60,265^FDPedido Cliente / Customer Order No.^FS
^A0N,48,48^FO60,305^FD{customer_order}^FS
^A0N,27,27^FO610,265^FDCajas o Rollos por Tarima^FS
^A0N,26,26^FO610,300^FDBoxes or Rolls per Pallet^FS
^A0N,52,52^FO610,338^FD{self.box_count}^FS
^A0N,27,27^FO1210,265^FDPeso Bruto / Gross Weight^FS
^A0N,52,52^FO1210,305^FD{self.total_gross_weight:.2f} KG^FS
^FO45,405^GB1710,2,2^FS

^A0N,27,27^FO60,435^FDFecha / Date^FS
^A0N,44,44^FO60,475^FD{packed_date}^FS
^A0N,27,27^FO610,435^FDPeso Neto / Net Weight^FS
^A0N,52,52^FO610,475^FD{self.total_net_weight:.2f} KG^FS
^A0N,27,27^FO1210,435^FDTarima / Pallet ID^FS
^A0N,48,48^FO1210,475^FD{zpl_safe(self.name)}^FS
^FO45,555^GB1710,2,2^FS

^A0N,27,27^FO60,585^FDDescripción / Description^FS
^A0N,37,37^FO60,625^FB1660,3,42,L,0^FD{label_text}^FS
^FO45,760^GB1710,2,2^FS

^A0N,25,25^FO80,790^FDTarima / Pallet ID^FS
^BY4,2,150
^FO80,830^BCN,150,Y,N,N^FD{zpl_safe(self.name)}^FS
^FO1370,790^BQN,2,8^FDLA,{qr}^FS
^A0N,20,20^FO1310,1090^FB390,2,24,C,0^FDArticulo/Tarima/Cantidad^FS
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
        zpl_code = self.generate_pallet_zpl()
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
