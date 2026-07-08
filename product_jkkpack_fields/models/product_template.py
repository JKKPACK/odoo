# models/product_template.py
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_width = fields.Char(string="Ancho")
    x_caliber = fields.Char(string="Calibre")
    x_density = fields.Char(string="Densidad")
    x_conversion_factor = fields.Float(string="Factor de conversión")
    x_product_family_id = fields.Many2one(
        'product.family',
        string="Familia de producto"
    )
