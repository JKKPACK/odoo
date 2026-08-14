from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    is_finished_product = fields.Boolean(
        string="Es Centro de Producto Terminado (Mamata/Embolsado)",
        help="Marca el centro de trabajo desde el que se realiza el etiquetado final.",
    )
