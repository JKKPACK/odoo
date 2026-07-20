# -*- coding: utf-8 -*-
{
    'name': 'Zebra ZT411 Label Custom Print & Preview',
    'version': '19.0.1.0.0',
    'summary': 'Generación de etiquetas ZPL para Zebra ZT411 con vista previa interactiva vía Labelary API',
    'category': 'Inventory/Warehouse',
    'author': 'Odoo Consultant',
    'depends': ['stock', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_label_preview_wizard_view.xml',
        'views/stock_move_line_views.xml',
        'report/zebra_label_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
