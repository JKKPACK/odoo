from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockLabelPreviewWizard(models.TransientModel):
    _name = "stock.label.preview.wizard"
    _description = "Etiquetas Zebra de Recepción"

    move_line_id = fields.Many2one(
        "stock.move.line", string="Línea de Movimiento", readonly=True
    )
    move_line_ids = fields.Many2many(
        "stock.move.line", string="Líneas a imprimir", readonly=True
    )
    preview_line_ids = fields.One2many(
        "stock.label.preview.line", "wizard_id", string="Vistas previas", readonly=True
    )
    zpl_code = fields.Text(string="Código Fuente ZPL", readonly=True)
    label_count = fields.Integer(string="Cantidad de etiquetas", compute="_compute_label_count")

    @api.depends("preview_line_ids")
    def _compute_label_count(self):
        for wizard in self:
            wizard.label_count = len(wizard.preview_line_ids)

    def action_print_physical_label(self):
        self.ensure_one()
        lines = self.move_line_ids or self.move_line_id
        if not lines:
            raise UserError(_("No hay líneas para imprimir"))
        return self.env.ref(
            "mrp_packing_final.action_report_zebra_jkkpack"
        ).report_action(lines.ids)


class StockLabelPreviewLine(models.TransientModel):
    _name = "stock.label.preview.line"
    _description = "Línea de Vista Previa Zebra de Recepción"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "stock.label.preview.wizard", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Nombre de etiqueta", readonly=True)
    preview_image = fields.Binary(string="Imagen de etiqueta", readonly=True)
