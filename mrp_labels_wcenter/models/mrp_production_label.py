from odoo import models, fields, api

class MrpProductionLabel(models.Model):
    _name = 'mrp.production.label'
    _description = 'Etiquetas por Rollo / Caja de Producción'
    _order = 'id desc'

    name = fields.Char(string="Código de Barra / Lote Interno", required=True, copy=False, readonly=True)
    production_id = fields.Many2one('mrp.production', string="Orden de Fabricación", ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', related='production_id.product_id', store=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string="Centro de Trabajo", required=True)
    weight = fields.Float(string="Peso (KG)", digits=(16, 4), required=True)
    date_produced = fields.Datetime(string="Fecha de Producción", default=fields.Datetime.now)
    operator_id = fields.Many2one('res.users', string="Operador", default=lambda self: self.env.user)

    # Campos adicionales solicitados para la estructura de la etiqueta
   # caliber = fields.Float(string="Calibre", related='product_id.product_tmpl_id.caliber_field_custom', readonly=False) # Ajustar al campo real en tu product.template
   # width = fields.Float(string="Ancho", related='product_id.product_tmpl_id.width_field_custom', readonly=False)   # Ajustar al campo real
