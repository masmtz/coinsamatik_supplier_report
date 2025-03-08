# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

from dateutil.relativedelta import *
from datetime import datetime
from datetime import timedelta
from collections import defaultdict
from dateutil.relativedelta import relativedelta  # Importar relativedelta

####### TRABAJAR CON LOS EXCEL
import base64
import xlsxwriter
import tempfile
from xlsxwriter.utility import xl_rowcol_to_cell
import io
from PIL import Image
from io import BytesIO


class CoinsamatikSupplierReport(models.TransientModel):
    _name = "coinsamatik.supplier.report"
    _description = "Supplier report Coinsamatik"

    # CAMPOS PARA GENERAR EL ARCHIVO
    # datas_fname = fields.Char("File Name", size=256)
    file_data = fields.Binary("Layout")
    # download_file = fields.Boolean("Downlad file")
    # cadena_decoding = fields.Text("Binary not encoding")

    name = fields.Char()
    partner_id = fields.Many2one("res.partner")
    start_date = fields.Date(string="Date start", default=fields.Date.today())
    end_date = fields.Date(string="Date end", default=fields.Date.today())

    @api.onchange("start_date", "end_date")
    def calculate_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("Date start should not be later than date end"))

    def print_report(self):
        xlines = []
        # FIRST WE NEED TO FIND THE INVOICE LINES (OUT_INVOICE) THAT MATCHES THE DATES SELECTED
        invoice_out_line_ids = self.env["account.move.line"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("invoice_date", "<=", self.end_date),
                ("invoice_date", ">=", self.start_date),
                ("parent_state", "=", "posted"),
                ("account_id", "=", self.env.ref("l10n_mx.1_cuenta401_01").id),
            ]
        )

        # THEN, ITERATE THE INVOICE LINES (OUT_INVOICE)
        for line in invoice_out_line_ids:
            # VALIDATE THAT THE PRODUCT MATCHES THE PARTNER SELECTED
            if (
                line.product_id.seller_ids
                and line.product_id.seller_ids[0].partner_id == self.partner_id
            ):
                # SEARCH THE LAST INVOICE LINE (IN_INVOICE) WITH THE PRODUCT WE ARE ITERATING TO GET THE COST
                # WHERE THE INVOICE_DATE OF THE IN_INVOICE IS BEFORE THE INVOICE_DATE OF OUT_INVOICE
                invoice_in_line_ids = (
                    self.env["account.move.line"]
                    .search(
                        [
                            ("move_type", "=", "in_invoice"),
                            ("product_id", "=", line.product_id.id),
                            ("parent_state", "=", "posted"),
                            ("invoice_date", "<=", line.invoice_date),
                        ]
                    )
                    .sorted(key=lambda l: l.id, reverse=True)
                )
                cost = 0
                currency_cost = False
                if invoice_in_line_ids:
                    cost = invoice_in_line_ids[0].price_unit
                    currency_cost = invoice_in_line_ids[0].currency_id.name

                report_fields = {
                    "FECHA": line.invoice_date,
                    "FACTURA": line.move_id.name,
                    "CLIENTE": line.partner_id.name,
                    "CIUDAD": line.partner_id.city,
                    "NO_ARTICULO": line.product_id.default_code,
                    "MODELO": line.product_id.name,
                    "CANTIDAD": line.quantity,
                    "PRECIO_UNITARIO": line.price_unit,
                    "MONEDA_VENTA": line.currency_id.name,
                    "COSTO_UNITARIO": cost,
                    "MONEDA_COSTO": currency_cost,
                    "TOTAL_VENTA": line.price_subtotal,
                }
                xlines.append(report_fields)

        return self.export_xlsx_file(xlines)

    def export_xlsx_file(self, xlines):
        output = io.BytesIO()
        book = xlsxwriter.Workbook(output)
        sheet = book.add_worksheet("Picture")

        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d").strftime(
            "%d/%m/%Y"
        )
        finish_date = datetime.strptime(str(self.end_date), "%Y-%m-%d").strftime(
            "%d/%m/%Y"
        )

        # FORMATOS
        header = book.add_format({"bold": True})
        header.set_bg_color("gray")

        sheet.write("A1", "FECHA INICIO", header)
        sheet.write("B1", start_date, header)
        sheet.write("A2", "FECHA FINAL", header)
        sheet.write("B2", finish_date, header)
        sheet.write("A3", "PROVEEDOR", header)
        sheet.write("B3", self.partner_id.name, header)

        # ENCABEZADO DE REPORTE
        sheet.write("A5", "FECHA", header)
        sheet.write("B5", "FACTURA", header)
        sheet.write("C5", "CLIENTE", header)
        sheet.write("D5", "CIUDAD", header)
        sheet.write("E5", "NO. ARTICULO", header)
        sheet.write("F5", "MODELO", header)
        sheet.write("G5", "CANTIDAD", header)
        sheet.write("H5", "PRECIO UNITARIO", header)
        sheet.write("I5", "MONEDA VENTA", header)
        sheet.write("J5", "COSTO UNITARIO", header)
        sheet.write("K5", "MONEDA COSTO", header)
        sheet.write("L5", "TOTAL VENTA", header)

        date_format = book.add_format({"num_format": "dd/mm/yyyy"})
        float_format = book.add_format({"num_format": "#,##0.00"})
        integer_format = book.add_format({"num_format": "#,##0"})

        if len(xlines) < 1:
            raise ValidationError(
                _(
                    "The parameters provided do not generate information to complete the report, please try to modify them."
                )
            )
            return {}

        row = 6
        count = 1
        for record in xlines:
            sheet.write("A%s" % (row), record["FECHA"], date_format)
            sheet.write("B%s" % (row), record["FACTURA"])
            sheet.write("C%s" % (row), record["CLIENTE"])
            sheet.write("D%s" % (row), record["CIUDAD"])
            sheet.write("E%s" % (row), record["NO_ARTICULO"])
            sheet.write("F%s" % (row), record["MODELO"])
            sheet.write("G%s" % (row), record["CANTIDAD"], integer_format)
            sheet.write("H%s" % (row), record["PRECIO_UNITARIO"], float_format)
            sheet.write("I%s" % (row), record["MONEDA_VENTA"])
            sheet.write("J%s" % (row), record["COSTO_UNITARIO"], float_format)
            sheet.write("K%s" % (row), record["MONEDA_COSTO"])
            sheet.write("L%s" % (row), record["TOTAL_VENTA"], float_format)

            row += 1

        book.close()
        wiz_id = self.env["coinsamatik.supplier.report"].create(
            {"file_data": base64.encodebytes(output.getvalue())}
        )
        value = dict(
            type="ir.actions.act_url",
            target="self",
            url="/web/content?model=%s&id=%s&field=file_data&download=true&filename=Rerpote_Proveedor.xlsx"
            % (self._name, wiz_id.id),
        )
        return value
