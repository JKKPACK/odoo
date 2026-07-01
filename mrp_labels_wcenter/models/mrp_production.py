from odoo import models, fields, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    label_ids = fields.One2many('mrp.production.label', 'production_id', string="Etiquetas Emitidas")

    def action_open_label_wizard(self):
        self.ensure_one()
        # Calculamos la cantidad pendiente real a producir (Peso límite)
        # En Odoo 19, qty_to_produce o la diferencia entre qty_producing y product_qty
        weight_limit = self.product_qty - sum(label.weight for label in self.label_ids)
        
        return {
            'name': _('Generar Etiquetas de Producción por Rollo'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'default_mo_expected_weight': weight_limit if weight_limit > 0 else self.product_qty,
            }
        }
