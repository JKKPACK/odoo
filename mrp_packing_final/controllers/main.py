
from odoo import http
from odoo.http import request

class PackingPrintController(http.Controller):

    @http.route('/mrp_packing/print_pallet/<int:pallet_id>', type='http', auth='user')
    def print_pallet(self, pallet_id, **kw):
        pallet = request.env['mrp.pallet'].browse(pallet_id)
        html = f'''
        <html><head><title>Etiqueta Master {pallet.name}</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin:0; padding:20px; }}
          .label {{ width: 4in; height: 6in; border:2px solid black; padding:10px; font-size:12px; }}
          .row {{ display:flex; justify-content:space-between; }}
          .barcode {{ text-align:center; margin-top:20px; }}
          @media print {{ .no-print {{ display:none; }} }}
        </style></head><body>
        <div class="no-print" style="margin-bottom:15px;">
          <button onclick="window.print()" style="padding:10px 20px; background:#714B67; color:white; border:none; cursor:pointer;">🖨️ Imprimir Etiqueta</button>
          <button onclick="downloadZPL()" style="padding:10px 20px; margin-left:10px;">⬇️ Descargar ZPL</button>
          <button onclick="window.close()" style="padding:10px 20px; margin-left:10px;">Cerrar</button>
        </div>
        <div class="label">
          <div class="row"><b>Pedido/ Order No. {pallet.sale_order_id.name if pallet.sale_order_id else ''}</b> <span>Cod. Producto: {pallet.product_id.default_code or ''}</span> <span>CantX Tarima: {pallet.total_qty:.2f}</span></div>
          <div class="row" style="margin-top:10px;"><span>Pedido/ Order No. {pallet.customer_order_ref or ''}</span> <span>Cajas por Tarima: {pallet.box_count}</span> <span>Peso Bruto: {pallet.total_gross_weight:.2f} KG</span></div>
          <div class="row" style="margin-top:10px;"><span>Fecha: {pallet.date_packing.strftime('%d/%m/%Y') if pallet.date_packing else ''}</span> <span>Peso Neto: {pallet.total_net_weight:.2f} KG</span></div>
          <div style="margin-top:15px; font-size:11px;">{pallet.product_id.display_name}</div>
          <div style="margin-top:5px;">{pallet.customer_name or ''}</div>
          <div class="barcode">
            <svg id="barcode"></svg><br/>
            <b style="font-size:18px;">{pallet.name}</b>
          </div>
          <div style="font-size:8px; margin-top:10px; text-align:right;">Impreso por Odoo 19 - {pallet.operator or ''}</div>
        </div>
        <pre id="zpl" style="display:none;">{pallet.zpl_pallet}</pre>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
        <script>
          JsBarcode("#barcode", "{pallet.name}", {{format:"CODE128", width:2, height:80}});
          function downloadZPL() {{
            var zpl = document.getElementById('zpl').innerText;
            var blob = new Blob([zpl], {{type: 'text/plain'}});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a'); a.href=url; a.download='{pallet.name}_MASTER.zpl'; a.click();
          }}
        </script>
        </body></html>
        '''
        return html

    @http.route('/mrp_packing/print_box/<int:box_id>', type='http', auth='user')
    def print_box(self, box_id, **kw):
        box = request.env['mrp.box'].browse(box_id)
        pallet = box.pallet_id
        html = f'''
        <html><head><title>Etiqueta Caja {box.name}</title>
        <style>
          body {{ font-family: Arial; margin:0; padding:20px; }}
          .label {{ width: 4in; height: 6in; border:2px solid black; padding:10px; font-size:11px; }}
          .barcode {{ text-align:center; }}
          @media print {{ .no-print {{ display:none; }} }}
        </style></head><body>
        <div class="no-print" style="margin-bottom:10px;">
          <button onclick="window.print()" style="padding:10px 20px; background:#714B67; color:white; border:none;">🖨️ Imprimir</button>
          <button onclick="downloadZPL()" style="padding:10px 20px; margin-left:10px;">⬇️ Descargar ZPL</button>
        </div>
        <div class="label">
          <div>O. Fab {pallet.production_id.name} | Prod {pallet.product_id.default_code} | Rollo {box.master_lot} | Op {pallet.operator}</div>
          <div>Cliente {pallet.customer_code} | Fecha {pallet.date_packing.strftime('%d/%m/%Y') if pallet.date_packing else ''} | Mill {box.mill_roll} | Maq {pallet.machine}</div>
          <div>Pedido {pallet.sale_order_id.name if pallet.sale_order_id else ''} | Destiny {box.customer_item_no} | Neto {box.peso_neto} | Box #{box.sequence}</div>
          <div>LOTE/PALLET {pallet.name} - TARA {box.tara}</div>
          <div style="font-size:13px; font-weight:bold; margin:5px 0;">{pallet.product_id.display_name}</div>
          <div class="barcode"><svg id="bc1"></svg><div>{box.customer_item_no or ''}</div></div>
          <div class="barcode"><svg id="bc2"></svg><div>Qty {box.qty_per_box}</div></div>
          <div class="barcode"><svg id="bc3"></svg><div>{box.name}</div></div>
        </div>
        <pre id="zpl" style="display:none;">{box.zpl_box}</pre>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
        <script>
          JsBarcode("#bc1", "{box.customer_item_no or '1525'}", {{format:"CODE128", width:1.5, height:50}});
          JsBarcode("#bc2", "{box.qty_per_box}", {{format:"CODE128", width:1.5, height:50}});
          JsBarcode("#bc3", "{box.name}", {{format:"CODE128", width:1.8, height:60}});
          function downloadZPL() {{
            var blob = new Blob([document.getElementById('zpl').innerText], {{type:'text/plain'}});
            var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='{box.name}.zpl'; a.click();
          }}
        </script>
        </body></html>
        '''
        return html

    @http.route('/mrp_packing/download_zpl_pallet/<int:pallet_id>', type='http', auth='user')
    def download_zpl_pallet(self, pallet_id, **kw):
        pallet = request.env['mrp.pallet'].browse(pallet_id)
        headers = [('Content-Type', 'text/plain'), ('Content-Disposition', f'attachment; filename="{pallet.name}_MASTER.zpl"')]
        return request.make_response(pallet.zpl_pallet or '', headers)
