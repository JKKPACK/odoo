from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MrpProductionLabelWizard(models.TransientModel):
    _name = 'mrp.production.label.wizard'
    _description = 'Asistente de Pesaje y Etiquetado'

    production_id = fields.Many2one('mrp.production', string="Orden de Fabricación", required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string="Centro de Trabajo Originario", required=True)
    qty_labels = fields.Integer(string="Número de Etiquetas (Rollos/Cajas)", default=1, required=True)
    
    # Datos de control de peso para la validación en tiempo real
    mo_expected_weight = fields.Float(string="Límite por Producir (KG)", digits=(16, 4), readonly=True)
    line_ids = fields.One2many('mrp.production.label.wizard.line', 'wizard_id', string="Pesaje de Rollos")

    @api.onchange('qty_labels')
    def _onchange_qty_labels(self):
        """Genera dinámicamente las líneas de captura conforme el usuario cambia el número de etiquetas"""
        commands = [(5, 0, 0)] # Limpiar líneas existentes
        for i in range(self.qty_labels):
            commands.append((0, 0, {
                'sequence_no': i + 1,
                'weight': 0.0
            }))
        self.line_ids = commands

    def generate_and_print_labels(self):
        self.ensure_one()
        # 1. Validar que el peso total ingresado coincida con la tolerancia/límite de la parcialidad de la MO
        total_wizard_weight = sum(line.weight for line in self.line_ids)
        
        if total_wizard_weight <= 0:
            raise ValidationError(_("El peso total de los rollos debe ser mayor a cero."))
            
        # Validación estricta del límite contra el total marcado en rojo en tu imagen (Cantidad Pendiente / Parcial de la MO)
        if total_wizard_weight > self.mo_expected_weight:
            raise ValidationError(_(
                "El peso total de las etiquetas (%(total)s kg) excede el peso límite de la orden de fabricación (%(limit)s kg).",
                total=total_wizard_weight, limit=self.mo_expected_weight
            ))

        created_labels = self.env['mrp.production.label']
        prefix = self.workcenter_id.label_prefix or 'GEN'

        for line in self.line_ids:
            if line.weight <= 0:
                raise ValidationError(_("Cada rollo/etiqueta debe tener un peso asignado válido."))
                
            # PRIORIDAD: 1. Prefijo personalizado -> 2. Código nativo del Centro de Trabajo -> 3. "GEN" de respaldo
            prefix = self.workcenter_id.label_prefix or self.workcenter_id.code or 'GEN'
            
            # Consumir la secuencia global infinita
            seq_num = self.env['ir.sequence'].next_by_code('mrp.production.label.sequence')
            label_name = f"{prefix}{seq_num}"

            label = self.env['mrp.production.label'].create({
                'name': label_name,
                'production_id': self.production_id.id,
                'workcenter_id': self.workcenter_id.id,
                'weight': line.weight,
            })
            created_labels |= label
    

        # Retornar la acción de impresión del reporte QWeb con los registros recién creados
        return self.env.ref('mrp_labels_wcenter.action_report_production_labels').report_action(created_labels)


class MrpProductionLabelWizardLine(models.TransientModel): #  Correcto
    _name = 'mrp.production.label.wizard.line'
    _description = 'Línea de captura individual de Peso'

    wizard_id = fields.Many2one('mrp.production.label.wizard', ondelete='cascade')
    sequence_no = fields.Integer(string="Rollo N°", readonly=True)
    weight = fields.Float(string="Peso Individual (KG)", digits=(16, 4), required=True)
