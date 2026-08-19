from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    packing_label_text = fields.Text(
        string="Leyenda para etiquetas de empaque",
        help=(
            "Leyenda proporcionada por el cliente. Se imprime en las etiquetas de caja/bobina "
            "y en la etiqueta Master de la tarima."
        ),
    )
