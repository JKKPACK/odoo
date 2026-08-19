{
    "name": "MRP Empaquetado Final - Armado de Tarimas",
    "version": "19.0.1.6.3",
    "summary": "Empaquetado post-manufactura: cajas/bobinas, tarimas, ZPL y packing list",
    "category": "Manufacturing",
    "author": "Oscar Morocho <oscar.morocho@gateway-resources.com>",
    "depends": ["mrp", "sale", "stock", "hr", "mrp_multi_lot_distribution"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/mrp_workcenter_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_pallet_views.xml",
        "views/mrp_box_views.xml",
        "wizards/packing_wizards_views.xml",
        "wizards/label_preview_wizard_views.xml",
        "reports/packing_list_report.xml",
        "reports/packing_list_template.xml",
        "reports/box_labels_zpl.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "mrp_packing_final/static/src/scss/zpl_preview.scss",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
