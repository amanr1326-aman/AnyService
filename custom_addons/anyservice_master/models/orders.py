# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import random
import string


import pytz
import datetime

def convertdatetolocal(user_tz,date):
    if not isinstance(date,datetime.datetime):
        return date.strftime('%a, %d %b %y')
    local =  pytz.timezone(user_tz)
    display_date_result = datetime.datetime.strftime(pytz.utc.localize(date).astimezone(local),'%a, %d %b %y\n%I:%M %p')
    return display_date_result

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
    'draft':'Draft','pending':'Pending From Agent','accepted':'Accepted By Agent','progress':'In Progress','done':'Awaiting Payment','paid':'Paid','cancel':'Cancelled','Message From Agent':'Message From Agent','Message From Customer':'Message From Customer'
}

class AnyserviceOrder(models.Model):
    _name = 'anyservice.order'
    _description = 'Anyservice Orders'
    _order = 'id desc'

    name = fields.Char('Order No.', readonly=True,default='/')
    customer_id = fields.Many2one('res.partner',string='Belongs To',domain=[('state','=','approved'),('is_anyservice_user','=',True),('user_type','=','client')] ,required=True)
    agent_id = fields.Many2one('res.partner',string='Agent',domain=[('state','=','approved'),('is_anyservice_user','=',True),('user_type','=','agent')] ,required=True)
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
    rating = fields.Float('Rating')
    code = fields.Char('Code')
    updated = fields.Boolean(default=True)

    def print_invoice(self,vals=False):
        # if vals.get('id'):
        #     order = self.search([('id','=',vals.get('id'))])
        # http://localhost:8069/report/pdf/account.report_invoice/
        return self.env.ref('account.report_invoice').sudo().get_action(self.invoice_id) 

    def write(self,vals):
        if 'updated' not in vals:
            vals['updated'] = True
        return super(AnyserviceOrder,self).write(vals)


    def add_remark(self,msg,partner_id):
        self.env['anyservice.order.remarks'].create({
            'order_id':self.id,
            'action':self.state,
            'remark':msg,
            'partner_id':partner_id.id,
            'date':datetime.datetime.now()

        })
        notification = self.env['anyservice.notification'].create({
                'name':'Order '+self.name,
                'message':msg+'\n'+self.desc+' ('+STATES[self.state]+')',
                'model_name':'anyservice.order',
                'record_name':self.id,
                'partner_id':self.customer_id.id,
            })
        notification.send_notification(self.customer_id.fcm_token)
        if partner_id.id != self.service_ids[0].partner_id.id or self.state=='paid':
            notification = self.env['anyservice.notification'].create({
                    'name':'Order '+self.name,
                    'message':msg+'\n'+self.desc+' ('+STATES[self.state]+')',
                    'model_name':'anyservice.order',
                    'record_name':self.id,
                    'partner_id':self.service_ids[0].partner_id.id,
                })
            notification.send_notification(partner_id.fcm_token)

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
        invoice_journal_id = self.env['account.journal'].sudo().browse(int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.invoice_journal_id')) or 1)

        self.invoice_id = self.env['account.move'].sudo().create({
            'partner_id':self.customer_id.id,
            'ref':self.name,
            'type':'out_invoice',
            'journal_id':invoice_journal_id.id,
             'line_ids': [(6, 0, [])],
        })
        # invoice_line_ids = []
        for service in self.service_ids:
            if service.name == 'Price Change(by Agent)' and service.total_price<0:
                line_id = self.env['account.move.line'].sudo().create([{
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
                    'credit':-1*service.total_price,
                    'move_id':self.invoice_id.id,
                    'exclude_from_invoice_tab':True,
                    'account_id':self.customer_id.property_account_receivable_id.id,
                }])
            else:
                line_id = self.env['account.move.line'].sudo().create([{
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
            line_id = self.env['account.move.line'].sudo().create([{
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

        self.invoice_id.sudo().action_post()
        self.state='done'
        self.add_remark(msg,self.service_ids[0].partner_id)

    def cancel(self,msg="From Admin"):
        self.state='cancel'
        self.add_remark(msg,self.customer_id)

    def pay(self,msg="From Admin"):
        if self.invoice_id.sudo().amount_residual>0:
            payment_id=self.env['account.payment'].sudo().create({
                'journal_id':int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.journal_id')) or 1,
                'amount':self.invoice_id.amount_total,
                'payment_date':self.invoice_id.invoice_date,
                'partner_id':self.customer_id.id,
                'communication':self.invoice_id.name,
                'partner_type':'customer',
                'payment_type':'inbound',
                'invoice_ids':[self.invoice_id.id],
                'payment_method_id':self.env['account.payment.method'].sudo().search([('name','=','Manual')])[0].id,
            })
            payment_id.sudo().post()
            self.env['anyservice.transaction'].sudo().create({
                    'partner_id':self.agent_id.id,
                    'credit':self.total_price,
                    'debit':self.total_price,
                    'total':self.agent_id.sudo().balance,
                    'name':'Payment got by cash for '+self.name
                })
            self.agent_id.sudo().balance -= self.total_price*0.02
            self.env['anyservice.transaction'].sudo().create({
                    'partner_id':self.agent_id.id,
                    'credit':0,
                    'debit':self.total_price*0.02,
                    'total':self.agent_id.sudo().balance,
                    'name':'2% Anyservice Charge for the Order '+self.name
                })
            deduct_price = 0
            for service in self.service_ids:
                if service.name == 'Pending Bill' and service.total_price>0:
                    deduct_price = service.total_price
                    self.agent_id.sudo().balance -= deduct_price
                    self.env['anyservice.transaction'].sudo().create({
                        'partner_id':self.agent_id.id,
                        'credit':0,
                        'debit':deduct_price,
                        'total':self.agent_id.sudo().balance,
                        'name':'Pending bill charges from user for '+self.name
                        })
            self.env['anyservice.transaction'].sudo().create({
                    'partner_id':self.customer_id.id,
                    'credit':self.total_price,
                    'debit':self.total_price,
                    'total':self.customer_id.sudo().balance,
                    'name':'Order Paid fully '+self.name
                })
            self.state='paid'
            self.add_remark(msg,self.service_ids[0].partner_id)
        else:
            self.state='paid'
            self.add_remark(msg,self.service_ids[0].partner_id)
            return {
                'result':'Fail',
                'msg':'Already Paid'
            }

    @api.depends('service_ids','other_charge')
    def _compute_price(self):
        for rec in self:
            price = 0
            for service in rec.service_ids:
                price += service.total_price
            price += rec.other_charge
            rec.total_price = price


    def update_order(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])
            order = self.search([('id','=',vals.get('id'))])
            if vals.get('price'):
                service_id = self.env['anyservice.order.child'].sudo().create({'name':'Price Change(by Agent)','price':vals.get('price')-order.total_price})
                service_id.onchangeservice()
                service_id._compute_price()
                order.service_ids = [(4,service_id.id)]
                order.add_remark("Order Price updated by Agent"+'\n'+vals.get('msg'),user)
                return {
                    'result':'Success',
                    'msg':'Price Updated'
                }
            if vals.get('rating'):
                order.rating = vals.get('rating')
                for service_obj in order.service_ids:
                    if service_obj.service_id:
                        rating = service_obj.service_id.rating
                        if rating:
                            rating += vals.get('rating')
                            rating = rating/2
                        else:
                            rating = vals.get('rating')
                        service_obj.service_id.rating += rating
                order.add_remark("Rated Successfully with rating "+str(vals.get('rating'))+'\n'+vals.get('msg'),user)
                return{
                    'result':'Success',
                    'msg':"Rated Successfully with rating "+str(vals.get('rating')),
                }
            if vals.get('cancel'):
                order.state = 'cancel'
                if user.user_type == 'agent':
                    order.add_remark("Order Cancelled by Agent"+'\n'+vals.get('msg'),user)
                    return{
                        'result':'Success',
                        'msg':"Order Cancelled",
                    }

                else:
                    order.add_remark("Order Cancelled by customer with Charge Rs. "+str(vals.get('charge',0))+'\n'+vals.get('msg'),user)
                    user.sudo().balance = user.balance - vals.get('charge',0)                    
                    self.env['anyservice.transaction'].sudo().create({
                            'partner_id':order.customer_id.id,
                            'credit':0,
                            'debit':vals.get('charge',0) ,
                            'total':user.sudo().balance,
                            'name':'Cancellation charge for the order'+order.name
                        })
                    return{
                        'result':'Success',
                        'msg':"Order Cancelled by customer with Charge Rs. "+str(vals.get('charge',0)),
                    }
            if vals.get('accept'):
                order.accept(vals.get('msg'))
                return{
                'result':'Success',
                'msg':"Order Accepted",
                }               
            if vals.get('progress'):
                if order.code == vals.get('code'):
                    order.progress(vals.get('msg'))
                    return{
                    'result':'Success',
                    'msg':"Service started",
                    }
                else:
                    return{
                    'result':'Fail',
                    'msg':"Wrong Code Entered",
                    }  
            if vals.get('done'):
                order.done(vals.get('msg'))
                return{
                'result':'Success',
                'msg':"Order completed",
                }  
            if vals.get('paid'):
                order.pay(vals.get('msg'))
                return{
                'result':'Success',
                'msg':"Order Paid",
                }  
            if vals.get('clientpaid'):
                payment_id = self.env['account.payment'].sudo().search([('communication','ilike',order.invoice_id.sudo().name),('state','=','posted'),('amount','=',order.total_price)])
                if payment_id:
                    order.state = 'paid'
                    payment_id.sudo().invoice_ids = [(6,0,[order.invoice_id.sudo().id])]
                    moves = self.env['account.move'].sudo().search([('name','=',payment_id[0].sudo().move_name),('state','=','posted'),('type','=','entry')])
                    if moves:
                        (moves[0] + order.invoice_id).sudo().line_ids \
                            .filtered(lambda line: not line.sudo().reconciled and line.sudo().account_id == payment_id.sudo().destination_account_id)\
                            .sudo().reconcile()
                        self.env['anyservice.transaction'].sudo().create({
                                'partner_id':order.customer_id.id,
                                'credit':payment_id[0].sudo().amount,
                                'debit':payment_id[0].sudo().amount,
                                'total':order.customer_id.sudo().balance,
                                'name':'Order Paid fully '+order.name+' by online payment '+payment_id.sudo().name
                            })
                        order.agent_id.sudo().balance += payment_id[0].sudo().amount - (payment_id[0].sudo().amount*0.02)
                        self.env['anyservice.transaction'].sudo().create({
                                'partner_id':order.agent_id.id,
                                'credit':payment_id[0].sudo().amount,
                                'debit':(payment_id[0].sudo().amount*0.02),
                                'total':order.agent_id.sudo().balance,
                                'name':'Payment added to your wallet after deducting anyservice charge. Order Paid fully '+order.name+' by customer using online payment '+payment_id.sudo().name
                            })
                        deduct_price = 0
                        for service in order.service_ids:
                            if service.name == 'Pending Bill' and service.total_price>0:
                                deduct_price = service.total_price
                                order.agent_id.sudo().balance -= deduct_price
                                self.env['anyservice.transaction'].sudo().create({
                                    'partner_id':order.agent_id.id,
                                    'credit':0,
                                    'debit':deduct_price,
                                    'total':order.agent_id.sudo().balance,
                                    'name':'Pending bill charges from user for '+order.name
                                    })
                        notification = self.env['anyservice.notification'].create({
                                'name':'Order '+order.name,
                                'message':'Online Payment recieved Successfully.\nPlease use the following reference for your payment in future -'+payment_id[0].sudo().name,
                                'model_name':'anyservice.order',
                                'record_name':order.id,
                                'partner_id':order.customer_id.id,
                            })
                        notification.send_notification(user.fcm_token)
                        notification= self.env['anyservice.notification'].create({
                                'name':'Order '+order.name,
                                'message':'Online Payment recieved Successfully from customer.\nMoney is added to your wallet and same will be added to your account within 5 working days.\nPlease use the following reference for your payment in future -'+payment_id[0].sudo().name,
                                'model_name':'anyservice.order',
                                'record_name':order.id,
                                'partner_id':order.agent_id.id,
                            })
                        notification.send_notification(user.fcm_token)
                        order.add_remark("Online Payment Received with payment no. "+payment_id[0].sudo().name,order.customer_id)
                        return {
                            'result':'Success',
                            'msg':'Order Successfully paid through online mode.'
                        }
                    else:
                        return {
                            'result':'Fail',
                            'msg':'No Move found.'
                        }

                else:
                    return {
                        'result':'Fail',
                        'msg':'No Payment found.'
                    }


    def xmlrpc_create_order(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            agent_id = False
            remark = ''
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])   
            service_ids = []
            for val in list(vals.get('services')):
                service = self.env['anyservice.service'].sudo().search([('id','=',int(val.get('id')))])
                service_id = self.env['anyservice.order.child'].sudo().create({'name':val.get('variant') if val.get('variant') else service[0].sudo().name,'service_id':int(val.get('id')),'quantity':int(val.get('quantity')),'price':service[0].sudo().price})
                # service_id.onchangeservice()
                service_id._compute_price()
                service_ids.append(service_id.id)
                agent_id = service_id.partner_id.id
                remark = remark+service_id.sudo().name+', '
            if vals.get('visiting_charge'):
                service_id = self.env['anyservice.order.child'].sudo().create({'name':'Visiting Charge','price':vals.get('visiting_charge')})
                service_id.onchangeservice()
                service_id._compute_price()
                service_ids.append(service_id.id)
            if vals.get('pending'):
                service_id = self.env['anyservice.order.child'].sudo().create({'name':'Pending Bill','price':vals.get('pending')})
                service_id.onchangeservice()
                service_id._compute_price()
                service_ids.append(service_id.id)
                self.env['anyservice.transaction'].sudo().create({
                        'partner_id':user.id,
                        'credit':vals.get('pending'),
                        'debit':0,
                        'total':user.sudo().balance,
                        'name':'Pending Payment added to next bill.'
                    })
                user.sudo().balance = user.balance + vals.get('pending')
            vals = {
                'customer_id' : user.id,
                'agent_id' : agent_id,
                'service_ids' :service_ids,
                'date' :datetime.datetime.now(),
                'desc':remark+'\n'+vals.get('remark'),
                'full_address':vals.get('full_address'),
                'gps_address':vals.get('gps_address'),


            }
            order = self.sudo().create(vals)
            order.submit('Submitted by '+user.name)
            letters = "1234567890"
            code = ''.join(random.choice(letters) for i in range(6))
            order.code = code
            notification = self.env['anyservice.notification'].create({
                    'name':'Order '+order.name,
                    'message':'CODE - '+code+'\nPlease share this code with Agent only when agent will visit your home to start service.',
                    'model_name':'anyservice.order',
                    'record_name':order.id,
                    'partner_id':order.customer_id.id,
                })
            notification.send_notification(user.fcm_token)
            return {
                'result':'Success',
                'order_id':order.name,
            }

    def notify_onchange_order(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            orders = []
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)],order="id desc")   
            domain = [('customer_id' if user.user_type=='client' else 'agent_id','=',user.id),('updated','=',True)]
            if vals.get('id'):
                domain.append(('id','=',vals.get('id')))
            order_ids = self.search(domain,limit=20)
            for order_id in order_ids:
                if order_id.remarks:
                    last_action_partner = order_id.remarks[len(order_id.remarks)-1].partner_id
                    if int(vals.get('login')) != last_action_partner.id:
                        order_id.updated = False
                        if order_id.service_ids and order_id.date:
                            if order_id.agent_id:
                                orders.append({
                                    'id':order_id.id,
                                    'name':order_id.name,
                                    'order_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
                                    'final_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.remarks[len(order_id.remarks)-1].date) if order_id.remarks else convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
                                    'cust_id':order_id.customer_id.id,
                                    'agent_id':order_id.agent_id.id,
                                    'cust_name':order_id.customer_id.name,
                                    'agent_name':order_id.agent_id.parent_id.name,
                                    'description':order_id.desc or '',
                                    'gps_address':order_id.gps_address or '',
                                    'full_address':order_id.full_address or '',
                                    'state':STATES[order_id.state],
                                    'total_price':order_id.total_price,
                                    'image':order_id.service_ids[0].service_id.image_128 or order_id.agent_id.parent_id.image_128,
                                    'cust_phone':order_id.customer_id.phone,
                                    'agent_phone':order_id.agent_id.phone,
                                    'rating':order_id.rating,
                                    'invoice_id':order_id.invoice_id.id or 0,
                                    'code':order_id.code,
                                    })
            return {
                'result':'Success' if len(orders)>0 else 'Fail',
                'orders':orders,
            }
   
    def get_user_done_orders(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            orders = []
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)],order="id desc")   
            order_ids = self.search([('customer_id' if user.user_type=='client' else 'agent_id','=',user.id),('state','in',['paid','cancel'])],order="id desc",offset=vals.get('offset',0),limit=vals.get('limit',50))
            for order_id in order_ids:
                if order_id.service_ids and order_id.date:
                    if order_id.agent_id:
                        orders.append({
                            'id':order_id.id,
                            'name':order_id.name,
                            'order_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
                            'final_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.remarks[len(order_id.remarks)-1].date) if order_id.remarks else convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
                            'cust_id':order_id.customer_id.id,
                            'agent_id':order_id.agent_id.id,
                            'cust_name':order_id.customer_id.name,
                            'agent_name':order_id.agent_id.parent_id.name,
                            'description':order_id.desc or '',
                            'gps_address':order_id.gps_address or '',
                            'full_address':order_id.full_address or '',
                            'state':STATES[order_id.state],
                            'total_price':order_id.total_price,
                            'image':order_id.service_ids[0].service_id.image_128 or order_id.agent_id.parent_id.image_128,
                            'cust_phone':order_id.customer_id.phone,
                            'agent_phone':order_id.agent_id.phone,
                            'rating':order_id.rating,
                            'invoice_id':order_id.invoice_id.id or 0,
                            'code':order_id.code,
                            })
            return {
                'result':'Success',
                'orders':orders,
            }

    def get_order_services(self,vals):
        clean_str_data(vals)
        services = []
        if vals.get('id'):
            order = self.search([('id','=',vals.get('id'))])
            for service in order.service_ids:
                services.append({
                    'name':service.name,
                    'price':service.price,
                    'quantity':service.quantity or 1,
                    })
            services.append({
                'name':'Total',
                'price':order.total_price,
                'quantity':1,
                })
            return {
                'result':'Success',
                'services':services,
            }

    def get_user_orders(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            orders = []
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])
            order_ids = self.search([('customer_id' if user.user_type=='client' else 'agent_id','=',user.id),('state','not in',['paid','cancel'])],order="id desc",offset=vals.get('offset',0),limit=vals.get('limit',50))
            for order_id in order_ids:
                if order_id.service_ids and order_id.date:
                    if order_id.agent_id:
                        orders.append({
                            'id':order_id.id,
                            'name':order_id.name,
                            'order_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
                            'final_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.remarks[len(order_id.remarks)-1].date) if order_id.remarks else convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
                            'cust_id':order_id.customer_id.id,
                            'agent_id':order_id.agent_id.id,
                            'cust_name':order_id.customer_id.name,
                            'agent_name':order_id.agent_id.parent_id.name,
                            'description':order_id.desc or '',
                            'gps_address':order_id.gps_address or '',
                            'full_address':order_id.full_address or '',
                            'state':STATES[order_id.state],
                            'total_price':order_id.total_price,
                            'image':order_id.service_ids[0].service_id.image_128 or order_id.agent_id.parent_id.image_128,
                            'cust_phone':order_id.customer_id.phone,
                            'agent_phone':order_id.agent_id.phone,
                            'rating':order_id.rating,
                            'invoice_id':order_id.invoice_id.id or 0,
                            'code':order_id.code,
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
            'date': convertdatetolocal(self.env.user.tz or pytz.utc,order_id.create_date),
            'msg': 'Order Placed',
            'active':order_id.state=='draft',
            })
        for action_id in order_id.remarks:

            states.append({
                'name':STATES[action_id.action.replace('Set to ','')],
                'date': convertdatetolocal(self.env.user.tz or pytz.utc,action_id.date),
                'msg': action_id.remark,
                'active': False
                })
        if states:
            states[len(states)-1]['active'] = True

        entry_start = False
        for key in STATES:
            if key == 'Message From Agent':
                break
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
            'verified':order_id.agent_id.verified,
            'states':states,
        }

    def create_notification(self,vals):
        clean_str_data(vals)
        user = self.env['res.partner'].search([('id','=',id),('is_anyservice_user','=',True)])
        notification = self.env['anyservice.notification'].sudo().create({
                'name':vals.get('name'),
                'message':vals.get('msg'),
                'partner_id':vals.get('id'),
            })
        notification.send_notification(user.fcm_token)
        return {
            'result':'Success',
            'msg':'User Notified'
        }

    def get_payment_link(self,vals):
        clean_str_data(vals)
        order_id = self.search([('id','=',int(vals.get('id')))])
        if order_id.invoice_id.sudo().amount_residual>0:
            invoice_sudo = order_id.invoice_id.sudo()
            payment_link  = self.env['payment.link.wizard'].sudo().create({
                    'res_id':invoice_sudo.id,
                    'res_model':'account.move',
                    'currency_id':invoice_sudo.currency_id.id,
                    'description': invoice_sudo.invoice_payment_ref,
                    'amount': invoice_sudo.amount_residual,
                    'partner_id': invoice_sudo.partner_id.id,
                    'amount_max': invoice_sudo.amount_residual,

                })
            payment_link.sudo()._onchange_amount()
            payment_link.sudo()._compute_values()
            payment_link.sudo().check_token(payment_link.access_token,payment_link.partner_id,payment_link.amount,payment_link.currency_id)
            return {
                'result':'Success',
                'link':payment_link.link.replace('8069','8079'),
            }
        else:
            return{
                'result':'Fail',
                'msg':'Already Paid'
            }
    def xmlrpcadd_remark(self,vals):
        tag = ''
        clean_str_data(vals)
        user_id = int(decrypt(vals.get('login')))
        user = self.env['res.partner'].search([('id','=',user_id),('is_anyservice_user','=',True)])
        order_id = self.search([('id','=',int(vals.get('id')))])
        if user_id == order_id.customer_id.id:
            tag = 'Message From Customer'
        else:
            tag = 'Message From Agent'

        self.env['anyservice.order.remarks'].create({
            'order_id':order_id.id,
            'action':tag,
            'remark':vals.get('msg'),
            'partner_id':user_id,
            'date':datetime.datetime.now()

        })
        notification = self.env['anyservice.notification'].sudo().create({
                'name':tag+' for order '+order_id.name,
                'message':vals.get('msg'),
                'partner_id': order_id.agent_id.id if user_id==order_id.customer_id.id else order_id.customer_id.id,
            })
        notification.send_notification(order_id.agent_id.fcm_token if user_id==order_id.customer_id.id else order_id.customer_id.fcm_token)
        return {
            'result':'Success',
            'msg':'Sent',
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
