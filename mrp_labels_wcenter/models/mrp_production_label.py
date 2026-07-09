# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

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


# --- AGREGAMOS ESTO AQUÍ MISMO PARA FORZAR LA DETECCIÓN DEL BOTÓN ---
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    label_ids = fields.One2many('mrp.production.label', 'production_id', string="Etiquetas Emitidas")

    def action_open_label_wizard(self):
        self.ensure_one()
        # Sumamos los pesos de las etiquetas ya emitidas
        total_printed = sum(label.weight for label in self.label_ids)
        
        # Extraemos el valor bruto de la cantidad a producir directo de la pantalla principal de Odoo
        # Si qty_to_produce es cero por el estado de la MO, forzamos product_qty de forma estricta
        mo_total_qty = self.qty_to_produce if self.qty_to_produce > 0 else self.product_qty
        
        # Si necesitas que SIEMPRE muestre los 21.7070 ignorando lo que ya imprimiste antes, usa: weight_limit = mo_total_qty
        # Si prefieres que vaya restando el remanente, dejamos la resta:
        weight_limit = mo_total_qty - total_printed
        
        default_wc = self.workorder_ids[0].workcenter_id.id if self.workorder_ids else False

        return {
            'name': 'Generar Etiquetas de Producción por Rollo',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'default_mo_expected_weight': weight_limit if weight_limit > 0 else mo_total_qty,
                'default_workcenter_id': default_wc,
            }
        }
