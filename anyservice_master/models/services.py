# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductCategory(models.Model):
    _inherit = "product.category"

    is_anyservice_category = fields.Boolean('Anyservice Category')

    state = fields.Selection([('draft','Draft'),('pending','Pending'),('approved','Approved'),('banned','Banned')], default='draft')

    def set_draft(self):
        self.state='draft'

    def submit(self):
        self.state='pending'

    def approve(self):
        self.state='approved'

    def ban_user(self):
        self.state='banned'

    def get_categories(self,vals):
        categories = []
        for categ in self.sudo().search([('is_anyservice_category','=',True)]):
            categories.append(categ.name)
        return {
            'result':'Success',
            'categories':categories,
        }

class AnyserviceService(models.Model):
    _name = 'anyservice.service'
    _description = 'Anyservice Services'

    name = fields.Char(required=True)
    partner_id = fields.Many2one('res.partner',string='Belongs To',domain=[('state','=','approved'),('is_anyservice_user','=',True),('user_type','=','agent')] ,required=True)
    category_id = fields.Many2one('product.category',string='Service Category',domain=[('state','=','approved')] ,required=True)
    price = fields.Float('Price')
    is_measurable = fields.Boolean()
    delivery_charge = fields.Boolean('Delivery Charge', default=True)
