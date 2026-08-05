from odoo import fields, models


class PalletLabelPreviewWizard(models.TransientModel):
    _name = "pallet.label.preview.wizard"
    _description = "Vista previa de etiqueta ZPL de tarima"

    pallet_id = fields.Many2one(
        "mrp.pallet",
        string="Tarima",
        required=True,
        readonly=True,
    )
    preview_image = fields.Binary(
        string="Vista previa",
        readonly=True,
    )
    zpl_code = fields.Text(
        string="Código ZPL",
        readonly=True,
    )

    def action_print_zpl(self):
        self.ensure_one()
        return self.env.ref(
            "mrp_packing_final.action_report_pallet_zpl"
        ).report_action(self.pallet_id)
