
from odoo import models, fields, api

class MrpBox(models.Model):
    _name = 'mrp.box'
    _description = 'Caja por Tarima'
    _order = 'id'

    pallet_id = fields.Many2one('mrp.pallet', string='Tarima', required=True, ondelete='cascade')
    production_id = fields.Many2one(related='pallet_id.production_id', store=True)
    
    name = fields.Char(string='Lote Caja / Box Lot', compute='_compute_name', store=True)
    sequence = fields.Integer(string='No. Caja por tarima')
    
    master_lot = fields.Char(string='Lote Maestro / Master Lot / Rollo Maestro', help='Ej. BMC00288264')
    peso_bruto = fields.Float(string='Peso Bruto / Gross Weight')
    peso_neto = fields.Float(string='Peso Neto / Net Weight')
    tara = fields.Float(string='TARA', default=0.98, help='Manual como en SAP - captura operador')
    qty_per_box = fields.Float(string='Cantidad x Caja / Quantity per box / Mill/Roll', default=2.0)
    mill_roll = fields.Float(string='Mill / Rollo', default=2.0)

    operador = fields.Char(related='pallet_id.operator', store=True)
    customer_item_no = fields.Char(related='pallet_id.production_id.customer_item_no', store=True)
    
    zpl_box = fields.Text(compute='_compute_zpl')

    @api.depends('pallet_id.name', 'sequence')
    def _compute_name(self):
        for rec in self:
            if rec.pallet_id.name and rec.sequence:
                rec.name = f"{rec.pallet_id.name}-{rec.sequence}"
            else:
                rec.name = f"{rec.pallet_id.name or 'NEW'}-{rec.sequence or 0}"

    def _compute_zpl(self):
        for rec in self:
            rec.zpl_box = rec.generate_box_zpl()

    def generate_box_zpl(self):
        prod = self.pallet_id.product_id
        prod_code = prod.default_code or ''
        cust_code = self.pallet_id.customer_code or ''
        cust_name = self.pallet_id.customer_name or ''
        sale_ref = self.pallet_id.customer_order_ref or ''
        sale_name = self.pallet_id.sale_order_id.name if self.pallet_id.sale_order_id else ''
        return f"""
^XA
^CF0,20
^FO10,10^FDO. Fab/ Mfg No {self.pallet_id.production_id.name}   Cod.Producto {prod_code}   Rollo Maestro {self.master_lot or ''}   Operador {self.operador or ''}^FS
^FO10,40^FDCliente {cust_code}   Fecha {self.pallet_id.date_packing.strftime('%d/%m/%Y') if self.pallet_id.date_packing else ''}   Mill/Roll {self.mill_roll}   Maquina {self.pallet_id.machine}^FS
^FO10,70^FDPedido JkkPack: {sale_name}   Destiny # {self.customer_item_no or ''}   Peso Neto {self.peso_neto} Kg   CASE BOX ID # {self.sequence}^FS
^FO10,100^FDLOTE/PALLET {self.pallet_id.name}  {prod.display_name[:60]}^FS
^FO10,130^FD{cust_name}^FS
^BY2,2,60^FO10,170^BCN,60,Y,N,A^FD{self.customer_item_no or ''}^FS
^FO10,240^FD{self.customer_item_no or ''}^FS
^BY2,2,60^FO250,170^BCN,60,Y,N,A^FD{self.qty_per_box}^FS
^FO250,240^FDQty {self.qty_per_box}^FS
^BY3,2,70^FO10,300^BCN,70,Y,N,A^FD{self.name}^FS
^FO10,380^FD{self.name}^FS
^XZ
""".strip()

    def action_print_browser(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/mrp_packing/print_box/{self.id}',
            'target': 'new',
        }
