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
        related="pallet_id.production_id", store=True, index=True,
        help="Producción principal asociada a la tarima."
    )
    source_production_id = fields.Many2one(
        "mrp.production",
        string="Producción origen",
        index=True,
        ondelete="set null",
        help="Producción principal o parcial que generó el lote de esta caja/bobina.",
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
    expiration_date_text = fields.Char(
        compute="_compute_expiration_date_text",
        string="Fecha Caducidad",
        help=(
            "Fecha de caducidad tomada de la producción origen de la caja/bobina. "
            "Para tarimas manuales, si no existe producción, se intenta tomar del lote."
        ),
    )
    zpl_box = fields.Text(compute="_compute_zpl", string="ZPL Caja/Bobina")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("source_production_id") and vals.get("pallet_id"):
                pallet = self.env["mrp.pallet"].browse(vals["pallet_id"])
                vals["source_production_id"] = pallet.production_id.id or False
        return super().create(vals_list)

    @api.depends("lot_id.name", "master_lot", "pallet_id.name", "sequence")
    def _compute_name(self):
        for rec in self:
            # The PDF specification identifies each box/roll with its production lot.
            rec.name = rec.lot_id.name or rec.master_lot or f"{rec.pallet_id.name or 'NEW'}-{rec.sequence or 0}"

    @api.depends("lot_id.name", "master_lot")
    def _compute_lot_code(self):
        for rec in self:
            rec.lot_code = rec.lot_id.name or rec.master_lot or rec.name or ""

    @api.depends(
        "source_production_id.expiration_date",
        "production_id.expiration_date",
        "lot_id",
        "lot_id.write_date",
    )
    def _compute_expiration_date_text(self):
        """Fecha de caducidad de la producción que originó la caja/bobina.

        El flujo productivo ya dispone del campo ``mrp.production.expiration_date``.
        Para empaquetado agrupado se respeta la producción parcial de origen; para
        el flujo individual se usa la producción de la tarima. Solo las tarimas
        manuales, que no tienen producción, conservan el lote como respaldo.
        """
        for rec in self:
            production = rec.source_production_id or rec.production_id
            value = production.expiration_date if production else False

            # Respaldo exclusivo para tarimas manuales sin una OF asociada.
            if not value and not production and rec.lot_id:
                lot = rec.lot_id
                for field_name in ("expiration_date", "use_date", "life_date"):
                    if field_name in lot._fields and lot[field_name]:
                        value = lot[field_name]
                        break

            rec.expiration_date_text = (
                value.strftime("%d/%m/%Y")
                if value and hasattr(value, "strftime")
                else (str(value) if value else False)
            )

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
        "expiration_date_text",
    )
    def _compute_zpl(self):
        for rec in self:
            rec.zpl_box = rec.render_box_zpl()

    @api.constrains("lot_id", "source_production_id", "production_id", "product_id", "pallet_id")
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
            if rec.source_production_id:
                domain += [
                    "|",
                    ("source_production_id", "=", rec.source_production_id.id),
                    "&", ("source_production_id", "=", False), ("production_id", "=", rec.source_production_id.id),
                ]
                error = _("El lote %s ya fue empacado en otra caja/bobina de esta producción.")
            elif rec.production_id:
                # Compatibilidad con registros históricos previos al campo producción origen.
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

    def _zpl_safe(self, value):
        """Sanitiza únicamente datos variables; el layout ZPL vive en QWeb-text."""
        return zpl_safe(value)

    def _zpl_qty(self, value):
        return qty_text(value)

    def _zpl_date(self, value):
        return value.strftime("%d/%m/%Y") if value else ""

    def render_box_zpl(self):
        """Renderiza la etiqueta 4x6 desde su plantilla QWeb-text real."""
        self.ensure_one()
        content = self.env["ir.actions.report"]._render_template(
            "mrp_packing_final.report_box_labels_zpl",
            {
                "doc_ids": self.ids,
                "doc_model": self._name,
                "docs": self,
            },
        )
        return content.decode("utf-8") if isinstance(content, bytes) else str(content)

    def action_preview_zpl_boxes(self, pallet=None):
        """Previsualiza una o varias etiquetas 4x6 antes de enviarlas a Zebra."""
        boxes = self.sorted(lambda b: (b.pallet_id.id, b.sequence, b.id))
        if not boxes:
            raise UserError(_("No existen cajas/bobinas para previsualizar."))

        # Labelary limita la previsualización a un máximo operativo de 50 etiquetas.
        # Para lotes mayores generamos directamente el reporte qweb-text completo,
        # evitando llamadas de previsualización y conservando todas las etiquetas
        # en el ZPL final.
        if len(boxes) > 50:
            return self.env.ref(
                "mrp_packing_final.action_report_box_labels_zpl"
            ).report_action(boxes)

        preview_lines = []
        all_zpl = []
        for index, box in enumerate(boxes, start=1):
            zpl_code = box.render_box_zpl()
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
