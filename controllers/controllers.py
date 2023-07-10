# -*- coding: utf-8 -*-
from odoo import http

# class CustomRepair(http.Controller):
#     @http.route('/custom_repair/custom_repair/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_repair/custom_repair/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_repair.listing', {
#             'root': '/custom_repair/custom_repair',
#             'objects': http.request.env['custom_repair.custom_repair'].search([]),
#         })

#     @http.route('/custom_repair/custom_repair/objects/<model("custom_repair.custom_repair"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_repair.object', {
#             'object': obj
#         })