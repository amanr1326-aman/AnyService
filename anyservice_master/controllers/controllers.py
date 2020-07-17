# -*- coding: utf-8 -*-
# from odoo import http


# class AnyserviceMaster(http.Controller):
#     @http.route('/anyservice_master/anyservice_master/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/anyservice_master/anyservice_master/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('anyservice_master.listing', {
#             'root': '/anyservice_master/anyservice_master',
#             'objects': http.request.env['anyservice_master.anyservice_master'].search([]),
#         })

#     @http.route('/anyservice_master/anyservice_master/objects/<model("anyservice_master.anyservice_master"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('anyservice_master.object', {
#             'object': obj
#         })
