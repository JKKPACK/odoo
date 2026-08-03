
from odoo import models, fields, api
from datetime import datetime

class MrpPallet(models.Model):
    _name = 'mrp.pallet'
    _description = 'Tarima / Pallet - Master'
    _order = 'create_date desc'

    name = fields.Char(string='LOTE TARIMA', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('mrp.pallet') or 'TR/NEW', copy=False)
    production_id = fields.Many2one('mrp.production', string='Orden de Fabricación', required=True, ondelete='cascade')
    product_id = fields.Many2one(related='production_id.product_id', store=True, readonly=True)
    sale_order_id = fields.Many2one(related='production_id.sale_order_id', store=True)
    
    # Datos operador
    operator = fields.Char(string='Operador')
    machine = fields.Char(string='Máquina', default='Bolseadora Mamata 1')
    date_packing = fields.Datetime(string='Fecha Empaquetado', default=fields.Datetime.now)
    
    # Totales
    box_ids = fields.One2many('mrp.box', 'pallet_id', string='Cajas')
    box_count = fields.Integer(compute='_compute_totals', store=True)
    total_gross_weight = fields.Float(string='Peso Bruto Total (KG)', compute='_compute_totals', store=True)
    total_net_weight = fields.Float(string='Peso Neto Total (KG)', compute='_compute_totals', store=True)
    total_qty = fields.Float(string='Cant. Total / QtyPerPallet', compute='_compute_totals', store=True)
    total_tara = fields.Float(string='TARA Total', compute='_compute_totals', store=True)
    
    # Campos para etiqueta master (mapeo)
    customer_code = fields.Char(related='production_id.customer_code')
    customer_name = fields.Char(related='production_id.customer_name')
    customer_order_ref = fields.Char(related='production_id.customer_order_ref')
    
    # ZPL
    zpl_pallet = fields.Text(string='ZPL Master Tarima', compute='_compute_zpl')
    packing_list_pdf_done = fields.Boolean(default=False)

    @api.depends('box_ids.peso_bruto', 'box_ids.peso_neto', 'box_ids.qty_per_box')
    def _compute_totals(self):
        for rec in self:
            rec.box_count = len(rec.box_ids)
            rec.total_gross_weight = sum(rec.box_ids.mapped('peso_bruto'))
            rec.total_net_weight = sum(rec.box_ids.mapped('peso_neto'))
            rec.total_qty = sum(rec.box_ids.mapped('qty_per_box'))
            rec.total_tara = sum(rec.box_ids.mapped('tara'))

    def _compute_zpl(self):
        for rec in self:
            rec.zpl_pallet = rec.generate_pallet_zpl()

    def generate_pallet_zpl(self):
        # Basado en tu etiqueta de la imagen TR019053
        # Formato ZPL 4x6 aprox
        prod_code = self.product_id.default_code or self.product_id.name or ''
        prod_name = self.product_id.display_name or ''
        return f"""
^XA
^CF0,30
^FO20,20^FDJkk Pack^FS
^CF0,20
^FO20,50^FDPedido/ Order No. {self.sale_order_id.name or ''}   Cod. Producto: {prod_code}   CantX Tarima: {self.total_qty:.2f}^FS
^FO20,90^FDPedido Cliente: {self.customer_order_ref or ''}   Cajas por Tarima: {self.box_count}   Peso Bruto: {self.total_gross_weight:.2f} KG^FS
^FO20,130^FDFecha: {self.date_packing.strftime('%d/%m/%Y') if self.date_packing else ''}   Peso Neto: {self.total_net_weight:.2f} KG^FS
^FO20,170^FD{prod_name[:70]}^FS
^FO20,200^FD{self.customer_name or ''} - {self.customer_code or ''}^FS
^BY3,2,80^FO20,250^BCN,80,Y,N,A^FD{self.name}^FS
^FO20,350^FD{self.name}^FS
^FO20,380^FDImpreso por SAP / Odoo 19 - {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}^FS
^XZ
""".strip()

    def generate_boxes_zpl(self):
        return [b.generate_box_zpl() for b in self.box_ids]

    def action_print_packing_list(self):
        return self.env.ref('mrp_packing_final.action_report_packing_list').report_action(self)

    def action_print_browser_master(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/mrp_packing/print_pallet/{self.id}',
            'target': 'new',
        }

    def action_download_zpl_master(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/mrp_packing/download_zpl_pallet/{self.id}',
            'target': 'self',
        }

    def action_reprint_master_label(self):
        # Retorna wizard de previsualización ZPL
        return {
            'type': 'ir.actions.act_window',
            'name': f'Etiqueta Master {self.name}',
            'res_model': 'pallet.start.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_production_id': self.production_id.id, 'default_pallet_id': self.id, 'is_reprint': True}
        }
