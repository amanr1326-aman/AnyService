# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

def decrypt(data):
    return data

def encrypt(data):
    return data

def clean_str_data(data):
    if type(data)==dict:
        for key in data:
            if type(data[key])==str:
                data[key] = data[key].strip()
STATES = {
    'draft':'Draft','pending':'Pending From Agent','accepted':'Accepted By Agent','progress':'In Progress','done':'Awaiting Payment','paid':'Paid','cancel':'Cancelled',
}

class AnyserviceOrder(models.Model):
    _name = 'anyservice.order'
    _description = 'Anyservice Orders'
    _order = 'id desc'

    name = fields.Char('Order No.', readonly=True,default='/')
    customer_id = fields.Many2one('res.partner',string='Belongs To',domain=[('state','=','approved'),('is_anyservice_user','=',True),('user_type','=','client')] ,required=True)
    service_ids = fields.Many2many('anyservice.order.child',string='Services',required=True)
    invoice_id = fields.Many2one('account.move',string='Invoice')
    state = fields.Selection([('draft','Draft'),('pending','Pending From Agent'),('accepted','Accepted By Agent'),('progress','In Progress'),('done','Awaiting Payment'),('cancel','Cancelled'),('paid','Paid')], default='draft')
    other_charge = fields.Float()
    total_price = fields.Float(compute="_compute_price",store=True)
    date = fields.Date()
    remarks = fields.One2many('anyservice.order.remarks','order_id')
    desc = fields.Text('Remark')
    gps_address = fields.Text('GPS Address')
    full_address = fields.Text('Full Address')


    def add_remark(self,msg,partner_id):
        self.env['anyservice.order.remarks'].create({
            'order_id':self.id,
            'action':self.state,
            'remark':msg,
            'partner_id':partner_id.id,
            'date':datetime.now()

        })

    def open_invoice(self):
        return {
        'type': 'ir.actions.act_window',
        'res_model': 'account.move',
        'name':'Invoice',
        'view_type': 'tree',
        'view_mode': 'tree,form',
        'domain':[('id','=',self.invoice_id.id)]
    }

    def set_draft(self,msg="From Admin"):
        self.state='draft'
        self.add_remark(msg,self.customer_id)

    def submit(self,msg="From Admin"):
        self.state='pending'
        self.name = self.env['ir.sequence'].sudo().next_by_code('anyservice.order')
        self.add_remark(msg,self.customer_id)

    def accept(self,msg="From Admin"):
        self.state='accepted'
        self.add_remark(msg,self.service_ids[0].partner_id)

    def progress(self,msg="From Admin"):
        self.state='progress'
        self.add_remark(msg,self.service_ids[0].partner_id)

    def done(self,msg="From Admin"):
        self.state='done'
        self.add_remark(msg,self.service_ids[0].partner_id)

    def cancel(self,msg="From Admin"):
        self.state='cancel'
        self.add_remark(msg,self.customer_id)

    def pay(self,msg="From Admin"):
        invoice_journal_id = self.env['account.journal'].browse(int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.invoice_journal_id')) or 1)

        self.invoice_id = self.env['account.move'].create({
            'partner_id':self.customer_id.id,
            'ref':self.name,
            'type':'out_invoice',
            'journal_id':invoice_journal_id.id,
             'line_ids': [(6, 0, [])],
        })
        # invoice_line_ids = []
        for service in self.service_ids:
            line_id = self.env['account.move.line'].create([{
                'product_id':int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.product_id')) or 1,
                'name': service.name,
                'quantity':service.quantity,
                'tax_ids':False,
                'price_unit':service.price,
                'price_subtotal':service.total_price,
                'move_id':self.invoice_id.id,
                'account_id':invoice_journal_id.default_debit_account_id.id
            },{
                'quantity':service.quantity,
                'tax_ids':False,
                'debit':service.total_price,
                'move_id':self.invoice_id.id,
                'exclude_from_invoice_tab':True,
                'account_id':self.customer_id.property_account_receivable_id.id,
            }])
            # invoice_line_ids.append(line_id.id)
        if self.other_charge:
            line_id = self.env['account.move.line'].create([{
                'product_id':int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.product_id')) or 1,
                'name': 'Others',
                'quantity':1,
                'price_unit':self.other_charge,
                'tax_ids':False,
                'price_subtotal':self.other_charge,
                'move_id':self.invoice_id.id,
                'account_id':invoice_journal_id.default_debit_account_id.id
            },{
                'tax_ids':False,
                'debit':self.other_charge,
                'move_id':self.invoice_id.id,
                'exclude_from_invoice_tab':True,
                'account_id':self.customer_id.property_account_receivable_id.id,
            }])
            # invoice_line_ids.append(line_id.id)

        self.invoice_id.action_post()
        payment_id=self.env['account.payment'].create({
            'journal_id':int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.journal_id')) or 1,
            'amount':self.invoice_id.amount_total,
            'payment_date':self.invoice_id.invoice_date,
            'partner_id':self.customer_id.id,
            'communication':self.invoice_id.name,
            'partner_type':'customer',
            'payment_type':'inbound',
            'invoice_ids':[self.invoice_id.id],
            'payment_method_id':self.env['account.payment.method'].search([('name','=','Manual')])[0].id,
        })
        payment_id.post()
        self.state='paid'
        self.add_remark(msg,self.customer_id)

    @api.depends('service_ids')
    def _compute_price(self):
        for rec in self:
            price = 0
            for service in rec.service_ids:
                price += service.price
            price += rec.other_charge
            rec.total_price = price


    def xmlrpc_create_order(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])   
            service_ids = []
            for val in list(vals.get('services')):
                service_id = self.env['anyservice.order.child'].sudo().create({'service_id':val.get('id'),'quantity':val.get('quantity')})
                service_id.onchangeservice()
                service_id._compute_price()
                service_ids.append(service_id.id)
            if vals.get('visiting_charge'):
                service_id = self.env['anyservice.order.child'].sudo().create({'name':'Visiting Charge','price':vals.get('visiting_charge')})
                service_id.onchangeservice()
                service_id._compute_price()
                service_ids.append(service_id.id)
            vals = {
                'customer_id' : user.id,
                'service_ids' :service_ids,
                'date' :datetime.now(),
                'desc':vals.get('remark'),
                'full_address':vals.get('full_address'),
                'gps_address':vals.get('gps_address'),


            }
            order = self.sudo().create(vals)
            order.submit('Submitted by '+user.name)
            return {
                'result':'Success',
                'order_id':order.name,
            }
   
    def get_user_done_orders(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            orders = []
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)],order="id desc")   
            order_ids = self.search([('customer_id','=',user.id),('state','in',['paid','cancel'])])
            for order_id in order_ids:
                if order_id.service_ids and order_id.date:
                    if order_id.service_ids[0].partner_id:
                        orders.append({
                            'id':order_id.id,
                            'name':order_id.name,
                            'order_date':order_id.date,
                            'final_date':order_id.remarks[len(order_id.remarks)-1].date if order_id.remarks else order_id.date,
                            'cust_id':order_id.customer_id.id,
                            'agent_id':order_id.service_ids[0].partner_id.id,
                            'cust_name':order_id.customer_id.name,
                            'agent_name':order_id.service_ids[0].partner_id.parent_id.name,
                            'description':order_id.desc or '',
                            'gps_address':order_id.gps_address or '',
                            'full_address':order_id.full_address or '',
                            'state':STATES[order_id.state],
                            'total_price':order_id.total_price,
                            'image':order_id.service_ids[0].partner_id.parent_id.image_1920,
                            'cust_phone':order_id.customer_id.phone,
                            'agent_phone':order_id.service_ids[0].partner_id.phone,
                            })
            return {
                'result':'Success',
                'orders':orders,
            }

    def get_user_orders(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            orders = []
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])   
            order_ids = self.search([('customer_id','=',user.id),('state','not in',['paid','cancel'])],order="id desc")
            for order_id in order_ids:
                if order_id.service_ids and order_id.date:
                    if order_id.service_ids[0].partner_id:
                        orders.append({
                            'id':order_id.id,
                            'name':order_id.name,
                            'order_date':order_id.date,
                            'final_date':order_id.remarks[len(order_id.remarks)-1].date if order_id.remarks else order_id.date,
                            'cust_id':order_id.customer_id.id,
                            'agent_id':order_id.service_ids[0].partner_id.id,
                            'cust_name':order_id.customer_id.parent_id.name,
                            'agent_name':order_id.service_ids[0].partner_id.parent_id.name,
                            'description':order_id.desc or '',
                            'gps_address':order_id.gps_address or '',
                            'full_address':order_id.full_address or '',
                            'state':STATES[order_id.state],
                            'total_price':order_id.total_price,
                            'image':order_id.service_ids[0].partner_id.parent_id.image_1920,
                            'cust_phone':order_id.customer_id.phone,
                            'agent_phone':order_id.service_ids[0].partner_id.phone,
                            })
            return {
                'result':'Success',
                'orders':orders,
            }

    def get_order_status(self,vals):
        clean_str_data(vals)
        order_id = self.search([('id','=',int(vals.get('id')))])
        states = []
        states.append({
            'name':'Submitted',
            'date': order_id.create_date.strftime('%a, %d %b %y\n%I:%M %p'),
            'msg': 'Order Placed',
            'active':order_id.state=='draft',
            })
        for action_id in order_id.remarks:
            states.append({
                'name':STATES[action_id.action.replace('Set to ','')],
                'date': action_id.date.strftime('%a, %d %b %y\n%I:%M %p'),
                'msg': action_id.remark,
                'active': action_id.action.replace('Set to ','')==order_id.state
                })

        entry_start = False
        for key in STATES:
            if entry_start:
                states.append({
                    'name': STATES[key],
                    'date': '',
                    'msg': '',
                    'active':False,
                    })
            if key == order_id.state:
                entry_start = True
        return {
            'result':'Success',
            'states':states,
        }



class AnyserviceOrderRemarks(models.Model):
    _name = 'anyservice.order.remarks'
    _description = "AnyserviceOrder Remarks"

    order_id = fields.Many2one('anyservice.order', required=True)
    date = fields.Datetime()
    action = fields.Char()
    remark = fields.Char()
    partner_id = fields.Many2one('res.partner','Action By')

class AnyserviceServiceChilds(models.Model):
    _name = 'anyservice.order.child'

    @api.depends('service_id','quantity')
    def _compute_price(self):
        for rec in self:
            price = rec.price * rec.quantity
            rec.total_price = price
    @api.onchange('service_id')
    def onchangeservice(self):
        for rec in self:
            if rec.service_id:
                rec.price = rec.service_id.price
                rec.name = rec.service_id.name

    name = fields.Char(required=True)
    service_id = fields.Many2one('anyservice.service',string='Services')
    quantity = fields.Integer('Quantity',default=1)
    price = fields.Float('Unit Price')
    total_price = fields.Float('Total Price',compute=_compute_price)
    partner_id = fields.Many2one('res.partner',string='Belongs To',related='service_id.partner_id')
