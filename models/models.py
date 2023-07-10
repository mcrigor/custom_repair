# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from odoo.http import request
from dotenv import load_dotenv
from datetime import datetime
import pyodbc
import os
import re
import logging

_logger = logging.getLogger(__name__)

load_dotenv()


class CustomRepair(models.Model):
    _name = 'custom.repair'
    _description = 'custom.repair'

    product = fields.Char(string='Product')
    cantidad = fields.Char(string='Cantidad')
    total = fields.Char(string='Total Neto ($)')
    repair_order = fields.Many2one('repair.order', 'My Repair')


class InheritRepair(models.Model):
    _inherit = 'repair.order'

    invoice_no = fields.Char(string="Invoice No.")
    create_date = fields.Datetime(string="Create date")
    date_created = fields.Datetime(string="Create date")
    total_net = fields.Float(string="Total Net")
    
    custom_repair_ids = fields.One2many('custom.repair', 'repair_order', 'Test Repair')

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


    @api.multi
    def sync(self):
        invoice_no = self.invoice_no
        # products = [('0001495310', 'ZI41002003', 'SENSOR DELANTERO (DERECHO)', 1.0, 685000.0), ('0001495310', 'SE-35736', 'MANO DE OBRA MECANICO', 1.0, 140000.0)]
        # customer = [('0001495310', '76124915', 'H. MOTORES S.A.', '15 NORTE 1018', 'VIÑA DEL MAR', 'V REGION DE VALPARAISO', '32-2151101', datetime.datetime(2023, 6, 22, 0, 0))]
        products = self.get_products(str(invoice_no))
        customer = self.get_customer(str(invoice_no))
        try:
            cust_name = customer[0][2]
            _logger.info('cust_name: %s', cust_name)
            customer_q = self.env['res.partner'].search([('name', 'ilike', cust_name.strip())], limit=1)
            _logger.info('customer date: %s', customer[0][7])
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
                'product': '[' + product[1] + '] ' + product[2],
                'cantidad': product[3],
                'total': format(product[4] / 1000, ",.3f").replace(",", "."),
            }
            repairs_data.append(vals)
        self.custom_repair_ids = repairs_data

