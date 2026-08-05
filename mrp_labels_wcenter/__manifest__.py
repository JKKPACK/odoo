# -*- coding: utf-8 -*-
{
    "name": "MRP Production Custom Labels",
    "version": "19.0.1.0.1",
    "summary": "Generación y pesaje dinámico de etiquetas por rollo/caja en Órdenes de Fabricación",
    "description": """
        Módulo personalizado para la industria de empaques flexibles y manufactura.
        Permite:
        - Configurar prefijos únicos por Centro de Trabajo.
        - Utilizar una secuencia global e infinita de 8 dígitos para etiquetas.
        - Asistente (Wizard) para capturar el número de etiquetas y pesos individuales por rollo.
        - Validación estricta de peso total contra el límite parcial/total de la Orden de Fabricación.
        - Formato de etiqueta térmica QWeb de 4" x 6" con códigos de barras y QR.
    """,
    "author": "Desarrollador Odoo",
    "category": "Manufacturing/Manufacturing",
    "sequence": 10,
    "depends": [
        "mrp",
        "barcodes",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "report/paperformat_data.xml",
        "report/production_label_template.xml",
        "report/mrp_production_label_reports.xml",
        "wizard/mrp_production_label_wizard_view.xml",
        "views/mrp_workcenter_views.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
