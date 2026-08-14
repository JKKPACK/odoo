from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PalletStartWizard(models.TransientModel):
    _name = "pallet.start.wizard"
    _description = "Iniciar Armado de Tarima"

    production_id = fields.Many2one("mrp.production", string="Orden de Fabricación", required=True)
    operator_id = fields.Many2one("hr.employee", string="Operador", required=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Centro de Trabajo")
    machine = fields.Char(string="Máquina")
    num_boxes = fields.Integer(
        string="Número de cajas/bobinas que van en la tarima", required=True, default=24
    )
    pallet_id = fields.Many2one("mrp.pallet", string="Tarima existente (reimpresión)")
    is_reprint = fields.Boolean(default=False)

    @api.onchange("workcenter_id")
    def _onchange_workcenter_id(self):
        if self.workcenter_id:
            self.machine = self.workcenter_id.name

    @api.constrains("num_boxes")
    def _check_num_boxes(self):
        for rec in self:
            if rec.num_boxes <= 0:
                raise ValidationError(_("El número de cajas/bobinas debe ser mayor a cero."))

    def action_next(self):
        self.ensure_one()
        if self.is_reprint and self.pallet_id:
            return self.pallet_id.action_print_browser_master()

        available_lots = self.production_id._available_packing_lots()
        if not available_lots:
            raise ValidationError(_("No existen lotes disponibles para empacar en esta orden de fabricación."))
        if self.num_boxes > len(available_lots):
            raise ValidationError(_(
                "Solicitó %s cajas/bobinas, pero solo existen %s lotes disponibles."
            ) % (self.num_boxes, len(available_lots)))

        pallet = self.env["mrp.pallet"].create({
            "production_id": self.production_id.id,
            "operator_id": self.operator_id.id,
            "workcenter_id": self.workcenter_id.id,
            "machine": self.machine or self.workcenter_id.name,
        })
        wizard = self.env["box.entry.wizard"].create({
            "pallet_id": pallet.id,
            "production_id": self.production_id.id,
        })
        self.env["box.entry.line"].create([
            {
                "wizard_id": wizard.id,
                "sequence": i,
                "qty_per_box": 2.0,
                "tara": 0.98,
            }
            for i in range(1, self.num_boxes + 1)
        ])
        return {
            "type": "ir.actions.act_window",
            "name": f"Captura de Cajas/Bobinas - Tarima {pallet.name}",
            "res_model": "box.entry.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }


class BoxEntryWizard(models.TransientModel):
    _name = "box.entry.wizard"
    _description = "Captura Manual de Pesos por Caja/Bobina"

    pallet_id = fields.Many2one("mrp.pallet", required=True)
    production_id = fields.Many2one("mrp.production", required=True)
    production_lot_ids = fields.Many2many("stock.lot", compute="_compute_lots", string="Lotes de producción")
    lot_ids_empacados = fields.Many2many("stock.lot", compute="_compute_lots", string="Lotes ya empacados")
    lot_ids_disponibles = fields.Many2many("stock.lot", compute="_compute_lots", string="Lotes disponibles")
    line_ids = fields.One2many("box.entry.line", "wizard_id", string="Cajas/Bobinas")
    total_gross = fields.Float(compute="_compute_totals")
    total_net = fields.Float(compute="_compute_totals")
    total_qty = fields.Float(compute="_compute_totals")
    tara = fields.Float(string="TARA", default=0.98)

    @api.depends("production_id")
    def _compute_lots(self):
        Box = self.env["mrp.box"]
        for wizard in self:
            lots = wizard.production_id._packing_lots() if wizard.production_id else self.env["stock.lot"]
            boxes = Box.search([("production_id", "=", wizard.production_id.id)]) if wizard.production_id else Box
            used = boxes.filtered("lot_id").mapped("lot_id") if wizard.production_id else self.env["stock.lot"]
            if wizard.production_id:
                legacy_names = set(
                    name.strip()
                    for box in boxes.filtered(lambda b: not b.lot_id and b.master_lot)
                    for name in box.master_lot.split(",")
                    if name.strip()
                )
                if legacy_names:
                    used |= lots.filtered(lambda lot: lot.name in legacy_names)
            wizard.production_lot_ids = lots
            wizard.lot_ids_empacados = used & lots
            wizard.lot_ids_disponibles = lots - used

    @api.onchange("tara")
    def _onchange_tara(self):
        self.line_ids.update({"tara": self.tara})

    @api.depends("line_ids.peso_bruto", "line_ids.peso_neto", "line_ids.qty_per_box")
    def _compute_totals(self):
        for wizard in self:
            wizard.total_gross = sum(wizard.line_ids.mapped("peso_bruto"))
            wizard.total_net = sum(wizard.line_ids.mapped("peso_neto"))
            wizard.total_qty = sum(wizard.line_ids.mapped("qty_per_box"))

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Debe capturar al menos una caja/bobina."))

        selected_lots = self.line_ids.mapped("lot_id")
        if len(selected_lots) != len(self.line_ids):
            raise ValidationError(_("Debe seleccionar exactamente un lote por cada caja/bobina."))
        if len(set(selected_lots.ids)) != len(selected_lots):
            raise ValidationError(_("Un lote no puede seleccionarse más de una vez en la misma tarima."))

        already_used = self.env["mrp.box"].search([
            ("production_id", "=", self.production_id.id),
            ("lot_id", "in", selected_lots.ids),
            ("pallet_id", "!=", self.pallet_id.id),
        ])
        legacy_boxes = self.env["mrp.box"].search([
            ("production_id", "=", self.production_id.id),
            ("lot_id", "=", False),
            ("master_lot", "!=", False),
            ("pallet_id", "!=", self.pallet_id.id),
        ])
        legacy_used_names = set(
            name.strip()
            for box in legacy_boxes
            for name in box.master_lot.split(",")
            if name.strip()
        )
        conflicts = selected_lots.filtered(lambda lot: lot.name in legacy_used_names)
        if already_used or conflicts:
            names = set(already_used.mapped("lot_id.name")) | set(conflicts.mapped("name"))
            raise ValidationError(_(
                "Estos lotes ya fueron empacados en otra tarima: %s"
            ) % ", ".join(sorted(names)))

        values = []
        for line in self.line_ids.sorted("sequence"):
            if line.peso_bruto <= 0:
                raise ValidationError(_("Falta peso bruto en caja/bobina %s.") % line.sequence)
            if line.tara < 0 or line.peso_neto <= 0:
                raise ValidationError(_("Revise la tara/peso neto de la caja/bobina %s.") % line.sequence)
            if line.qty_per_box <= 0:
                raise ValidationError(_("La cantidad de la caja/bobina %s debe ser mayor a cero.") % line.sequence)
            values.append({
                "pallet_id": self.pallet_id.id,
                "sequence": line.sequence,
                "lot_id": line.lot_id.id,
                "master_lot": line.lot_id.name,
                "peso_bruto": line.peso_bruto,
                "peso_neto": line.peso_neto,
                "tara": line.tara,
                "qty_per_box": line.qty_per_box,
                "mill_roll": line.qty_per_box,
            })
        self.env["mrp.box"].create(values)
        return {
            "type": "ir.actions.act_window",
            "name": f"Tarima {self.pallet_id.name}",
            "res_model": "mrp.pallet",
            "res_id": self.pallet_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_cancel(self):
        self.ensure_one()
        pallet = self.pallet_id
        if pallet and not pallet.box_ids:
            pallet.unlink()
        return {"type": "ir.actions.act_window_close"}


class BoxEntryLine(models.TransientModel):
    _name = "box.entry.line"
    _description = "Línea Captura Caja/Bobina"
    _order = "sequence, id"

    wizard_id = fields.Many2one("box.entry.wizard", ondelete="cascade", required=True)
    sequence = fields.Integer(string="#", required=True)
    production_id = fields.Many2one(related="wizard_id.production_id", readonly=True)
    lot_ids_disponibles = fields.Many2many(related="wizard_id.lot_ids_disponibles", readonly=True)
    lot_ids_usados = fields.Many2many("stock.lot", compute="_compute_lot_ids_usados", string="Lotes usados")
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote Maestro / Master Lot",
        domain="[('id', 'in', lot_ids_disponibles), ('id', 'not in', lot_ids_usados)]",
    )
    peso_bruto = fields.Float(string="Peso Bruto")
    peso_neto = fields.Float(string="Peso Neto", compute="_compute_peso_neto", store=True, readonly=True)
    tara = fields.Float(string="TARA", default=0.98)
    qty_per_box = fields.Float(string="Cant x Caja", default=2.0)

    @api.depends("wizard_id.line_ids.lot_id")
    def _compute_lot_ids_usados(self):
        for line in self:
            line.lot_ids_usados = (line.wizard_id.line_ids - line).mapped("lot_id")

    @api.constrains("lot_id", "wizard_id.line_ids.lot_id")
    def _check_lotes_unicos(self):
        for line in self.filtered("lot_id"):
            if line.lot_id in (line.wizard_id.line_ids - line).mapped("lot_id"):
                raise ValidationError(_("El lote %s ya fue seleccionado en otra línea.") % line.lot_id.display_name)

    @api.depends("peso_bruto", "tara")
    def _compute_peso_neto(self):
        for line in self:
            line.peso_neto = (line.peso_bruto or 0.0) - (line.tara or 0.0)
