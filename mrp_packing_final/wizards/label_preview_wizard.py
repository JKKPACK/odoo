from odoo import _, fields, models
from odoo.exceptions import UserError


class PalletLabelPreviewWizard(models.TransientModel):
    _name = "pallet.label.preview.wizard"
    _description = "Etiquetas ZPL"

    label_type = fields.Selection(
        [("master", "Master 6x4"), ("box", "Caja/Bobina 4x6")],
        string="Tipo de etiqueta",
        required=True,
        readonly=True,
    )
    pallet_id = fields.Many2one("mrp.pallet", string="Tarima", readonly=True)
    box_ids = fields.Many2many("mrp.box", string="Cajas/Bobinas", readonly=True)
    preview_line_ids = fields.One2many(
        "pallet.label.preview.line", "wizard_id", string="Etiquetas", readonly=True
    )
    zpl_code = fields.Text(string="Código ZPL completo", readonly=True)
    label_count = fields.Integer(string="Etiquetas", compute="_compute_label_count")

    def _compute_label_count(self):
        for wizard in self:
            wizard.label_count = len(wizard.preview_line_ids)

    def action_print_zpl(self):
        self.ensure_one()
        if self.label_type == "master":
            if not self.pallet_id:
                raise UserError(_("No se encontró la tarima de la etiqueta Master."))
            return self.env.ref(
                "mrp_packing_final.action_report_pallet_zpl"
            ).report_action(self.pallet_id)

        if not self.box_ids:
            raise UserError(_("No existen cajas/bobinas para imprimir."))
        return self.env.ref(
            "mrp_packing_final.action_report_box_labels_zpl"
        ).report_action(self.box_ids)


class PalletLabelPreviewLine(models.TransientModel):
    _name = "pallet.label.preview.line"
    _description = "Línea de etiqueta ZPL"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "pallet.label.preview.wizard", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Etiqueta", readonly=True)
    preview_image = fields.Binary(string="Etiqueta", readonly=True)
    zpl_code = fields.Text(string="ZPL", readonly=True)
