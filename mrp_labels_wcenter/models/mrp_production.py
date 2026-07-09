from odoo import models, fields, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    label_ids = fields.One2many('mrp.production.label', 'production_id', string="Etiquetas Emitidas")

    def action_open_label_wizard(self):
        self.ensure_one()
        # Sumamos los pesos de etiquetas ya emitidas para esta orden
        total_printed = sum(label.weight for label in self.label_ids)
        # El límite restante debe ser el total de la orden menos lo ya pesado
        weight_limit = self.product_qty - total_printed
        
        # Encontrar el primer centro de trabajo de las operaciones para sugerirlo en el wizard
        default_wc = self.workorder_ids[0].workcenter_id.id if self.workorder_ids else False

        return {
            'name': 'Generar Etiquetas de Producción por Rollo',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'default_mo_expected_weight': weight_limit if weight_limit > 0 else self.product_qty,
                'default_workcenter_id': default_wc,
            }
        }
