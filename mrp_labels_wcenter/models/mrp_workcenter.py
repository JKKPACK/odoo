from odoo import fields, models

class MrpWorkCenter(models.Model):
    super_model = 'mrp.workcenter'
    _inherit = 'mrp.workcenter'

    label_prefix = fields.Char(string="Prefijo de Etiqueta", size=5, help="Prefijo para la nomenclatura de la etiqueta de producción.")
