# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

def decrypt(data):
    return data

def encrypt(data):
    return data

def clean_str_data(data):
    if type(data)==dict:
        for key in data:
            if type(data[key])==str:
                data[key] = data[key].strip()
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
        for categ in self.sudo().search([('is_anyservice_category','=',True),('state','=','approved')]):
            if vals.get('all'):
                categories.append(categ.name)
            elif self.env['anyservice.service'].sudo().search(['|',('category_id','=',categ.id),('category_id','child_of',categ.id)],count=True):
                categories.append(categ.name)
        return {
            'result':'Success',
            'categories':categories,
        }

class AnyserviceService(models.Model):
    _name = 'anyservice.service'
    _description = 'Anyservice Services'

    name = fields.Char(required=True)
    details = fields.Text('Description')
    partner_id = fields.Many2one('res.partner',string='Belongs To',domain=[('state','=','approved'),('is_anyservice_user','=',True),('user_type','=','agent')] ,required=True)
    category_id = fields.Many2one('product.category',string='Service Category',domain=[('state','=','approved')] ,required=True)
    price = fields.Float('Price')
    is_measurable = fields.Boolean()
    delivery_charge = fields.Boolean('Delivery Charge', default=True)
    rating = fields.Float('Rating')

    image = fields.Image("Image", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_1024 = fields.Image("Image 1024", related="image", max_width=1024, max_height=1024, store=True)
    image_512 = fields.Image("Image 512", related="image", max_width=512, max_height=512, store=True)
    image_256 = fields.Image("Image 256", related="image", max_width=256, max_height=256, store=True)
    image_128 = fields.Image("Image 128", related="image", max_width=128, max_height=128, store=True)

    def create_service(self,vals):
        clean_str_data(vals)
        id = decrypt(vals.get('login'))
        user = self.env['res.partner'].search([('id','=',id),('is_anyservice_user','=',True)])
        category_id = self.env['product.category'].sudo().search([('is_anyservice_category','=',True),('name','=',vals.get('category')),('state','=','approved')])[0]
        if category_id:
            code = self.env['ir.sequence'].sudo().next_by_code('anyservice.product')
            service_id = self.sudo().create({
                    'name':vals.get('name')+' \n'+code,
                    'image':vals.get('image',False) or user.parent_id.image_1920,
                    'partner_id':id,
                    'category_id':category_id.id,
                    'price':abs(float(vals.get('price'))),
                    'is_measurable':vals.get('measurable'),
                    'delivery_charge':vals.get('delivery_charge'),
                    'details':vals.get('description')
                })
            self.env['anyservice.notification'].sudo().create({
                    'name':vals.get('name'),
                    'message':'Your Service/Product is created and Approved',
                    'model_name':'anyservice.service',
                    'record_name':service_id.id,
                    'partner_id':id,
                })
            return {
                'result':'Success',
                'msg':'Service/Product Created'
            }
        else:
            return {
                'result':'Fail',
                'msg':'No Category found'
            }
    def delete_service(self,vals):
        clean_str_data(vals)
        id = decrypt(vals.get('login'))
        service_id = self.sudo().search([('id','=',vals.get('id'))])
        if service_id:
            self.env['anyservice.notification'].sudo().create({
                'name':service_id.name,
                'message':'Your Service/Product is deleted',
                'model_name':'anyservice.service',
                'record_name':service_id.id,
                'partner_id':id,
            })
            service_id.unlink()
            return {
                'result':'Success',
                'msg':'Service/Product Deleted'
            }
        else:
            return {
                'result':'Fail',
                'msg':'No Category found'
            }

    def load_image(self,vals):
        clean_str_data(vals)
        service_id = self.sudo().search([('id','=',vals.get('id'))])
        return {
            'result':'Success',
            'image':service_id.image,
        }

