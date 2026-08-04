
from odoo import models, fields, api
class MrpBox(models.Model):
    _name = 'mrp.box'
    _description = 'Caja por Tarima'
    _order = 'id'
    pallet_id = fields.Many2one('mrp.pallet', string='Tarima', required=True, ondelete='cascade')
    production_id = fields.Many2one(related='pallet_id.production_id', store=True)
    name = fields.Char(string='Lote Caja / Box Lot', compute='_compute_name', store=True)
    sequence = fields.Integer(string='No. Caja por tarima')
    master_lot = fields.Char(string='Lote Maestro / Master Lot / Rollo Maestro')
    peso_bruto = fields.Float(string='Peso Bruto / Gross Weight')
    peso_neto = fields.Float(string='Peso Neto / Net Weight')
    tara = fields.Float(string='TARA', default=0.98)
    qty_per_box = fields.Float(string='Cantidad x Caja', default=2.0)
    mill_roll = fields.Float(string='Mill / Rollo', default=2.0)
    operador = fields.Char(related='pallet_id.operator', store=True)
    customer_item_no = fields.Char(related='pallet_id.production_id.customer_item_no', store=True)
    zpl_box = fields.Text(compute='_compute_zpl')
    @api.depends('pallet_id.name','sequence')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.pallet_id.name or 'NEW'}-{rec.sequence or 0}" if rec.pallet_id.name else f"NEW-{rec.sequence or 0}"
    def _compute_zpl(self):
        for rec in self:
            rec.zpl_box = rec.generate_box_zpl()
    def generate_box_zpl(self):
        prod = self.pallet_id.product_id
        prod_code = prod.default_code or ''
        return f"""^XA
^CF0,20
^FO10,10^FDO. Fab {self.pallet_id.production_id.name} Prod {prod_code} Rollo {self.master_lot or ''} Op {self.operador or ''}^FS
^FO10,40^FDCliente {self.pallet_id.customer_code or ''} Fecha {self.pallet_id.date_packing.strftime('%d/%m/%Y') if self.pallet_id.date_packing else ''} Mill {self.mill_roll} Maq {self.pallet_id.machine}^FS
^FO10,70^FDPedido {self.pallet_id.sale_order_id.name if self.pallet_id.sale_order_id else ''} Destiny {self.customer_item_no or ''} Neto {self.peso_neto} Box #{self.sequence} TARA {self.tara}^FS
^FO10,100^FDLOTE/PALLET {self.pallet_id.name}^FS
^BY3,2,70^FO10,150^BCN,70,Y,N,A^FD{self.name}^FS
^FO10,230^FD{self.name}^FS
^XZ""".strip()
