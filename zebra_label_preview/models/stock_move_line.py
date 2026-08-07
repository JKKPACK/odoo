# -*- coding: utf-8 -*-

import base64
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # ==========================================================
    # Campos personalizados
    # ==========================================================

    x_calibre = fields.Float(string="Calibre", digits=(16, 2))
    x_ancho = fields.Float(string="Ancho (mm)", digits=(16, 2))
    x_factura_proveedor = fields.Char(string="Factura Proveedor")
    x_rollo_proveedor = fields.Char(string="Rollo Proveedor")
    x_lote_proveedor = fields.Char(string="Lote Proveedor")

    x_qr_content = fields.Char(
        compute="_compute_qr_content",
        string="Contenido Código QR",
    )

    # ==========================================================
    # QR
    # ==========================================================

    @api.depends("product_id", "lot_id", "quantity")
    def _compute_qr_content(self):
        for line in self:
            product_code = line.product_id.default_code or ""
            lot_name = line.lot_name or ""
            qty = line.quantity or 0.0

            line.x_qr_content = f"{product_code}|{lot_name}|{qty:.2f}"

    # ==========================================================
    # Validaciones
    # ==========================================================

    # @api.onchange("quantity")
    # def _onchange_quantity_validate(self):
    #    for line in self:
    #        if not line.move_id:
    #            continue
    #
    #        demand = line.move_id.product_uom_qty
    #
    #        total = sum(
    #            line.move_id.move_line_ids.filtered(
    #                lambda l: l.product_id == line.product_id
    #            ).mapped("quantity")
    #        )
    #
    #        if total > demand:
    #            return {
    #                "warning": {
    #                    "title": _("Cantidad total excede la demanda"),
    #                    "message": _(
    #                        "La cantidad total (%s) no puede exceder la demanda (%s) para el producto %s"
    #                    )
    #                    % (
    #                        total,
    #                        demand,
    #                        line.product_id.display_name,
    #                    ),
    #                }
    #            }
    #
    # @api.constrains("quantity")
    # def _check_quantity_not_exceeds_demand(self):
    #    for line in self:
    #        if not line.move_id:
    #            continue
    #
    #        demand = line.move_id.product_uom_qty
    #
    #        total = sum(
    #            line.move_id.move_line_ids.filtered(
    #                lambda l: l.product_id == line.product_id
    #            ).mapped("quantity")
    #        )
    #
    #        if total > demand:
    #            raise UserError(
    #                _(
    #                    "La cantidad total (%s) no puede exceder la demanda (%s) para el producto %s"
    #                )
    #                % (
    #                    total,
    #                    demand,
    #                    line.product_id.display_name,
    #                )
    #            )
    #
    # ==========================================================
    # Utilidades
    # ==========================================================

    def _render_zpl(self, ids):
        report = self.env["ir.actions.report"]

        zpl_bytes, report_type = report._render_qweb_text(
            "zebra_label_preview.action_report_zebra_jkkpack",
            ids,
        )

        return zpl_bytes.decode("utf-8") if isinstance(zpl_bytes, bytes) else zpl_bytes

    # ==========================================================
    # Vista previa
    # ==========================================================

    def action_open_label_preview(self):

        if not self:
            raise UserError(_("Debe seleccionar al menos una línea."))

        # ZPL COMPLETO
        zpl_all = self._render_zpl(self.ids)

        # SOLO PRIMERA ETIQUETA
        zpl_preview = self._render_zpl([self[0].id])

        try:

            response = requests.post(
                "http://api.labelary.com/v1/printers/12dpmm/labels/4x6/0/",
                headers={
                    "Accept": "image/png",
                },
                data=zpl_preview.encode("utf-8"),
                timeout=10,
            )

        except requests.exceptions.RequestException as exc:
            raise UserError(_("No se pudo conectar con Labelary:\n%s") % str(exc))

        if response.status_code != 200:
            raise UserError(
                _("Error de Labelary (%s):\n%s")
                % (
                    response.status_code,
                    response.text,
                )
            )

        wizard = self.env["stock.label.preview.wizard"].create(
            {
                "move_line_id": self[0].id,
                "preview_image": base64.b64encode(response.content).decode(),
                "zpl_code": zpl_all,
            }
        )

        return {
            "name": _("Vista previa de etiquetas (%d)") % len(self),
            "type": "ir.actions.act_window",
            "res_model": "stock.label.preview.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    # ==========================================================
    # Imprimir
    # ==========================================================

    def action_print_all_labels(self):
        """
        Genera el ZPL completo para todas las etiquetas.

        La vista previa utiliza únicamente la primera etiqueta,
        mientras que el wizard almacena el ZPL completo listo para
        imprimir.
        """

        return self.action_open_label_preview()
