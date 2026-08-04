
from odoo import http
from odoo.http import request
class PackingPrintController(http.Controller):
    @http.route(['/mrp_packing/print_pallet/<int:pallet_id>', '/es/mrp_packing/print_pallet/<int:pallet_id>'], type='http', auth='user')
    def print_pallet(self, pallet_id, **kw):
        pallet = request.env['mrp.pallet'].sudo().browse(pallet_id)
        if not pallet.exists():
            return request.not_found()
        html = "<html><body><h1>Master %s</h1><button onclick='window.print()'>Imprimir</button><br><svg id='bc'></svg><script src='https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js'></script><script>JsBarcode('#bc','%s',{format:'CODE128',width:2,height:80});</script></body></html>" % (pallet.name, pallet.name)
        return request.make_response(html, [('Content-Type','text/html')])
    @http.route(['/mrp_packing/download_zpl_pallet/<int:pallet_id>', '/es/mrp_packing/download_zpl_pallet/<int:pallet_id>'], type='http', auth='user')
    def download_zpl_pallet(self, pallet_id, **kw):
        pallet = request.env['mrp.pallet'].sudo().browse(pallet_id)
        return request.make_response(pallet.zpl_pallet or '', [('Content-Type','text/plain'),('Content-Disposition','attachment; filename="%s_MASTER.zpl"' % pallet.name)])
    @http.route(['/mrp_packing/print_box/<int:box_id>', '/es/mrp_packing/print_box/<int:box_id>'], type='http', auth='user')
    def print_box(self, box_id, **kw):
        box = request.env['mrp.box'].sudo().browse(box_id)
        if not box.exists():
            return request.not_found()
        html = "<html><body><h1>Caja %s Pallet %s</h1><button onclick='window.print()'>Imprimir</button><br><svg id='bc'></svg><script src='https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js'></script><script>JsBarcode('#bc','%s',{format:'CODE128',width:2,height:60});</script></body></html>" % (box.name, box.pallet_id.name, box.name)
        return request.make_response(html, [('Content-Type','text/html')])
    @http.route(['/mrp_packing/download_zpl_box/<int:box_id>', '/es/mrp_packing/download_zpl_box/<int:box_id>'], type='http', auth='user')
    def download_zpl_box(self, box_id, **kw):
        box = request.env['mrp.box'].sudo().browse(box_id)
        return request.make_response(box.zpl_box or '', [('Content-Type','text/plain'),('Content-Disposition','attachment; filename="%s.zpl"' % box.name)])
    @http.route(['/mrp_packing/print_all_boxes/<int:pallet_id>', '/es/mrp_packing/print_all_boxes/<int:pallet_id>'], type='http', auth='user')
    def print_all_boxes(self, pallet_id, **kw):
        pallet = request.env['mrp.pallet'].sudo().browse(pallet_id)
        if not pallet.exists():
            return request.not_found()
        boxes = ""
        for b in pallet.box_ids:
            boxes += "<div style='border:2px solid black;padding:10px;margin:10px;width:4in;'><b>%s - %s</b><br><svg class='bc' data-value='%s'></svg></div><div style='page-break-after:always;'></div>" % (pallet.name, b.name, b.name)
        html = "<html><head></head><body><button onclick='window.print()'>Imprimir TODAS (%s)</button>%s<script src='https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js'></script><script>document.querySelectorAll('.bc').forEach(function(el){JsBarcode(el, el.dataset.value, {format:'CODE128',width:1.8,height:60});});</script></body></html>" % (len(pallet.box_ids), boxes)
        return request.make_response(html, [('Content-Type','text/html')])
