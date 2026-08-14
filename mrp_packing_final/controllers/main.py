from odoo import http
from odoo.http import request


class PackingPrintController(http.Controller):
    @http.route(
        [
            "/mrp_packing/download_zpl_pallet/<int:pallet_id>",
            "/es/mrp_packing/download_zpl_pallet/<int:pallet_id>",
        ],
        type="http", auth="user", methods=["GET"], csrf=False,
    )
    def download_zpl_pallet(self, pallet_id, **kw):
        pallet = request.env["mrp.pallet"].browse(pallet_id).exists()
        if not pallet:
            return request.not_found()
        pallet.check_access("read")
        return request.make_response(
            pallet.generate_pallet_zpl(),
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Disposition", 'attachment; filename="%s_MASTER.zpl"' % pallet.name),
            ],
        )

    @http.route(
        [
            "/mrp_packing/download_zpl_box/<int:box_id>",
            "/es/mrp_packing/download_zpl_box/<int:box_id>",
        ],
        type="http", auth="user", methods=["GET"], csrf=False,
    )
    def download_zpl_box(self, box_id, **kw):
        box = request.env["mrp.box"].browse(box_id).exists()
        if not box:
            return request.not_found()
        box.check_access("read")
        return request.make_response(
            box.generate_box_zpl(),
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Disposition", 'attachment; filename="%s.zpl"' % box.name),
            ],
        )
