# -*- coding: utf-8 -*-
{
    'name': 'purchase_in_stock',
    'version': '19.0.1.0.0',
    'summary': 'vista de datos de compra en recepcion',
    'category': 'Inventory/Warehouse',
    'author': 'Luis Garcia',
    'depends': ['stock', 'purchase'],
    'data': [
 
        'views/recep_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}