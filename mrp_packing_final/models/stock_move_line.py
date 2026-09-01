import base64

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    x_calibre = fields.Float(string="Calibre", digits=(16, 2))
    x_ancho = fields.Float(string="Ancho (mm)", digits=(16, 2))
    x_factura_proveedor = fields.Char(string="Factura Proveedor")
    x_rollo_proveedor = fields.Char(string="Rollo Proveedor")
    x_lote_proveedor = fields.Char(string="Lote Proveedor")
    x_qr_content = fields.Char(
        compute="_compute_qr_content",
        string="Contenido Código QR",
    )
    x_expiration_date_text = fields.Char(
        compute="_compute_expiration_date_text",
        string="Fecha de Caducidad",
    )

    @api.depends("product_id", "lot_id", "lot_name", "quantity")
    def _compute_qr_content(self):
        for line in self:
            product_code = line.product_id.default_code or ""
            lot_name = line.lot_id.name or line.lot_name or ""
            qty = line.quantity or 0.0
            line.x_qr_content = f"{product_code}|{lot_name}|{qty:.2f}"


    @api.depends("lot_id", "lot_name", "product_id")
    def _compute_expiration_date_text(self):
        """Fecha de caducidad del lote sin forzar stock_expiration como dependencia."""
        Lot = self.env["stock.lot"]
        for line in self:
            lot = line.lot_id
            if not lot and line.lot_name and line.product_id:
                lot = Lot.search([
                    ("name", "=", line.lot_name),
                    ("product_id", "=", line.product_id.id),
                ], limit=1)
            value = False
            if lot:
                for field_name in ("expiration_date", "use_date", "life_date"):
                    if field_name in lot._fields and lot[field_name]:
                        value = lot[field_name]
                        break
            line.x_expiration_date_text = (
                value.strftime("%d/%m/%Y") if value and hasattr(value, "strftime")
                else (str(value) if value else False)
            )

    def _render_receipt_zpl(self, ids):
        zpl_bytes, _report_type = self.env["ir.actions.report"]._render_qweb_text(
            "mrp_packing_final.action_report_zebra_jkkpack",
            ids,
        )
        return zpl_bytes.decode("utf-8") if isinstance(zpl_bytes, bytes) else zpl_bytes

    def action_open_label_preview(self):
        if not self:
            raise UserError(_("Debe seleccionar al menos una línea."))

        # Labelary admite hasta 50 etiquetas por solicitud/flujo de vista previa.
        # Para selecciones mayores se evita cualquier llamada de preview y se
        # entrega directamente el ZPL qweb-text completo.
        if len(self) > 50:
            return self.env.ref(
                "mrp_packing_final.action_report_zebra_jkkpack"
            ).report_action(self.ids)

        zpl_all = self._render_receipt_zpl(self.ids)
        preview_lines = []
        for sequence, line in enumerate(self, start=1):
            zpl_preview = self._render_receipt_zpl([line.id])
            try:
                response = requests.post(
                    "https://api.labelary.com/v1/printers/12dpmm/labels/4x6/0/",
                    headers={"Accept": "image/png"},
                    data=zpl_preview.encode("utf-8"),
                    timeout=10,
                )
            except requests.exceptions.RequestException as exc:
                raise UserError(
                    _("No se pudo generar la vista previa con Labelary:\n%s") % str(exc)
                )

            if response.status_code != 200:
                raise UserError(
                    _("Error de Labelary (%s):\n%s")
                    % (response.status_code, response.text)
                )

            lot_name = line.lot_id.name or line.lot_name or _("Sin lote")
            preview_lines.append((0, 0, {
                "sequence": sequence,
                "name": _("Recepción %(receipt)s - Lote %(lot)s") % {
                    "receipt": line.picking_id.name or "",
                    "lot": lot_name,
                },
                "preview_image": base64.b64encode(response.content),
            }))

        wizard = self.env["stock.label.preview.wizard"].create({
            "move_line_id": self[0].id,
            "move_line_ids": [(6, 0, self.ids)],
            "preview_line_ids": preview_lines,
            "zpl_code": zpl_all,
        })
        return {
            "name": _("Etiquetas ZPL"),
            "type": "ir.actions.act_window",
            "res_model": "stock.label.preview.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def action_print_all_labels(self):
        return self.action_open_label_preview()
