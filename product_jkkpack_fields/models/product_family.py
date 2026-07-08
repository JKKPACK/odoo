# models/product_family.py
from odoo import models, fields

class ProductFamily(models.Model):
    _name = 'product.family'
    _description = 'Familia de producto'

    name = fields.Char(string="Nombre", required=True)
    description = fields.Text(string="Descripción")
