
from odoo import models, fields
class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'
    is_finished_product = fields.Boolean(string='Es Centro de Producto Terminado (Mamata/Embolsado)', help='Si se marca, al finalizar la OF permitirá iniciar el proceso de armado de tarimas')
