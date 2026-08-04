
from odoo import http
from odoo.http import request
class PackingPrintController(http.Controller):
    @http.route('/mrp_packing/print_pallet/<int:pallet_id>', type='http', auth='user')
    def print_pallet(self, pallet_id, **kw):
        pallet = request.env['mrp.pallet'].browse(pallet_id)
        html = f'''
        <html><head><title>Etiqueta Master {pallet.name}</title>
        <style>body{{font-family:Arial;margin:0;padding:20px;}}.label{{width:4in;height:6in;border:2px solid black;padding:10px;font-size:12px;}}.row{{display:flex;justify-content:space-between;}}.barcode{{text-align:center;margin-top:20px;}}@media print{{.no-print{{display:none;}}}}</style></head><body>
        <div class="no-print" style="margin-bottom:15px;"><button onclick="window.print()" style="padding:10px 20px;background:#714B67;color:white;border:none;">Imprimir</button><button onclick="downloadZPL()" style="padding:10px 20px;margin-left:10px;">Descargar ZPL</button></div>
        <div class="label"><div class="row"><b>Pedido {pallet.sale_order_id.name if pallet.sale_order_id else ''}</b><span>Cod {pallet.product_id.default_code or ''}</span><span>Cant {pallet.total_qty:.2f}</span></div><div class="row" style="margin-top:10px;"><span>Cliente {pallet.customer_order_ref or ''}</span><span>Cajas {pallet.box_count}</span><span>Bruto {pallet.total_gross_weight:.2f} KG</span></div><div class="row"><span>Fecha {pallet.date_packing.strftime('%d/%m/%Y') if pallet.date_packing else ''}</span><span>Neto {pallet.total_net_weight:.2f} KG</span></div><div style="margin-top:10px;">{pallet.product_id.display_name}</div><div>{pallet.customer_name or ''}</div><div class="barcode"><svg id="barcode"></svg><br/><b>{pallet.name}</b></div></div>
        <pre id="zpl" style="display:none;">{pallet.zpl_pallet}</pre>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script><script>JsBarcode("#barcode","{pallet.name}",{{format:"CODE128",width:2,height:80}});function downloadZPL(){{var zpl=document.getElementById('zpl').innerText;var blob=new Blob([zpl],{{type:'text/plain'}});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download='{pallet.name}_MASTER.zpl';a.click();}}</script></body></html>'''
        return html
    @http.route('/mrp_packing/download_zpl_pallet/<int:pallet_id>', type='http', auth='user')
    def download_zpl_pallet(self, pallet_id, **kw):
        pallet = request.env['mrp.pallet'].browse(pallet_id)
        return request.make_response(pallet.zpl_pallet or '', [('Content-Type','text/plain'),('Content-Disposition',f'attachment; filename="{pallet.name}_MASTER.zpl"')])
