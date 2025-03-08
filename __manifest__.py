{
    "name": "Reporte de facturas de proveedor",
    "summary": "Reporte que nos permite obtener precio de venta y costos de cierto proveedor.",
    "description": """
        Reporte que nos permite obtener precio de venta y costos de cierto proveedor.
    """,
    "author": "Samuel Mtz",
    "category": "Account",
    "version": "0.1",
    "depends": [
        "base",
        "account",
        "purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/groups.xml",
        "views/account_views.xml",
        "wizard/supplier_report_views.xml",
    ],
    "demo": [],
    "license": "LGPL-3",
}
