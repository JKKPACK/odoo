from odoo import http
from odoo.http import request


class PackingPrintController(http.Controller):
    @http.route(
        [
            "/mrp_packing/print_pallet/<int:pallet_id>",
            "/es/mrp_packing/print_pallet/<int:pallet_id>",
        ],
        type="http",
        auth="user",
    )
    def print_pallet(self, pallet_id, **kw):
        p = request.env["mrp.pallet"].sudo().browse(pallet_id)
        prod_code = p.product_id.default_code or ""
        prod_name = p.product_id.display_name or ""
        so_name = p.sale_order_id.name or ""
        cust_order = p.customer_order_ref or ""
        cust_name = p.customer_name or ""
        html = f"""
        <html><head><title>Master {p.name}</title>
        <style>@page{{size:4in 6in;margin:0}}body{{font-family:Arial;margin:0;padding:0;width:4in;height:6in;font-size:10px}}.label{{width:3.8in;height:5.8in;border:1px solid #000;padding:8px;box-sizing:border-box}}.row{{display:flex;justify-content:space-between;margin-bottom:4px}}.big{{font-size:15px;font-weight:bold}}.barcode{{text-align:center;margin-top:10px}}@media print{{.no-print{{display:none}}.label{{border:none}}}}</style></head><body>
        <div class="no-print" style="padding:8px;"><button onclick="window.print()" style="padding:10px 20px;background:#714B67;color:white;border:none;">Imprimir MASTER {p.name}</button></div>
        <div class="label">
          <div class="row"><div>Pedido/ Order No.<br><b>{so_name}</b></div><div>Cod. Producto/Product No.<br><b>{prod_code}</b></div><div>CantX Tarima/QtyPerPallet<br><b class="big">{p.total_qty:.2f}</b></div></div>
          <div class="row" style="margin-top:8px;"><div>Pedido/ Order No.<br><b class="big">{cust_order}</b></div><div>Cajas o Rollos por Tarima / Boxes or Rolls per Pallet<br><b class="big">{p.box_count}</b></div><div>Peso Bruto/ Gross Weight<br><b class="big">{p.total_gross_weight:.2f} KG</b></div></div>
          <div class="row" style="margin-top:8px;"><div>Fecha/Date<br><b class="big">{p.date_packing.strftime('%d/%m/%Y') if p.date_packing else ''}</b></div><div>Peso Neto/ Net Weight<br><b class="big">{p.total_net_weight:.2f} KG</b></div></div>
          <div style="margin-top:10px;font-size:9px;line-height:1.2;"><b>{prod_name}</b><br>{cust_name} - {p.customer_code or ''}<br>Operador {p.operator_id.name if p.operator_id else ''} Maquina {p.machine or ''}</div>
          <div class="barcode"><svg id="bcM"></svg><br><b>{p.name}</b></div>
          <div style="text-align:right;font-size:7px;margin-top:6px;">Impreso por Odoo - {p.operator_id.name if p.operator_id else ''}</div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
        <script>JsBarcode("#bcM","{p.name}",{{format:"CODE128",width:1.6,height:70}});</script>
        </body></html>"""
        return request.make_response(html, [("Content-Type", "text/html")])

    @http.route(
        [
            "/mrp_packing/print_box/<int:box_id>",
            "/es/mrp_packing/print_box/<int:box_id>",
        ],
        type="http",
        auth="user",
    )
    def print_box(self, box_id, **kw):
        b = request.env["mrp.box"].sudo().browse(box_id)
        p = b.pallet_id
        prod_code = p.product_id.default_code or ""
        prod_name = p.product_id.display_name or ""
        so_name = p.sale_order_id.name or ""
        cust_item = b.customer_item_no or p.production_id.customer_item_no or "1525"
        cust_code = p.customer_code or "C000206"
        html = f"""
        <html><head><title>Caja {b.name}</title>
        <style>@page{{size:4in 6in;margin:0}}body{{font-family:Arial;margin:0;padding:0;width:4in;height:6in;font-size:8px}}.label{{width:3.8in;height:5.8in;border:1px solid #000;padding:6px;box-sizing:border-box}}.row{{display:flex;justify-content:space-between}}.col{{flex:1}}.bold{{font-weight:bold}}.big{{font-size:11px;font-weight:bold}}.center{{text-align:center}}.sep{{border-top:1px solid #000;margin:4px 0}}@media print{{.no-print{{display:none}}.label{{border:none}}}}</style></head><body>
        <div class="no-print" style="padding:6px;"><button onclick="window.print()" style="padding:8px 16px;background:#714B67;color:white;border:none;">Imprimir {b.name}</button></div>
        <div class="label">
          <div class="row"><div class="col">O. Fab/ Mfg No.<br><b>{p.production_id.name}</b></div><div class="col">Cod. Producto/Product No.<br><b>{prod_code}</b></div><div class="col">Rollo Maestro/Master Roll<br><b>{b.master_lot or 'BMC00288264'}</b></div><div class="col">Operador<br><b>{p.operator_id.name if p.operator_id else ''}</b></div></div>
          <div class="row" style="margin-top:3px;"><div class="col">Cliente/Customer<br><b>{cust_code}</b></div><div class="col">Fecha/Date<br><b>{p.date_packing.strftime('%d/%m/%Y') if p.date_packing else '27/5/2026'}</b></div><div class="col">Mill/Roll<br><b>{b.mill_roll}</b></div><div class="col">Maquina/Machine<br><b>{p.machine or 'Bolseadora Mamata 3'}</b></div></div>
          <div class="row" style="margin-top:3px;"><div class="col">Pedido JkkPack:<br><b>{so_name}</b><br><span style="font-size:6px;">{prod_name[:60]}</span></div><div class="col">Destiny Item #<br><b class="big">{cust_item}</b></div><div class="col">Peso Neto/ NetWeight<br><b>{b.peso_neto} Kg</b></div><div class="col">CASE BOX ID #<br><b class="big">{b.sequence}</b><br>LOTE/PALLET<br><b>{p.name}</b></div></div>
          <div class="sep"></div>
          <div class="bold" style="font-size:10px;">{cust_item}-CHURCH BROTHERS GREEN LEAF LETTUCE</div>
          <div class="row" style="margin-top:5px;"><div class="col center">Customer Item #<br><svg id="bcCust"></svg><br><b>{cust_item}</b></div><div class="col center">Qty Mill/Roll<br><svg id="bcQty"></svg><br><b>{b.qty_per_box}</b></div></div>
          <div class="center" style="margin-top:5px;"><svg id="bcBox"></svg><br><b>{b.name}</b></div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
        <script>
          JsBarcode("#bcCust","{cust_item}",{{format:"CODE128",width:1.2,height:35}});
          JsBarcode("#bcQty","{b.qty_per_box}",{{format:"CODE128",width:1.2,height:35}});
          JsBarcode("#bcBox","{b.name}",{{format:"CODE128",width:1.5,height:45}});
        </script></body></html>"""
        return request.make_response(html, [("Content-Type", "text/html")])

    @http.route(
        [
            "/mrp_packing/print_all_boxes/<int:pallet_id>",
            "/es/mrp_packing/print_all_boxes/<int:pallet_id>",
        ],
        type="http",
        auth="user",
    )
    def print_all_boxes(self, pallet_id, **kw):
        p = request.env["mrp.pallet"].sudo().browse(pallet_id)
        boxes = ""
        for b in p.box_ids:
            cust_item = b.customer_item_no or p.production_id.customer_item_no or "1525"
            boxes += f"<div class='label'><div class='row'><div class='col'>O.Fab {p.production_id.name} Cod {p.product_id.default_code or ''} Master {b.master_lot or ''}</div><div class='col'>Op {p.operator_id.name if p.operator_id else ''}</div></div><div class='row'><div class='col'>Cliente {p.customer_code or ''} Fecha {p.date_packing.strftime('%d/%m/%Y') if p.date_packing else ''} Peso {b.peso_neto} Kg Box {b.sequence}</div></div><div class='row'><div class='col center'>Customer Item #<br><svg class='bcCust' data-value='{cust_item}'></svg><br><b>{cust_item}</b></div><div class='col center'>Qty<br><svg class='bcQty' data-value='{b.qty_per_box}'></svg><br><b>{b.qty_per_box}</b></div></div><div class='center'><svg class='bcBox' data-value='{b.name}'></svg><br><b>{b.name} / {p.name}</b></div></div><div style='page-break-after:always;'></div>"
        html = f"<html><head><title>Todas {p.name}</title><style>@page{{size:4in 6in;margin:0}}body{{font-family:Arial;margin:0;font-size:8px}}.label{{width:3.8in;height:5.8in;border:1px solid #000;padding:6px;box-sizing:border-box;margin:5px}}.row{{display:flex;justify-content:space-between}}.col{{flex:1}}.center{{text-align:center}}@media print{{.no-print{{display:none}}.label{{border:none}}}}</style></head><body><div class='no-print' style='padding:8px;'><button onclick='window.print()' style='padding:10px 20px;background:#714B67;color:white;border:none;'>Imprimir TODAS ({len(p.box_ids)})</button></div>{boxes}<script src='https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js'></script><script>document.querySelectorAll('.bcBox').forEach(el=>{{JsBarcode(el, el.dataset.value, {{format:'CODE128',width:1.5,height:45}})}});document.querySelectorAll('.bcCust').forEach(el=>{{JsBarcode(el, el.dataset.value, {{format:'CODE128',width:1.2,height:30}})}});document.querySelectorAll('.bcQty').forEach(el=>{{JsBarcode(el, el.dataset.value, {{format:'CODE128',width:1.2,height:30}})}});</script></body></html>"
        return request.make_response(html, [("Content-Type", "text/html")])

    @http.route(
        [
            "/mrp_packing/download_zpl_pallet/<int:pallet_id>",
            "/es/mrp_packing/download_zpl_pallet/<int:pallet_id>",
        ],
        type="http",
        auth="user",
    )
    def download_zpl_pallet(self, pallet_id, **kw):
        p = request.env["mrp.pallet"].sudo().browse(pallet_id)
        return request.make_response(
            p.zpl_pallet or "",
            [
                ("Content-Type", "text/plain"),
                (
                    "Content-Disposition",
                    'attachment; filename="%s_MASTER.zpl"' % p.name,
                ),
            ],
        )

    @http.route(
        [
            "/mrp_packing/download_zpl_box/<int:box_id>",
            "/es/mrp_packing/download_zpl_box/<int:box_id>",
        ],
        type="http",
        auth="user",
    )
    def download_zpl_box(self, box_id, **kw):
        b = request.env["mrp.box"].sudo().browse(box_id)
        return request.make_response(
            b.zpl_box or "",
            [
                ("Content-Type", "text/plain"),
                ("Content-Disposition", 'attachment; filename="%s.zpl"' % b.name),
            ],
        )
