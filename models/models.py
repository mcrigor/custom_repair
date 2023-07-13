# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from odoo.http import request
from dotenv import load_dotenv
from datetime import datetime
import pyodbc
import os
import re
import logging
import decimal

_logger = logging.getLogger(__name__)

load_dotenv()


class CustomRepair(models.Model):
    _name = 'custom.repair'
    _description = 'custom.repair'

    product_code = fields.Char(string='Product Code')
    code = fields.Char(string='Code')
    product = fields.Char(string='Product')
    cantidad = fields.Float(string='Cantidad')
    total = fields.Float(string='Total Neto ($)')
    repair_order = fields.Many2one('repair.order', 'My Repair')

    formatted_cantidad = fields.Char(string='Cantidad', compute='_compute_formatted_cantidad')
    formatted_total = fields.Char(string='Total Neto ($)', compute='_compute_formatted_total')

    @api.depends('cantidad')
    def _compute_formatted_cantidad(self):
        for record in self:
            record.formatted_cantidad = '{0:.3f}'.format(record.cantidad)

    @api.depends('total')
    def _compute_formatted_total(self):
        for record in self:
            record.formatted_total = '{:,.0f}'.format(record.total).replace(',', '.')

    def select_row(self):
        _logger.info('Current ID: %s', self.id)
        _logger.info('Code: %s', self.code)
        self.repair_order.total_net = self.total/self.cantidad
        code = self.code
        _logger.info('Code again: %s', code)
        get_product_name = self.env['product.product'].search([('default_code', '=', str(code).strip())])
        _logger.info("get product name: %s", get_product_name)
        # TODO Add validation if get_product_name is true
        if get_product_name:
            _logger.info('Product name from template: %s', get_product_name.product_tmpl_id.name)
            self.repair_order.product_id = get_product_name.id
        else:
            raise exceptions.ValidationError("Product with internal reference " + self.code + " not found.")


class InheritRepair(models.Model):
    _inherit = 'repair.order'

    invoice_no = fields.Char(string="Invoice No.")
    create_date = fields.Datetime(string="Create date")
    date_created = fields.Datetime(string="Create date")
    total_net = fields.Float(string="Total Net")
    
    custom_repair_ids = fields.One2many('custom.repair', 'repair_order', 'Test Repair')

    formatted_field = fields.Char(string='Formatted Field', compute='_compute_formatted_field')

    @api.depends('total_net')
    def _compute_formatted_field(self):
        for record in self:
            record.formatted_field = '{:,.0f}'.format(record.total_net).replace(',', '.')

    def get_products(self, invoice_no):
        # SQL Server connection parameters
        server = os.getenv("DB_HOST")
        database = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        print("Server: ", server)
        driver = '{ODBC Driver 17 for SQL Server}'
        connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        query = """
        SELECT MAEEDO.NUDO,  
        MAEDDO.KOPRCT,
        MAEDDO.NOKOPR,
        MAEDDO.CAPRCO1,
        MAEDDO.VANELI  
        FROM    MAEEDO  
        LEFT OUTER JOIN MAEEN ON MAEEDO.ENDO = MAEEN.KOEN AND MAEEDO.SUENDO = MAEEN.SUEN 
        INNER JOIN MAEDDO MAEDDO ON MAEEDO.IDMAEEDO = MAEDDO.IDMAEEDO  
        WHERE MAEEDO.TIDO IN ('FCV') AND MAEEDO.NUDO LIKE '%' + ?
        """
        cursor.execute(query, (invoice_no,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    def get_customer(self, customer):
        # SQL Server connection parameters
        server = os.getenv("DB_HOST")
        database = os.getenv("DB_NAME")
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        print("Server: ", server)
        driver = '{ODBC Driver 17 for SQL Server}'
        connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        query = """
        SELECT MAEEDO.NUDO,  
        MAEEDO.ENDO,  
        MAEEN.NOKOEN,  
        MAEEN.DIEN,
        TABCM.NOKOCM, 
        TABCI.NOKOCI,
        MAEEN.FOEN,
        MAEEDO.FEEMDO  
        FROM MAEEDO  
        LEFT OUTER JOIN MAEEN ON MAEEDO.ENDO = MAEEN.KOEN AND MAEEDO.SUENDO = MAEEN.SUEN
        LEFT OUTER JOIN TABCI ON MAEEN.PAEN = TABCI.KOPA AND MAEEN.CIEN = TABCI.KOCI
        LEFT OUTER JOIN TABCM TABCM ON MAEEN.PAEN = TABCM.KOPA AND MAEEN.CIEN = TABCM.KOCI AND MAEEN.CMEN = TABCM.KOCM
        WHERE MAEEDO.TIDO IN ('FCV') AND MAEEDO.NUDO LIKE '%' + ?
        """
        cursor.execute(query, (customer,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        print("Rows: ", rows)
        return rows
    
    def convert_float(self, float_value):
        """Converts a float value to the desired format."""
        decimal_value = decimal.Decimal(float_value)
        formatted_value = decimal_value.quantize(decimal.Decimal("0.000"))
        formatted_value = str(formatted_value).replace(",", "")
        return formatted_value

    def convert_to_vat_format(self, number):
        region_code = str(number)[:2]  # Extract the first two digits as the region code
        serial_number = str(number)[2:5] + '.' + str(number)[5:8]  # Format the serial number
        verification_char = '0'  # Calculate the verification character 
        vat_number = f"{region_code}.{serial_number}-{verification_char}"  # Combine all parts
        return vat_number

    @api.multi
    def sync(self):
        invoice_no = self.invoice_no
        # products = [('0001495310', 'ZI41002003', 'SENSOR DELANTERO (DERECHO)', 1.0, 685000.0), ('0001495310', 'SE-35736', 'MANO DE OBRA MECANICO', 1.0, 140000.0)]
        # customer = [('0001495310', '76124915', 'H. MOTORES S.A.', '15 NORTE 1018', 'VIÑA DEL MAR', 'V REGION DE VALPARAISO', '32-2151101', datetime.datetime(2023, 6, 22, 0, 0))]
        products = self.get_products(str(invoice_no))
        customer = self.get_customer(str(invoice_no))
        try:
            _logger.info('cust_name: %s', customer[0][2])
            vat = str(customer[0][1])
            _logger.info('VAT: %s', vat)
            vat_format = self.convert_to_vat_format(vat)
            customer_q = self.env['res.partner'].search([('vat', '=', vat_format)], limit=1)  # Select customer in odoo that matches the vat
            _logger.info('VAT format: %s', vat_format)
            _logger.info('Customer_q: %s', customer_q)
            if customer_q:
                self.partner_id = customer_q.id
                new_create_date = customer[0][7]
                self.date_created = new_create_date 
            else:
                raise exceptions.ValidationError("Customer not found with the name " + customer[0][2])
        except IndexError:
            raise exceptions.ValidationError("Invoice number not found.")
        repair_orders = self.env['custom.repair'].search([('repair_order', '=', self.id)])  # Search custom repair records with current partner
        for ro in repair_orders:
            _logger.info('ro: %s', ro)
        repair_orders.unlink()
        repairs_data = []
        for product in products:
            vals = {
                'product': product[2],
                'code': product[1],
                'product_code': '[' + product[1] + '] ' + product[2],
                'cantidad': self.convert_float(product[3]),
                'total': product[4],
            }
            _logger.info('cantidad: %s', product[3])
            _logger.info('toal neto: %s', product[4])
            repairs_data.append(vals)
        self.custom_repair_ids = repairs_data

