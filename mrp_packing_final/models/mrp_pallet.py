import base64

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpPallet(models.Model):
    _name = "mrp.pallet"
    _description = "Tarima / Pallet - Master"
    _order = "create_date desc"
    name = fields.Char(
        string="LOTE TARIMA",
        required=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("mrp.pallet")
        or "TR/NEW",
        copy=False,
    )
    production_id = fields.Many2one(
        "mrp.production",
        string="Orden de Fabricación",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        related="production_id.product_id", store=True, readonly=True
    )
    sale_order_id = fields.Many2one(related="production_id.sale_order_id", store=True)
    operator_id = fields.Many2one(
        "hr.employee",
        string="Operador",
        tracking=True,
        index=True,
    )
    machine = fields.Char(string="Máquina", default="Bolseadora Mamata 1")
    date_packing = fields.Datetime(
        string="Fecha Empaquetado", default=fields.Datetime.now
    )
    box_ids = fields.One2many("mrp.box", "pallet_id", string="Cajas")
    box_count = fields.Integer(compute="_compute_totals", store=True)
    total_gross_weight = fields.Float(
        string="Peso Bruto Total (KG)", compute="_compute_totals", store=True
    )
    total_net_weight = fields.Float(
        string="Peso Neto Total (KG)", compute="_compute_totals", store=True
    )
    total_qty = fields.Float(
        string="Cant. Total / QtyPerPallet", compute="_compute_totals", store=True
    )
    total_tara = fields.Float(
        string="TARA Total", compute="_compute_totals", store=True
    )
    customer_code = fields.Char(related="production_id.customer_code")
    customer_name = fields.Char(related="production_id.customer_name")
    customer_order_ref = fields.Char(related="production_id.customer_order_ref")
    zpl_pallet = fields.Text(string="ZPL Master Tarima", compute="_compute_zpl")

    @api.depends(
        "box_ids.peso_bruto", "box_ids.peso_neto", "box_ids.qty_per_box", "box_ids.tara"
    )
    def _compute_totals(self):
        for rec in self:
            rec.box_count = len(rec.box_ids)
            rec.total_gross_weight = sum(rec.box_ids.mapped("peso_bruto"))
            rec.total_net_weight = sum(rec.box_ids.mapped("peso_neto"))
            rec.total_qty = sum(rec.box_ids.mapped("qty_per_box"))
            rec.total_tara = sum(rec.box_ids.mapped("tara"))

    def _compute_zpl(self):
        for rec in self:
            rec.zpl_pallet = rec.generate_pallet_zpl()

    def generate_pallet_zpl(self):
        """Genera una etiqueta master 4x6, compuesta en orientación horizontal."""
        prod_code = self.product_id.default_code or ""
        prod_name = self.product_id.display_name or ""
        order_no = self.sale_order_id.name or ""
        customer_order = self.customer_order_ref or ""
        customer = self.customer_name or ""
        customer_code = self.customer_code or ""
        packed_date = (
            self.date_packing.strftime("%d/%m/%Y") if self.date_packing else ""
        )

        # 12 dots/mm: 6 pulgadas de ancho x 4 pulgadas de alto.
        return f"""^XA
^CI28
^PW1829
^LL1219
^LH0,0
^CF0,34
^FO35,32^FDJkk Pack^FS
^FO35,78^GB1760,2,2^FS
^CF0,24
^FO55,110^FDPedido / Order No.^FS
^A0N,42,42^FO55,145^FD{order_no}^FS
^CF0,24
^FO390,110^FDCod. Producto / Product No.^FS
^A0N,42,42^FO390,145^FD{prod_code}^FS
^FO870,110^FDCant. X Tarima / Qty Per Pallet^FS
^A0N,42,42^FO870,145^FD{self.total_qty:.2f}^FS
^FO1390,110^FDPedido Cliente / Customer PO^FS
^A0N,42,42^FO1390,145^FD{customer_order}^FS
^FO35,220^GB1760,2,2^FS
^CF0,24
^FO55,255^FDCajas o Rollos por Tarima / Boxes or Rolls per Pallet^FS
^A0N,44,44^FO55,292^FD{self.box_count}^FS
^FO390,255^FDPeso Bruto / Gross Weight^FS
^A0N,44,44^FO390,292^FD{self.total_gross_weight:.2f} KG^FS
^FO870,255^FDPeso Neto / Net Weight^FS
^A0N,44,44^FO870,292^FD{self.total_net_weight:.2f} KG^FS
^FO1390,255^FDFecha / Date^FS
^A0N,44,44^FO1390,292^FD{packed_date}^FS
^FO35,370^GB1760,2,2^FS
^CF0,27
^FO55,410^FB1680,3,34,L,0^FD{customer} - {customer_code}^FS
^FO55,540^FB1680,2,34,L,0^FD{prod_name}^FS
^FO55,660^GB790,2,2^FS
^FO55,690^FDEtiqueta Master / Master Label^FS
^BY4,3,190
^FO70,745^BCN,190,Y,N,N^FD{self.name}^FS
^FO1110,1030^FDImpreso por SAP^FS
^XZ"""

    def action_print_packing_list(self):
        return self.env.ref(
            "mrp_packing_final.action_report_packing_list"
        ).report_action(self)

    def action_print_browser_master(self):
        return {
            "type": "ir.actions.act_url",
            "url": f"/mrp_packing/print_pallet/{self.id}",
            "target": "new",
        }

    def action_download_zpl_master(self):
        self.ensure_one()
        zpl_code = self.generate_pallet_zpl()

        try:
            response = requests.post(
                "https://api.labelary.com/v1/printers/12dpmm/labels/6x4/0/",
                headers={"Accept": "image/png"},
                data=zpl_code.encode("utf-8"),
                timeout=10,
            )
        except requests.exceptions.RequestException as exc:
            raise UserError(
                _("No se pudo conectar con Labelary:\n%s") % str(exc)
            ) from exc

        if response.status_code != 200:
            raise UserError(
                _("Error de Labelary (%s):\n%s") % (response.status_code, response.text)
            )

        preview = self.env["pallet.label.preview.wizard"].create(
            {
                "pallet_id": self.id,
                "preview_image": base64.b64encode(response.content),
                "zpl_code": zpl_code,
            }
        )
        return {
            "name": _("Vista previa de etiqueta ZPL"),
            "type": "ir.actions.act_window",
            "res_model": "pallet.label.preview.wizard",
            "view_mode": "form",
            "res_id": preview.id,
            "target": "new",
        }

    def action_print_all_boxes(self):
        self.ensure_one()

        return self.env.ref(
            "mrp_packing_final.action_report_box_labels_zpl"
        ).report_action(self.box_ids)

    def action_reprint_master_label(self):
        return {
            "type": "ir.actions.act_window",
            "name": f"Etiqueta Master {self.name}",
            "res_model": "pallet.start.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_production_id": self.production_id.id,
                "default_pallet_id": self.id,
                "is_reprint": True,
            },
        }
