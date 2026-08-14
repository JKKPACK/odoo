from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    packing_label_text = fields.Char(
        string="Texto para etiqueta de empaque",
        help=(
            "Texto comercial que debe imprimirse en las etiquetas de caja/bobina "
            "y en la etiqueta master de la tarima."
        ),
    )
