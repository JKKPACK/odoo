from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PalletStartWizard(models.TransientModel):
    _name = "pallet.start.wizard"
    _description = "Iniciar Armado de Tarima"

    production_id = fields.Many2one("mrp.production", string="Orden de Fabricación", required=True)
    operator_id = fields.Many2one(
        "hr.employee",
        string="Operador",
        required=True,
        default=lambda self: self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id)], limit=1
        ),
    )
    workcenter_id = fields.Many2one("mrp.workcenter", string="Centro de Trabajo")
    machine = fields.Char(string="Máquina")
    num_boxes = fields.Integer(
        string="Número de cajas/bobinas que van en la tarima", required=True, default=24
    )
    pallet_id = fields.Many2one("mrp.pallet", string="Tarima existente (reimpresión)")
    is_reprint = fields.Boolean(default=False)
    can_pack_partial_productions = fields.Boolean(
        string="Puede agrupar producciones parciales",
        compute="_compute_partial_production_options",
    )
    include_partial_productions = fields.Boolean(
        string="Incluir todas las producciones parciales",
        help=(
            "Solo disponible en la producción principal. Al activarlo, la captura "
            "incluye los lotes disponibles de la producción principal y de todas "
            "sus producciones parciales/backorders."
        ),
    )
    partial_production_ids = fields.Many2many(
        "mrp.production",
        string="Producciones relacionadas",
        compute="_compute_partial_production_options",
    )
    production_selection_line_ids = fields.One2many(
        "pallet.start.production.line",
        "wizard_id",
        string="Producciones a incluir",
    )

    @api.depends("production_id", "production_id.production_group_id.production_ids", "production_id.backorder_sequence")
    def _compute_partial_production_options(self):
        for wizard in self:
            if wizard.production_id and wizard.production_id._is_main_packing_production():
                family = wizard.production_id._packing_family_productions()
                wizard.can_pack_partial_productions = len(family) > 1
                wizard.partial_production_ids = family
            else:
                wizard.can_pack_partial_productions = False
                wizard.partial_production_ids = self.env["mrp.production"]

    @api.model
    def default_get(self, fields_list):
        """Carga automáticamente todo lo inferible desde la OF/tarima/contexto."""
        values = super().default_get(fields_list)
        context = self.env.context

        production = self.env["mrp.production"]
        pallet = self.env["mrp.pallet"]

        pallet_id = values.get("pallet_id") or context.get("default_pallet_id")
        if pallet_id:
            pallet = self.env["mrp.pallet"].browse(pallet_id).exists()
            if pallet:
                production = pallet.production_id
                values.setdefault("operator_id", pallet.operator_id.id)
                values.setdefault("workcenter_id", pallet.workcenter_id.id)
                values.setdefault("machine", pallet.machine)

        production_id = (
            values.get("production_id")
            or context.get("default_production_id")
            or (context.get("active_id") if context.get("active_model") == "mrp.production" else False)
        )
        if production_id and not production:
            production = self.env["mrp.production"].browse(production_id).exists()
        if production:
            values["production_id"] = production.id
            workcenter = production._packing_workcenter()
            if workcenter:
                values.setdefault("workcenter_id", workcenter.id)
                values.setdefault("machine", workcenter.name)
            if not context.get("default_num_boxes"):
                values["num_boxes"] = len(production._available_packing_lots()) or 1

        if not values.get("operator_id"):
            employee = self.env["hr.employee"].search(
                [("user_id", "=", self.env.user.id)], limit=1
            )
            if employee:
                values["operator_id"] = employee.id

        return values

    @api.onchange("production_id")
    def _onchange_production_id(self):
        if not self.production_id:
            return
        workcenter = self.production_id._packing_workcenter()
        self.workcenter_id = workcenter
        self.machine = workcenter.name if workcenter else False
        self.include_partial_productions = False
        available_lots = self.production_id._available_packing_lots()
        self.num_boxes = len(available_lots) or 1

    @api.onchange("include_partial_productions")
    def _onchange_include_partial_productions(self):
        if not self.production_id:
            return
        if self.include_partial_productions:
            if not self.production_id._is_main_packing_production():
                self.include_partial_productions = False
                return
            self.num_boxes = len(self.production_id._packing_family_available_lots()) or 1
        else:
            self.num_boxes = len(self.production_id._available_packing_lots()) or 1

    def action_load_partial_productions(self):
        """Load the MO family explicitly so the operator can choose partials."""
        self.ensure_one()
        if not self.production_id or not self.production_id._is_main_packing_production():
            raise ValidationError(_(
                "Las producciones parciales solo pueden cargarse desde la producción principal."
            ))
        family = self.production_id._packing_family_productions()
        if len(family) <= 1:
            raise ValidationError(_("Esta producción no tiene producciones parciales relacionadas."))

        existing = {line.production_id.id: line.selected for line in self.production_selection_line_ids}
        commands = [(5, 0, 0)]
        total_lots = 0
        for production in family:
            is_main = production == self.production_id
            selected = True if is_main else existing.get(production.id, True)
            available_count = len(production._available_packing_lots())
            commands.append((0, 0, {
                "production_id": production.id,
                "selected": selected,
                "is_main": is_main,
                "available_lot_count": available_count,
                "qty_producing": production.qty_producing or production.product_qty,
            }))
            if selected:
                total_lots += available_count
        self.production_selection_line_ids = commands
        self.include_partial_productions = True
        self.num_boxes = total_lots or 1
        return {
            "type": "ir.actions.act_window",
            "name": _("Iniciar Empaquetado"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.onchange("production_selection_line_ids.selected")
    def _onchange_production_selection(self):
        if not self.production_selection_line_ids:
            return
        # The main production is mandatory in grouped mode.
        for line in self.production_selection_line_ids.filtered("is_main"):
            line.selected = True
        selected = self.production_selection_line_ids.filtered("selected").mapped("production_id")
        self.include_partial_productions = len(selected) > 1
        self.num_boxes = sum(len(mo._available_packing_lots()) for mo in selected) or 1

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

        selected_lines = self.production_selection_line_ids.filtered("selected")
        if selected_lines:
            main_lines = self.production_selection_line_ids.filtered("is_main")
            if main_lines and not all(main_lines.mapped("selected")):
                raise ValidationError(_("La producción principal siempre debe incluirse."))
            packing_productions = selected_lines.mapped("production_id")
            grouped = len(packing_productions) > 1
        else:
            packing_productions = self.production_id
            grouped = False

        if grouped and not self.production_id._is_main_packing_production():
            raise ValidationError(_(
                "La opción de agrupar producciones parciales solo puede utilizarse desde la producción principal."
            ))

        available_pairs = []
        for production in packing_productions:
            available_pairs.extend((production, lot) for lot in production._available_packing_lots())

        if not available_pairs:
            raise ValidationError(_(
                "No existen lotes disponibles para empacar%s."
            ) % (_(" en la producción principal ni en sus parcialidades") if grouped else _(" en esta orden de fabricación")))
        if self.num_boxes > len(available_pairs):
            raise ValidationError(_(
                "Solicitó %s cajas/bobinas, pero solo existen %s lotes disponibles%s."
            ) % (
                self.num_boxes,
                len(available_pairs),
                _(" entre la producción principal y sus parcialidades") if grouped else "",
            ))

        pallet = self.env["mrp.pallet"].create({
            "production_id": self.production_id.id,
            "product_id": self.production_id.product_id.id,
            "is_grouped_production_packing": grouped,
            "packing_production_ids": [(6, 0, packing_productions.ids)],
            "operator_id": self.operator_id.id,
            "workcenter_id": self.workcenter_id.id,
            "machine": self.machine or (self.workcenter_id.name if self.workcenter_id else False),
        })
        wizard = self.env["box.entry.wizard"].create({
            "pallet_id": pallet.id,
            "production_id": self.production_id.id,
            "is_grouped_production_packing": grouped,
            "packing_production_ids": [(6, 0, packing_productions.ids)],
        })
        pairs_to_pack = available_pairs[: self.num_boxes]
        self.env["box.entry.line"].create([
            {
                "wizard_id": wizard.id,
                "sequence": i,
                "source_production_id": pairs_to_pack[i - 1][0].id,
                "lot_id": pairs_to_pack[i - 1][1].id,
                "qty_per_box": 2.0,
                "tara": 0.98,
                "peso_bruto": 0.0,
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


class PalletStartProductionLine(models.TransientModel):
    _name = "pallet.start.production.line"
    _description = "Selección de Producciones para Empaquetado"
    _order = "is_main desc, production_id"

    wizard_id = fields.Many2one("pallet.start.wizard", required=True, ondelete="cascade")
    selected = fields.Boolean(string="Incluir", default=True)
    production_id = fields.Many2one("mrp.production", string="Producción", required=True, readonly=True)
    is_main = fields.Boolean(string="Principal", readonly=True)
    product_id = fields.Many2one(related="production_id.product_id", string="Producto", readonly=True)
    qty_producing = fields.Float(string="Cantidad", readonly=True)
    available_lot_count = fields.Integer(string="Lotes disponibles", readonly=True)



class BoxEntryWizard(models.TransientModel):
    _name = "box.entry.wizard"
    _description = "Captura Manual de Pesos por Caja/Bobina"

    pallet_id = fields.Many2one("mrp.pallet", required=True)
    production_id = fields.Many2one("mrp.production", string="Orden de Fabricación")
    is_grouped_production_packing = fields.Boolean(string="Empaque agrupado de parcialidades", readonly=True)
    packing_production_ids = fields.Many2many(
        "mrp.production",
        "box_entry_wizard_production_rel",
        "wizard_id",
        "production_id",
        string="Producciones incluidas",
        readonly=True,
    )
    product_id = fields.Many2one(related="pallet_id.product_id", string="Producto", readonly=True)
    production_lot_ids = fields.Many2many("stock.lot", compute="_compute_lots", string="Lotes de producción")
    lot_ids_empacados = fields.Many2many("stock.lot", compute="_compute_lots", string="Lotes ya empacados")
    lot_ids_disponibles = fields.Many2many("stock.lot", compute="_compute_lots", string="Lotes disponibles")
    line_ids = fields.One2many("box.entry.line", "wizard_id", string="Cajas/Bobinas")
    total_gross = fields.Float(compute="_compute_totals")
    total_net = fields.Float(compute="_compute_totals")
    total_qty = fields.Float(compute="_compute_totals")
    tara = fields.Float(string="TARA", default=0.98)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        pallet_id = values.get("pallet_id") or self.env.context.get("default_pallet_id")
        if pallet_id:
            pallet = self.env["mrp.pallet"].browse(pallet_id).exists()
            if pallet:
                values["pallet_id"] = pallet.id
                values["production_id"] = pallet.production_id.id or False
        return values

    @api.depends("production_id", "pallet_id", "pallet_id.product_id", "pallet_id.box_ids.lot_id")
    def _compute_lots(self):
        Box = self.env["mrp.box"]
        Lot = self.env["stock.lot"]
        for wizard in self:
            if wizard.production_id and wizard.is_grouped_production_packing:
                productions = wizard.packing_production_ids or wizard.production_id._packing_family_productions()
                lots = Lot.browse()
                for production in productions:
                    lots |= production._packing_lots()
                boxes = Box.search([
                    ("pallet_id", "!=", wizard.pallet_id.id),
                    "|",
                    ("source_production_id", "in", productions.ids),
                    "&", ("source_production_id", "=", False), ("production_id", "in", productions.ids),
                ])
            elif wizard.production_id:
                lots = wizard.production_id._packing_lots()
                boxes = Box.search([
                    ("pallet_id", "!=", wizard.pallet_id.id),
                    "|",
                    ("source_production_id", "=", wizard.production_id.id),
                    "&", ("source_production_id", "=", False), ("production_id", "=", wizard.production_id.id),
                ])
            elif wizard.pallet_id and wizard.product_id:
                lots = Lot.search([("product_id", "=", wizard.product_id.id)])
                boxes = Box.search([
                    ("product_id", "=", wizard.product_id.id),
                    ("pallet_id", "!=", wizard.pallet_id.id),
                ])
            else:
                lots = Lot
                boxes = Box.browse()

            used = boxes.filtered("lot_id").mapped("lot_id")
            legacy_names = set(
                name.strip()
                for box in boxes.filtered(lambda b: not b.lot_id and b.master_lot)
                for name in box.master_lot.split(",")
                if name.strip()
            )
            if legacy_names:
                used |= lots.filtered(lambda lot: lot.name in legacy_names)

            current_lots = wizard.pallet_id.box_ids.mapped("lot_id") if wizard.pallet_id else Lot
            wizard.production_lot_ids = lots
            wizard.lot_ids_empacados = used & lots
            wizard.lot_ids_disponibles = (lots - used) | current_lots

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

        scope_domain = [("pallet_id", "!=", self.pallet_id.id)]
        if self.production_id and self.is_grouped_production_packing:
            production_ids = self.packing_production_ids.ids
            scope_domain += [
                "|",
                ("source_production_id", "in", production_ids),
                "&", ("source_production_id", "=", False), ("production_id", "in", production_ids),
            ]
        elif self.production_id:
            scope_domain += [
                "|",
                ("source_production_id", "=", self.production_id.id),
                "&", ("source_production_id", "=", False), ("production_id", "=", self.production_id.id),
            ]
        else:
            scope_domain.append(("product_id", "=", self.product_id.id))

        already_used = self.env["mrp.box"].search(
            scope_domain + [("lot_id", "in", selected_lots.ids)]
        )
        legacy_boxes = self.env["mrp.box"].search(
            scope_domain + [("lot_id", "=", False), ("master_lot", "!=", False)]
        )
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
            source_production = line.source_production_id
            if self.production_id and self.is_grouped_production_packing:
                matching = self.packing_production_ids.filtered(
                    lambda mo: line.lot_id in mo._packing_lots()
                )
                if not matching:
                    raise ValidationError(_(
                        "El lote %(lot)s no pertenece a ninguna de las producciones incluidas en esta tarima."
                    ) % {"lot": line.lot_id.display_name})
                source_production = matching[:1]
            elif self.production_id:
                source_production = self.production_id

            values.append({
                "pallet_id": self.pallet_id.id,
                "sequence": line.sequence,
                "source_production_id": source_production.id or False,
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
    source_production_id = fields.Many2one(
        "mrp.production",
        string="Producción origen",
        readonly=True,
        help="Producción principal o parcial que generó el lote de esta caja/bobina.",
    )
    lot_ids_disponibles = fields.Many2many(related="wizard_id.lot_ids_disponibles", readonly=True)
    lot_ids_usados = fields.Many2many("stock.lot", compute="_compute_lot_ids_usados", string="Lotes usados")
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lote Maestro / Master Lot",
        required=True,
        domain="[('id', 'in', lot_ids_disponibles), ('id', 'not in', lot_ids_usados)]",
    )
    peso_bruto = fields.Float(string="Peso Bruto", default=0.0)
    peso_neto = fields.Float(string="Peso Neto", compute="_compute_peso_neto", store=True, readonly=True)
    tara = fields.Float(string="TARA", default=0.98, required=True)
    qty_per_box = fields.Float(string="Cant x Caja", default=2.0, required=True)

    @api.depends("wizard_id.line_ids.lot_id")
    def _compute_lot_ids_usados(self):
        for line in self:
            line.lot_ids_usados = (line.wizard_id.line_ids - line).mapped("lot_id")

    @api.onchange("lot_id")
    def _onchange_lot_id_source_production(self):
        for line in self:
            if not line.lot_id or not line.wizard_id.production_id:
                continue
            if line.wizard_id.is_grouped_production_packing:
                productions = line.wizard_id.packing_production_ids
                source = productions.filtered(lambda mo: line.lot_id in mo._packing_lots())[:1]
                line.source_production_id = source or line.wizard_id.production_id
            else:
                line.source_production_id = line.wizard_id.production_id

    @api.constrains("lot_id", "wizard_id.line_ids.lot_id")
    def _check_lotes_unicos(self):
        for line in self.filtered("lot_id"):
            if line.lot_id in (line.wizard_id.line_ids - line).mapped("lot_id"):
                raise ValidationError(_("El lote %s ya fue seleccionado en otra línea.") % line.lot_id.display_name)

    @api.depends("peso_bruto", "tara")
    def _compute_peso_neto(self):
        for line in self:
            line.peso_neto = (line.peso_bruto or 0.0) - (line.tara or 0.0)
