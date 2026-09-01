from odoo import http
from odoo.http import request


class PackingPrintController(http.Controller):
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
            box.render_box_zpl(),
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Disposition", 'attachment; filename="%s.zpl"' % box.name),
            ],
        )
