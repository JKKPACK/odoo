import base64

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .zpl_utils import qty_text, zpl_safe


class MrpBox(models.Model):
    _name = "mrp.box"
    _description = "Caja/Bobina por Tarima"
    _order = "pallet_id, sequence, id"

    pallet_id = fields.Many2one(
        "mrp.pallet", string="Tarima", required=True, ondelete="cascade", index=True
    )
    production_id = fields.Many2one(
        related="pallet_id.production_id", store=True, index=True
    )
    product_id = fields.Many2one(
        related="pallet_id.product_id", store=True, index=True, readonly=True
    )
    name = fields.Char(
        string="ID Caja / Bobina", compute="_compute_name", store=True, index=True
    )
    sequence = fields.Integer(string="No. Caja/Bobina por tarima", required=True)
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote Maestro / Master Lot",
        index=True,
        domain="[('product_id', '=', product_id)]",
        help="ID/lote de la caja, rollo o bobina. Solo se permiten lotes del producto de la tarima.",
    )
    master_lot = fields.Char(
        string="Lote Maestro (texto)",
        help="Compatibilidad con registros históricos; los nuevos registros usan Lote Maestro.",
    )
    peso_bruto = fields.Float(string="Peso Bruto / Gross Weight", required=True)
    peso_neto = fields.Float(string="Peso Neto / Net Weight", required=True)
    tara = fields.Float(string="TARA", default=0.98)
    qty_per_box = fields.Float(string="Cantidad x Caja", default=2.0, required=True)
    mill_roll = fields.Float(string="Mill / Rollo", default=2.0)
    operator_id = fields.Many2one(
        "hr.employee",
        related="pallet_id.operator_id",
        string="Operador",
        store=True,
        readonly=True,
    )
    customer_item_no = fields.Char(
        related="pallet_id.production_id.customer_item_no", store=True
    )
    lot_code = fields.Char(compute="_compute_lot_code", string="Código de lote")
    qr_payload = fields.Char(compute="_compute_qr_payload", string="Contenido QR")
    zpl_box = fields.Text(compute="_compute_zpl", string="ZPL Caja/Bobina")

    @api.depends("lot_id.name", "master_lot", "pallet_id.name", "sequence")
    def _compute_name(self):
        for rec in self:
            # The PDF specification identifies each box/roll with its production lot.
            rec.name = rec.lot_id.name or rec.master_lot or f"{rec.pallet_id.name or 'NEW'}-{rec.sequence or 0}"

    @api.depends("lot_id.name", "master_lot")
    def _compute_lot_code(self):
        for rec in self:
            rec.lot_code = rec.lot_id.name or rec.master_lot or rec.name or ""

    @api.depends("pallet_id.product_id.default_code", "lot_code", "qty_per_box")
    def _compute_qr_payload(self):
        for rec in self:
            product_code = rec.pallet_id.product_id.default_code or ""
            rec.qr_payload = f"{product_code}/{rec.lot_code or ''}/{qty_text(rec.qty_per_box)}"

    @api.depends(
        "pallet_id.production_id.name",
        "pallet_id.product_id.default_code",
        "pallet_id.customer_code",
        "pallet_id.customer_label_text",
        "pallet_id.sale_order_id.name",
        "pallet_id.operator_id.name",
        "pallet_id.machine",
        "pallet_id.date_packing",
        "sequence",
        "lot_code",
        "peso_neto",
        "peso_bruto",
        "tara",
        "qty_per_box",
        "mill_roll",
        "customer_item_no",
    )
    def _compute_zpl(self):
        for rec in self:
            rec.zpl_box = rec.generate_box_zpl()

    @api.constrains("lot_id", "production_id", "product_id", "pallet_id")
    def _check_unique_lot_per_scope(self):
        for rec in self.filtered("lot_id"):
            if rec.lot_id.product_id != rec.product_id:
                raise ValidationError(_(
                    "El lote %(lot)s pertenece al producto %(lot_product)s y no al producto de la tarima %(pallet_product)s."
                ) % {
                    "lot": rec.lot_id.display_name,
                    "lot_product": rec.lot_id.product_id.display_name,
                    "pallet_product": rec.product_id.display_name,
                })

            domain = [("id", "!=", rec.id), ("lot_id", "=", rec.lot_id.id)]
            if rec.production_id:
                domain.append(("production_id", "=", rec.production_id.id))
                error = _("El lote %s ya fue empacado en otra caja/bobina de esta orden de fabricación.")
            else:
                domain += [("product_id", "=", rec.product_id.id)]
                error = _("El lote %s ya fue empacado en otra tarima de este producto.")

            if self.search_count(domain):
                raise ValidationError(error % rec.lot_id.display_name)

    @api.constrains("peso_bruto", "peso_neto", "tara", "qty_per_box")
    def _check_box_values(self):
        for rec in self:
            if rec.peso_bruto <= 0 or rec.peso_neto <= 0:
                raise ValidationError(_("Los pesos bruto y neto deben ser mayores a cero."))
            if rec.peso_neto > rec.peso_bruto:
                raise ValidationError(_("El peso neto no puede ser mayor que el peso bruto."))
            if rec.qty_per_box <= 0:
                raise ValidationError(_("La cantidad por caja/bobina debe ser mayor a cero."))

    def generate_box_zpl(self):
        """Etiqueta Caja/Bobina 4x6 pulgadas, vertical, 300 dpi (12 dpmm)."""
        self.ensure_one()
        pallet = self.pallet_id
        production = pallet.production_id
        manufacturing_no = production.name if production else _("MANUAL")
        product_code = zpl_safe(pallet.product_id.default_code)
        lot_code = zpl_safe(self.lot_code)
        operator = zpl_safe(pallet.operator_id.name)
        customer_code = zpl_safe(pallet.customer_code)
        customer_item = zpl_safe(self.customer_item_no)
        sale_order = zpl_safe(pallet.sale_order_id.name)
        customer_order = zpl_safe(pallet.customer_order_ref)
        label_text = zpl_safe(pallet.customer_label_text or pallet.product_id.display_name)
        machine = zpl_safe(pallet.machine)
        date_text = pallet.date_packing.strftime("%d/%m/%Y") if pallet.date_packing else ""
        qty = qty_text(self.qty_per_box)
        mill = qty_text(self.mill_roll)
        qr = zpl_safe(self.qr_payload)

        # 4 x 6 in @ 300 dpi: 1200 x 1800 dots. Portrait layout.
        return f"""^XA
^CI28
^PW1200
^LL1800
^LH0,0
^LS0
^PR4
^MD10
^FO25,25^GB1150,1745,3^FS
^FO45,45^GB1110,115,2^FS
^A0N,30,30^FO65,60^FDO. FAB / MFG NO.^FS
^A0N,45,45^FO65,98^FD{zpl_safe(manufacturing_no)}^FS
^A0N,30,30^FO575,60^FDCOD. PRODUCTO / PRODUCT NO.^FS
^A0N,43,43^FO575,98^FD{product_code}^FS

^FO45,180^GB1110,210,2^FS
^A0N,28,28^FO65,198^FDRollo Maestro / Master Roll^FS
^A0N,47,47^FO65,235^FD{lot_code}^FS
^A0N,28,28^FO720,198^FDCASE BOX ID #^FS
^A0N,58,58^FO780,240^FD{self.sequence}^FS
^A0N,25,25^FO65,315^FDCliente / Customer:^FS
^A0N,35,35^FO295,310^FD{customer_code}^FS
^A0N,25,25^FO650,315^FDFecha / Date:^FS
^A0N,35,35^FO820,310^FD{date_text}^FS

^FO45,410^GB1110,205,2^FS
^A0N,25,25^FO65,430^FDOperador / Operator^FS
^A0N,34,34^FO65,465^FD{operator}^FS
^A0N,25,25^FO600,430^FDMáquina / Machine^FS
^A0N,34,34^FO600,465^FD{machine}^FS
^A0N,23,23^FO65,525^FDPedido JkkPack / Sales Order^FS
^A0N,31,31^FO65,558^FD{sale_order}^FS
^A0N,23,23^FO430,525^FDPedido Cliente / Customer Order^FS
^A0N,31,31^FO430,558^FB430,1,34,L,0^FD{customer_order}^FS
^A0N,23,23^FO900,525^FDQty^FS
^A0N,31,31^FO900,558^FD{mill}^FS

^FO45,635^GB1110,250,2^FS
^A0N,26,26^FO65,655^FDDestiny / Customer Item #^FS
^A0N,43,43^FO65,692^FD{customer_item}^FS
^A0N,26,26^FO65,755^FDPeso Bruto / Gross Weight^FS
^A0N,42,42^FO65,792^FD{self.peso_bruto:.2f} KG^FS
^A0N,26,26^FO600,755^FDPeso Neto / Net Weight^FS
^A0N,42,42^FO600,792^FD{self.peso_neto:.2f} KG^FS

^FO45,905^GB1110,205,2^FS
^A0N,27,27^FO65,925^FDLeyenda Cliente / Customer Label Text^FS
^A0N,34,34^FO65,965^FB1060,3,40,L,0^FD{label_text}^FS

^A0N,24,24^FO65,1135^FDCustomer Item #^FS
^BY3,2,105
^FO65,1170^BCN,105,Y,N,N^FD{customer_item}^FS
^A0N,24,24^FO650,1135^FDQty Mill/Roll^FS
^BY3,2,105
^FO650,1170^BCN,105,Y,N,N^FD{qty}^FS

^A0N,24,24^FO65,1375^FDLote / Lot ID^FS
^BY3,2,120
^FO65,1410^BCN,120,Y,N,N^FD{lot_code}^FS
^FO865,1365^BQN,2,7^FDLA,{qr}^FS
^XZ"""

    def action_preview_zpl_boxes(self, pallet=None):
        """Previsualiza una o varias etiquetas 4x6 antes de enviarlas a Zebra."""
        boxes = self.sorted(lambda b: (b.pallet_id.id, b.sequence, b.id))
        if not boxes:
            raise UserError(_("No existen cajas/bobinas para previsualizar."))

        preview_lines = []
        all_zpl = []
        for index, box in enumerate(boxes, start=1):
            zpl_code = box.generate_box_zpl()
            all_zpl.append(zpl_code)
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
                    "No se pudo generar la previsualización de la caja/bobina %(box)s con Labelary.\n%(error)s"
                ) % {"box": box.display_name, "error": str(exc)}) from exc

            preview_lines.append((0, 0, {
                "sequence": index,
                "name": _("Caja/Bobina %(seq)s - %(lot)s") % {
                    "seq": box.sequence,
                    "lot": box.lot_code or box.name,
                },
                "preview_image": base64.b64encode(response.content),
                "zpl_code": zpl_code,
            }))

        pallet = pallet or (boxes[0].pallet_id if len(boxes.mapped("pallet_id")) == 1 else False)
        preview = self.env["pallet.label.preview.wizard"].create({
            "label_type": "box",
            "pallet_id": pallet.id if pallet else False,
            "box_ids": [(6, 0, boxes.ids)],
            "zpl_code": "\n".join(all_zpl),
            "preview_line_ids": preview_lines,
        })
        return {
            "name": _("Caja/Bobina ZPL 4x6"),
            "type": "ir.actions.act_window",
            "res_model": "pallet.label.preview.wizard",
            "view_mode": "form",
            "res_id": preview.id,
            "target": "new",
        }

    def action_print_browser_box(self):
        self.ensure_one()
        return self.action_preview_zpl_boxes(pallet=self.pallet_id)

    def action_download_zpl_box(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/mrp_packing/download_zpl_box/{self.id}",
            "target": "self",
        }
