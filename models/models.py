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

    product_code = fields.Char(string='Product Code') # product + code field
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
            record.formatted_cantidad = '{:,.0f}'.format(record.cantidad).replace(',', '.')

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
            # TODO create a product if code is not found
            Product = request.env['product.product']
            new_product = Product.create({
                'name': self.product,
                'default_code': self.code,
                # Add more fields as required
            })
            _logger.info("Newly created product: %s", new_product)
            self.repair_order.product_id = new_product.id
            # raise exceptions.ValidationError("Product with internal reference " + self.code + " not found.")


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
        return rows
    
    def convert_float(self, float_value):
        """Converts a float value to the desired format."""
        decimal_value = decimal.Decimal(float_value)
        formatted_value = decimal_value.quantize(decimal.Decimal("0.000"))
        formatted_value = str(formatted_value).replace(",", "")
        return formatted_value

    def string_to_list(self, string):
        _logger.info("String: %s", string)
        list_of_integers = []
        for character in string:
            list_of_integers.append(int(character))

        return list_of_integers

    def format_vat(self, vat_number):
        # Remove hyphen and check digit
        vat_number = str(vat_number)
        
        # 1. Reverse the digits
        reversed_vat_number = vat_number[::-1].strip()
        _logger.info('1. Reverse the VAT number: %s', reversed_vat_number)

        # 2 convert to list the reverse vat number
        vat_list = self.string_to_list(reversed_vat_number)
        _logger.info('2 Vat list: %s', vat_list)

        # 3 Multiply each digit by its series and sum
        series = [2, 3, 4, 5, 6, 7, 2, 3]
        ans_to_multiplier = []

        for i in range(len(vat_list)):
            product = vat_list[i] * series[i]
            ans_to_multiplier.append(product)
        sum_of_multiplier = sum(ans_to_multiplier)
        _logger.info('3 Multiply each digit by its series and sum: %s', sum(ans_to_multiplier))

        # 4 Divide sum_of_multiplier to 11
        divided_multiplier = sum_of_multiplier/11
        _logger.info('4 Divide sum_of_multiplier to 11: %s', divided_multiplier)

        # 5 Multiply divided_multiplier to 11
        multiply_by_11 = int(divided_multiplier) * 11
        _logger.info('5 Multiply divided_multiplier to 11: %s', multiply_by_11)

        # 6 ans to 3 minus ans to 5
        three_minus_5 = sum_of_multiplier - multiply_by_11
        _logger.info('6 ans to 3 minus ans to 5: %s', three_minus_5)

        # 7 Subtract 11 to step 6
        check_digit = 11-three_minus_5
        if check_digit == 11:
            check_digit = 0
        elif check_digit == 10:
            check_digit = K
        else:
           check_digit = 11-three_minus_5
        _logger.info('7 Subtract 11 to step 6: %s', check_digit)
        
        formatted_vat = f"{vat_number[:2]}.{vat_number[2:5]}.{vat_number[5:8]}-{check_digit}"
        
        return formatted_vat

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
            vat_format = self.format_vat(vat)
            customer_q = self.env['res.partner'].search([('vat', '=', vat_format)], limit=1)  # Select customer in odoo that matches the vat
            _logger.info('VAT format: %s', vat_format)
            _logger.info('Customer_q: %s', customer_q)
            if customer_q:
                self.partner_id = customer_q.id
                new_create_date = customer[0][7]
                self.date_created = new_create_date 
            else:
                # Create customer here if not found
                customer_create = request.env['res.partner'].create({
                    'name': customer[0][2],
                    'street': customer[0][3],
                    'city': customer[0][4],
                    'state': customer[0][5],
                    'phone': customer[0][6],
                    'vat': vat_format # calculated vat here
                })
                # Set the created partner in repair form view
                _logger.info("Newly created customer: %s", customer_create)
                self.partner_id = customer_create.id
                new_create_date = customer[0][7]
                self.date_created = new_create_date 
                # raise exceptions.ValidationError("Customer not found with the name " + customer[0][2])
        except IndexError:
            raise exceptions.ValidationError("Invoice number not found.")  # this error will pop up if the invoice no. enetered in invoice_no field not found in sql server
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

