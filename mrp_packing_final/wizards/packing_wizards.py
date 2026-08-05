from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PalletStartWizard(models.TransientModel):
    _name = "pallet.start.wizard"
    _description = "Iniciar Armado de Tarima"
    production_id = fields.Many2one(
        "mrp.production", string="Orden de Fabricación", required=True
    )
    operator_id = fields.Many2one(
        "hr.employee",
        string="Operador",
        required=True,
    )
    machine = fields.Char(string="Máquina", default="Bolseadora Mamata 1")
    num_boxes = fields.Integer(
        string="Número de cajas/bobinas que van en la tarima", required=True, default=24
    )
    pallet_id = fields.Many2one("mrp.pallet", string="Tarima existente (reimpresión)")
    is_reprint = fields.Boolean(default=False)

    def action_next(self):
        if self.is_reprint and self.pallet_id:
            return self.pallet_id.action_print_packing_list()
        pallet = self.env["mrp.pallet"].create(
            {
                "production_id": self.production_id.id,
                "operator_id": self.operator_id.id,
                "machine": self.machine,
            }
        )
        wizard = self.env["box.entry.wizard"].create(
            {"pallet_id": pallet.id, "production_id": self.production_id.id}
        )
        for i in range(1, self.num_boxes + 1):
            self.env["box.entry.line"].create(
                {
                    "wizard_id": wizard.id,
                    "sequence": i,
                    "qty_per_box": 2.0,
                    "tara": 0.98,
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": f"Captura de Cajas - Tarima {pallet.name}",
            "res_model": "box.entry.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }


class BoxEntryWizard(models.TransientModel):
    _name = "box.entry.wizard"
    _description = "Captura Manual de Pesos por Caja"
    pallet_id = fields.Many2one("mrp.pallet", required=True)
    production_id = fields.Many2one("mrp.production")
    line_ids = fields.One2many("box.entry.line", "wizard_id", string="Cajas")
    total_gross = fields.Float(compute="_compute_totals")
    total_net = fields.Float(compute="_compute_totals")
    total_qty = fields.Float(compute="_compute_totals")
    tara = fields.Float(string="TARA")

    @api.onchange("tara")
    def _onchange_tara(self):
        for wizard in self:
            wizard.line_ids.update({"tara": wizard.tara})

    @api.depends("line_ids.peso_bruto", "line_ids.peso_neto", "line_ids.qty_per_box")
    def _compute_totals(self):
        for w in self:
            w.total_gross = sum(w.line_ids.mapped("peso_bruto"))
            w.total_net = sum(w.line_ids.mapped("peso_neto"))
            w.total_qty = sum(w.line_ids.mapped("qty_per_box"))

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError("Debe capturar al menos una caja")
        for line in self.line_ids:
            if not line.peso_bruto or not line.peso_neto:
                raise ValidationError(f"Falta peso en caja {line.sequence}")
            self.env["mrp.box"].create(
                {
                    "pallet_id": self.pallet_id.id,
                    "sequence": line.sequence,
                    "master_lot": line.master_lot,
                    "peso_bruto": line.peso_bruto,
                    "peso_neto": line.peso_neto,
                    "tara": line.tara,
                    "qty_per_box": line.qty_per_box,
                    "mill_roll": line.qty_per_box,
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": f"Tarima {self.pallet_id.name} - Lista",
            "res_model": "mrp.pallet",
            "res_id": self.pallet_id.id,
            "view_mode": "form",
            "target": "current",
        }


class BoxEntryLine(models.TransientModel):
    _name = "box.entry.line"
    _description = "Linea Captura Caja"
    wizard_id = fields.Many2one("box.entry.wizard", ondelete="cascade")
    sequence = fields.Integer(string="#")
    master_lot = fields.Char(string="Lote Maestro / Master Lot")
    peso_bruto = fields.Float(string="Peso Bruto")
    peso_neto = fields.Float(
        string="Peso Neto",
        compute="_compute_peso_neto",
        store=True,
        readonly=False,
    )
    tara = fields.Float(string="TARA", default=0.98)
    qty_per_box = fields.Float(string="Cant x Caja", default=2.0)

    @api.depends("peso_bruto", "tara")
    def _compute_peso_neto(self):
        for line in self:
            line.peso_neto = (line.peso_bruto or 0.0) - (line.tara or 0.0)
