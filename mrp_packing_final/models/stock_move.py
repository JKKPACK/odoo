from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_round


class StockMove(models.Model):
    _inherit = "stock.move"

    line_number = fields.Integer(
        compute="_compute_line_number",
        string="#",
    )
    location_internal_id = fields.Integer(
        compute="_compute_location_internal_id",
        string="Almacén",
    )

    @api.depends(
        "raw_material_production_id",
        "raw_material_production_id.move_raw_ids.sequence",
    )
    def _compute_line_number(self):
        # Always initialize to avoid stale values on moves outside an MO.
        for move in self:
            move.line_number = 0
        for production in self.mapped("raw_material_production_id"):
            for index, move in enumerate(
                production.move_raw_ids.sorted("sequence"), start=1
            ):
                move.line_number = index

    @api.depends("location_id")
    def _compute_location_internal_id(self):
        for move in self:
            move.location_internal_id = move.location_id.id if move.location_id else False

    def _is_inbound_receipt(self):
        """Return True only for a normal supplier -> internal receipt."""
        self.ensure_one()
        if "Devolución" in (self.origin or ""):
            return False
        return (
            self.location_id.usage == "supplier"
            and self.location_dest_id.usage == "internal"
        )

    def _is_return_move(self):
        """Detect supplier returns without changing other stock flows."""
        self.ensure_one()
        is_return_location = (
            self.location_id.usage == "internal"
            and self.location_dest_id.usage == "supplier"
        )
        is_return_document = "Devolución" in (self.origin or "")
        return is_return_location or is_return_document

    def _action_done(self, cancel_backorder=False):
        # Preserve the original jkk_report safeguard: only purchase receipts are
        # validated, returns and non-purchase stock flows are untouched.
        for move in self:
            if not (
                move.purchase_line_id
                and move.product_id
                and move.quantity
                and move._is_inbound_receipt()
                and not move._is_return_move()
            ):
                continue

            purchase_line = move.purchase_line_id
            ordered_qty = purchase_line.product_qty
            previous_received = sum(
                purchase_line.move_ids.filtered(
                    lambda candidate: (
                        candidate.state == "done"
                        and candidate.id != move.id
                        and candidate._is_inbound_receipt()
                        and not candidate._is_return_move()
                    )
                ).mapped("quantity")
            )
            total_received = previous_received + move.quantity

            # Compare using the product UoM precision. A direct float comparison
            # can reject a valid receipt because values such as
            # 2166.00 + 2078.86 may internally become 4244.860000000001.
            rounding = purchase_line.product_uom.rounding or 0.01
            if float_compare(
                total_received,
                ordered_qty,
                precision_rounding=rounding,
            ) > 0:
                ordered_display = float_round(ordered_qty, precision_rounding=rounding)
                previous_display = float_round(previous_received, precision_rounding=rounding)
                current_display = float_round(move.quantity, precision_rounding=rounding)
                total_display = float_round(total_received, precision_rounding=rounding)
                raise ValidationError(
                    _(
                        "No puede recibir más cantidad de la comprada.\n\n"
                        "Producto: %s\n"
                        "Cantidad solicitada: %s\n"
                        "Cantidad recibida anteriormente: %s\n"
                        "Cantidad que intenta recibir: %s\n"
                        "Total recibido: %s"
                    )
                    % (
                        move.product_id.display_name,
                        ordered_display,
                        previous_display,
                        current_display,
                        total_display,
                    )
                )

        return super()._action_done(cancel_backorder)

    def action_print_all_labels_from_move(self):
        """Preview/print all Zebra receipt labels for this stock move."""
        self.ensure_one()
        move_lines = self.move_line_ids.filtered(lambda line: line.product_id)
        if not move_lines:
            raise UserError(_("Este movimiento no tiene líneas para imprimir"))
        return move_lines.action_open_label_preview()

    def action_print_physical_label_from_move(self):
        """Generate all receipt-label ZPL directly, without a preview."""
        self.ensure_one()
        move_lines = self.move_line_ids.filtered(lambda line: line.product_id)
        if not move_lines:
            raise UserError(_("Este movimiento no tiene líneas para imprimir"))
        return self.env.ref(
            "mrp_packing_final.action_report_zebra_jkkpack"
        ).report_action(move_lines.ids)
