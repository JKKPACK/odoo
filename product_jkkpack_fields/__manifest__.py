# __manifest__.py
{
    'name': 'Product JKKPACK Fields',
    'version': '19.0.1.0.0',
    'depends': ['product', 'stock'],
    'author': 'Luis',
    'category': 'Inventory',
    'description': 'Añade pestaña JKKPACK con campos personalizados en productos',
    'data': [
        'views/product_template_views.xml',
        'views/product_family_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
