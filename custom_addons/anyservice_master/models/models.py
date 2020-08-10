# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from geopy import distance

import pytz
import datetime

def convertdatetolocal(user_tz,date):
    if not isinstance(date,datetime.datetime):
        return date.strftime('%a, %d %b %y')
    local =  pytz.timezone(user_tz)
    display_date_result = datetime.datetime.strftime(pytz.utc.localize(date).astimezone(local),'%a, %d %b %y\n%I:%M %p')
    return display_date_result

def check_distance(lat1,long1,lat2,long2,radius):
    dis = distance.distance((lat1,long1),(lat2,long2)).km
    if dis<=radius:
        return True
    else:
        return False


def decrypt(data):
    return data

def encrypt(data):
    return data

def clean_str_data(data):
    if type(data)==dict:
        for key in data:
            if type(data[key])==str:
                data[key] = data[key].strip()






class ResPartner(models.Model):
    _inherit = 'res.partner'


    is_anyservice_user = fields.Boolean('Anyservice User')
    active_mode = fields.Boolean('Active Mode')
    user_type = fields.Selection([('agent','Agent'),('client','Client')])
    state = fields.Selection([('draft','Draft'),('pending','Pending For KYC'),('approved','Approved'),('banned','Banned')], default='draft',string="User State")
    # user_role = fields.Many2one('res.users', string="User Role")
    aadhar_number = fields.Char()
    aadhar_front = fields.Binary(string="Aadhar Front Image")
    aadhar_back = fields.Binary(string="Aadhar Back Image")

    place = fields.Char('Place')
    lat = fields.Char('Latitude')
    long = fields.Char('Longitude')
    rating = fields.Float('Rating',default=0)

    radius = fields.Integer('Service Distance', default=5)
    unlimted_distance = fields.Boolean('Unlimited Distance')
    verified = fields.Boolean('Verified User')
    unlimted_distance_charge = fields.Float('Delivery Distance')
    balance = fields.Float('Balance')
    transaction_ids = fields.One2many('anyservice.transaction','partner_id',string='Transaction')

    def set_draft(self):
        self.state='draft'

    def submit(self):
        self.state='pending'

    def approve(self):
        self.state='approved'

    def ban_user(self):
        self.state='banned'

    def check_app_details(self,vals):
        clean_str_data(vals)
        app_version = self.env['ir.config_parameter'].sudo().get_param('anyservice_master.version') or '1.0'
        if int(float(vals.get('app_version',0)))!=int(float(app_version)):
            return {
                'result':'Fail',
                'code':100,
                'msg':'Please Update the app to version '+app_version
            }
        if vals.get('login'):
            id = decrypt(vals.get('login'))
            user = self.search([('id','=',id),('is_anyservice_user','=',True)])
            if user:
                if len(user)>1:
                    return {
                        'result':'Fail',
                        'code':200,
                        'msg':'Annonymous User. Please Re-Register your account'
                    }
                else:
                    if user.state == 'approved':
                        return {
                            'result':'Success',
                            'name':user.name
                        }
                    elif user.state == 'pending':
                        return {
                            'result':'Fail',
                            'code': 103,
                            'msg':'Your e-KYC is still Pending.'
                        }
                    else:
                        return {
                            'result':'Fail',
                            'code': 100,
                            'msg':'Your account is Banned. Please Re-Register your account'
                        }
            else:
                return {
                    'result':'Fail',
                    'code':102,
                    'msg':'User Details not found on the server. Please Re-Register your account'
                    }
        else:
            return {
                'result':'Fail',
                'code':101,
                'msg':'New User'
            }

    def update_user_details(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            user = self.search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])
            if user:
                if len(user)>1:
                    return {
                        'result':'Fail',
                        'code':200,
                        'msg':'Annonymous User'
                    }
                if user.state == 'pending':
                    return {
                        'result':'Fail',
                        'code': 103,
                        'msg':'Your e-KYC is still Pending',
                        'login': user.id,
                        'name':user.name,
                    }
                else:
                    values = vals
                    if vals.get('rating'):
                        rating = user.rating
                        if rating:
                            rating += vals.get('rating')
                            rating = rating/2
                            vals['rating'] = rating
                    if vals.get('image'):
                        user.parent_id.sudo().image_1920 = vals.get('image')
                    if vals.get('company'):
                        user.parent_id.sudo().name = vals.get('company')
                    if vals.get('street'):
                        user.parent_id.sudo().street = vals.get('street')
                    if vals.get('street2'):
                        user.parent_id.sudo().street2 = vals.get('street2')
                    if vals.get('zip'):
                        user.parent_id.sudo().zip = vals.get('zip')
                    if vals.get('vat'):
                        user.parent_id.sudo().vat = vals.get('vat')
                    values.pop('login')
                    values.pop('company',False)
                    values.pop('image',False)
                    values.pop('street',False)
                    values.pop('street2',False)
                    values.pop('zip',False)
                    values.pop('vat',False)
                    user.sudo().write(values)
                    return {
                        'result':'Success',
                    }
            else:
                return {
                    'result':'Fail',
                    'code':100,
                    }
        else:
            return {
                'result':'Fail',
                'code':100,
                }




    def get_user_details(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            user = self.search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])
            if user:
                if len(user)>1:
                    return {
                        'result':'Fail',
                        'code':200,
                        'msg':'Annonymous User'
                    }
                if user.state == 'pending':
                    return {
                        'result':'Fail',
                        'code': 103,
                        'msg':'Your e-KYC is still Pending',
                        'login': user.id,
                        'name':user.name,
                    }
                else:
                    return {
                        'result':'Success',
                        'name':user.name,
                        'email':user.email or '',
                        'radius':user.radius,
                        'place':user.place,
                        'street1':user.parent_id.street or '',
                        'street2':user.parent_id.street2 or '',
                        'city':user.parent_id.city or '',
                        'state':user.parent_id.state_id.name or '',
                        'aadhar':user.aadhar_number or '',
                        'gst':user.parent_id.vat or '',
                        'company':user.parent_id.name,
                        'image':user.parent_id.image_128 or '',
                        'agent':user.user_type=='agent',
                        'active':user.active_mode,
                        'pin':user.parent_id.zip,
                        'balance':user.balance,
                        'unlimted_distance':user.unlimted_distance,
                        'delivery_charge':user.unlimted_distance_charge,
                    }
            else:
                return {
                    'result':'Fail',
                    'code':100,
                    'msg':'No User Found'
                }
                
    def check_user(self,vals):
        clean_str_data(vals)
        if vals.get('phone'):
            user = self.search([('phone','=',vals.get('phone')),('state','!=','banned'),('is_anyservice_user','=',True)])
            if user:
                if len(user)>1:
                    return {
                        'result':'Fail',
                        'code':200,
                        'msg':'Annonymous User'
                    }
                if user.state == 'pending':
                    return {
                        'result':'Fail',
                        'code': 103,
                        'msg':'Your e-KYC is still Pending',
                        'login': user.id,
                        'name':user.name,
                    }
                else:
                    return {
                        'result':'Success',
                        'login': user.id,
                        'name':user.name,
                    }
            else:
                return {
                    'result':'Fail',
                    'code':100,
                    'msg':'No User Found'
                }

        else:
            return {
                'result':'Fail',
                'code':100,
                'msg':'No Phone No. Found in request'
            }

    def get_states(self,vals):
        country_id = self.env['res.country'].search([('name','=','India')])
        states = self.env['res.country.state'].search([('country_id','=',country_id.id)])
        return {
            'result':'Success',
            'states':[rec.name for rec in states]
        }

    def create_anyservice_partner(self,vals):
        clean_str_data(vals)
        company_data = {}
        data ={}
        if vals.get('name') and vals.get('phone') and vals.get('user_type','') in ['agent','client']:
            user = self.search([('phone','=',vals.get('phone')),('is_anyservice_user','=',True)])
            if user:
                return {
                    'result':'Fail',
                    'code': 102,
                    'msg':'You already have an Account.'
                }
            if vals.get('user_type')=='agent':
                data['state']='pending'
                if vals.get('aadhar_number'):
                    data['aadhar_number'] = vals.get('aadhar_number')
                    data['aadhar_front'] = vals.get('aadhar_front')
                    data['aadhar_back'] = vals.get('aadhar_back')
                company_data['type'] = 'contact'
                company_data['name'] = vals.get('company_name')
                company_data['street'] = vals.get('street1','')
                company_data['street2'] = vals.get('street2','')
                company_data['city'] = vals.get('city','')
                company_data['is_company'] = True
                company_data['zip'] = vals.get('pin')
                company_data['vat'] = vals.get('gst')
                company_data['image_1920'] = vals.get('logo')
                company_data['country_id'] = self.env['res.country'].search([('name','=','India')])[0].id
                company_data['state_id'] = self.env['res.country.state'].search([('name','=',vals.get('state'))])[0].id
                company_id = self.env['res.partner'].sudo().create(company_data)
                data['parent_id'] = company_id.id
                #self.env['ir.attachment'].sudo().create(
                #{'name':'image','res_field':'image','res_model':'res.partner','res_id':company_id,'datas':vals.get('logo')})
            else:
                data['state']='approved'
            data['name']=vals.get('name')
            data['phone']=vals.get('phone')
            data['user_type']=vals.get('user_type')

            if vals.get('email'):
                data['email'] = vals.get('email')
            data['is_anyservice_user'] = True
            user = self.env['res.partner'].sudo().create(data)
            return {
                'result':'Success',
                'login': encrypt(user.id),
            }

        else:
            return {
                'result':'Fail',
                'code':100,
                'msg':'Name or phone not found'
            }

    def update_location(self,vals):
        clean_str_data(vals)
        id = decrypt(vals.get('login'))
        user = self.sudo().search([('id','=',id),('is_anyservice_user','=',True)])
        user.place = vals.get('place')
        user.lat = vals.get('lat')
        user.long = vals.get('long')
        return {
            'result':'Success'
        }

    # def check_distance(self,lat,long,radius):
    #     dis = distance.distance((lat1,long1),(self.lat,self.long)).km
    #     if dis<=radius:
    #         return True
    #     else:
    #         return False

    def get_user_services(self,vals):
        clean_str_data(vals)
        agent_id = int(vals.get('agent_id'))
        id = int(decrypt(vals.get('login')))
        user = self.search([('id','=',id),('is_anyservice_user','=',True)])
        services = []
        domain=[]
        if vals.get('key'):
            domain.append('&')
            domain.append('|')
            domain.append(('name','ilike',vals.get('key')))
            domain.append(('details','ilike',vals.get('key')))
        domain.append(('partner_id','=',agent_id))
        service_records = self.env['anyservice.service'].sudo().search(domain,order="id desc",offset=vals.get('offset',0),limit=vals.get('limit',50))
        for rec in service_records:
            cost=0
            if rec.delivery_charge and not id==agent_id:
                if rec.partner_id.unlimted_distance:
                    cost = rec.partner_id.unlimted_distance_charge
                else:
                    cost = 10+4*(distance.distance((user.lat,user.long),(rec.partner_id.lat,rec.partner_id.long)).km)
            services.append({
                'id':rec.id,
                'name':rec.name,
                'company':rec.partner_id.parent_id.name,
                'verified':rec.partner_id.verified,
                'image':rec.image_512 or '',
                'rating':rec.rating,
                'agent_id':rec.partner_id.id,
                'category':rec.category_id.name,
                'price':rec.price,
                'is_measurable':rec.is_measurable,
                'charge':round(cost),
                'balance':abs(user.balance) if user.balance<0 else 0,
                'delivery_costable':rec.delivery_charge,
                'description':rec.details or ''
            })
        if services:
            if vals.get('offset'):
                return {
                    'result':'Success',
                    'services':services,
                  }

            else:
                return {
                    'result':'Success',
                    'verified':service_records[0].partner_id.verified,
                    'company':service_records[0].partner_id.parent_id.name,
                    'rating':service_records[0].partner_id.rating,
                    'categories':', '.join(set([rec.get('category') for rec in services])),
                    'address':(service_records[0].partner_id.street+' '+service_records[0].partner_id.parent_id.street2+'\n'+service_records[0].partner_id.parent_id.city+' '+service_records[0].partner_id.parent_id.state_id.name+' '+str(service_records[0].partner_id.parent_id.zip)).replace('\n\n','\n').replace('  ',' ').strip(),
                    'image':service_records[0].partner_id.parent_id.image_128,
                    'services':services,
                }
        else:
            return {
                'result':'Fail',
                'msg':'No Service Found',
            }


    def search_services(self,vals):
        clean_str_data(vals)
        id = decrypt(vals.get('login'))
        user = self.search([('id','=',id),('is_anyservice_user','=',True)])
        domain = ['&']
        services = []
        if vals.get('key'):
            domain.append('|')
            domain.append('|')
            domain.append(('name','ilike',vals.get('key')))
            domain.append(('details','ilike',vals.get('key')))
        categ = vals.get('categ')
        category_ids = False
        if categ:
            category_id = self.env['product.category'].search([('name','=',categ),('is_anyservice_category','=',True),('state','=','approved')])
            if vals.get('key'):
                category_ids = self.env['product.category'].search(['&','&','|','|',('name','=',categ),('id','child_of',category_id.ids),('name','ilike',vals.get('key')),('is_anyservice_category','=',True),('state','=','approved')])
            else:
                category_ids = self.env['product.category'].search(['&','&','|',('name','=',categ),('id','child_of',category_id.ids),('is_anyservice_category','=',True),('state','=','approved')])
        elif vals.get('key'):
            category_ids = self.env['product.category'].search([('name','ilike',vals.get('key')),('is_anyservice_category','=',True),('state','=','approved')])

        
        domain.append(('category_id','in',category_ids.ids))
        partner_ids = self.env['res.partner'].search([('active_mode','=',True),('is_anyservice_user','=',True),('state','=','approved'),('user_type','=','agent')])
        temp_partner_ids = partner_ids
        partner_ids = partner_ids.filtered(lambda x:check_distance(float(user.lat),float(user.long),float(x.lat),float(x.long),min(user.radius,x.radius)) or x.unlimted_distance ==True)
        domain.append(('partner_id','in',partner_ids.ids))
        service_records = self.env['anyservice.service'].sudo().search(domain,order=vals.get("order",False) or "id desc",offset=vals.get('offset',0),limit=vals.get('limit',50))
        for rec in service_records:
            cost=0
            if rec.delivery_charge:
                if rec.partner_id.unlimted_distance:
                    cost = rec.partner_id.unlimted_distance_charge
                else:
                    cost = 10+4*(distance.distance((user.lat,user.long),(rec.partner_id.lat,rec.partner_id.long)).km)
            services.append({
                'id':rec.id,
                'name':rec.name,
                'image':rec.image_512 or '',
                'agent_id':rec.partner_id.id,
                'verified':rec.partner_id.verified,
                'category':rec.category_id.name,
                'price':rec.price,
                'rating':rec.rating,
                'company':rec.partner_id.parent_id.name,
                'charge':round(cost),
                'is_measurable':rec.is_measurable,
                'balance':abs(user.balance) if user.balance<0 else 0,
                'description':rec.details or ''
            })
        partners = False
        if vals.get('key'):
        	partners = temp_partner_ids.filtered(lambda x:vals.get('key').lower() in x.parent_id.name.lower())
        if partners and (len(services)<=vals.get('limit',50) or len(services)==0):
            for rec in self.env['anyservice.service'].sudo().search([('partner_id','in',partners.ids),('id','not in',service_records.ids)],order=vals.get("order",False) or "id desc",offset=vals.get('offset',0),limit=vals.get('limit',50)-len(services) if vals.get('limit',50)-len(services)>0 else 1):
                cost=0
                if rec.delivery_charge:
                    if rec.partner_id.unlimted_distance:
                        cost = rec.partner_id.unlimted_distance_charge
                    else:
                        cost = 10+4*(distance.distance((user.lat,user.long),(rec.partner_id.lat,rec.partner_id.long)).km)
                services.append({
                    'id':rec.id,
                    'name':rec.name,
                    'image':rec.image_512 or '',
                    'agent_id':rec.partner_id.id,
                    'verified':rec.partner_id.verified,
                    'category':rec.category_id.name,
                    'price':rec.price,
                    'rating':rec.rating,
                    'company':rec.partner_id.parent_id.name,
                    'charge':round(cost),
                    'is_measurable':rec.is_measurable,
                    'balance':abs(user.balance) if user.balance<0 else 0,
                    'description':rec.details or ''
                })
        return {
            'result':'Success',
            'services':services
        }
#	21.143301,81.753253
        # user.place = vals.get('place')
        # user.lat = vals.get('lat')
        # user.long = vals.get('long')
        # return {
        #     'result':'Success'
        # }

    def get_instructions(self,vals):
        return {
            'result':'Success',
            'instruction':self.env['ir.config_parameter'].sudo().get_param('anyservice_master.instruction') or ''
        }


    def write(self,vals):
        if vals.get('phone'):
            vals['phone'] = vals['phone'].replace('+91','').replace(' ','')
        res=super(ResPartner,self).write(vals)
        return res


class AnyserviceConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'anyservice.config.settings'
    _description = 'Any Service Configuration'

    version = fields.Char(required=True, default="1.0")
    description = fields.Char()
    instruction = fields.Text()
    product_id = fields.Many2one('product.product','Any Service Product')
    journal_id = fields.Many2one('account.journal','Any Service Journal')
    invoice_journal_id = fields.Many2one('account.journal','Any Service Invoice Journal',domain=[('type','=','sale')])

    @api.model
    def get_values(self):
        res = super(AnyserviceConfiguration, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        version = params.get_param('anyservice_master.version', default=False)
        description = params.get_param('anyservice_master.description', default=False)
        instruction = params.get_param('anyservice_master.instruction', default=False)
        product_id = params.get_param('anyservice_master.product_id', default=False)
        journal_id = params.get_param('anyservice_master.journal_id', default=False)
        invoice_journal_id = params.get_param('anyservice_master.invoice_journal_id', default=False)
        res.update(version=version,description=description,instruction=instruction,product_id=int(product_id),journal_id=int(journal_id),invoice_journal_id=int(invoice_journal_id))
        return res


    def set_values(self):
        super(AnyserviceConfiguration, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.version", self.version)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.description", self.description)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.instruction", self.instruction)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.product_id", self.product_id and self.product_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.journal_id", self.journal_id and self.journal_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.invoice_journal_id", self.invoice_journal_id and self.invoice_journal_id.id or False)

class AnyserviceServiceChilds(models.Model):
    _name = 'anyservice.transaction'

    name = fields.Char(required=True)
    credit = fields.Float('Credit')
    debit = fields.Float('Debit')
    total = fields.Float('Total')
    partner_id = fields.Many2one('res.partner',string='Belongs To')

    def post_payment(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])
            amount =  vals.get('amount')
            invoices = self.env['account.move'].sudo().search([('state','=','draft'),('invoice_payment_ref','ilike','ANY/Bill/'+str(user.id)),('partner_id','=',user.id)])
            if invoices:
                invoices[0].sudo().action_post()
                payment_id = self.env['account.payment'].sudo().search([('communication','ilike',invoices[0].sudo().ref),('state','=','posted'),('partner_id','=',user.id),('invoice_ids','=',False),('amount','=',amount)],order="id desc")
                if payment_id:
                    user.sudo().balance += payment_id[0].sudo().amount
                    payment_id[0].sudo().invoice_ids = [(6,0,[invoices[0].sudo().id])]
                    moves = self.env['account.move'].sudo().search([('name','=',payment_id[0].sudo().move_name),('state','=','posted'),('type','=','entry')])
                    if moves:
                        (moves[0] + invoices[0]).sudo().line_ids \
                            .filtered(lambda line: not line.sudo().reconciled and line.sudo().account_id == payment_id.sudo().destination_account_id)\
                            .sudo().reconcile()
                    self.env['anyservice.transaction'].sudo().create({
                            'partner_id':user.id,
                            'credit':payment_id[0].sudo().amount,
                            'debit':0,
                            'total':user.sudo().balance,
                            'name':'Payment Successfull by online '+payment_id[0].sudo().name
                        })
                    self.env['anyservice.notification'].create({
                                'name':'Payment recieved',
                                'message':'Online Payment'+' of amount '+str(payment_id[0].sudo().amount)+' recieved Successfully.\nPlease use the following reference for your payment in future -'+payment_id[0].sudo().name,
                                'model_name':'anyservice.transaction',
                                'record_name':'',
                                'partner_id':user.id,
                            })
                    return {
                        'result':'Success',
                        'msg':'Payment posted Successfully.'
                    }
                else:
                    return {
                        'result':'Fail',
                        'msg':'No Payment found.'
                    }
            else:
                return {
                    'result':'Fail',
                    'msg':'No Bill found.'
                }


    def get_payment_link(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])
            amount =  vals.get('amount')
            invoices = self.env['account.move'].sudo().search([('state','=','draft'),('ref','ilike','ANY/Bill/'+str(user.id)),('partner_id','=',user.id)])
            for invoice in invoices:
                invoice.sudo().unlink()
            invoice_journal_id = self.env['account.journal'].sudo().browse(int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.invoice_journal_id')) or 1)

            invoice_id = self.env['account.move'].sudo().create({
                'partner_id':user.id,
                'ref':'ANY/Bill/'+str(user.id),
                'invoice_payment_ref':'ANY/Bill/'+str(user.id),
                'type':'out_invoice',
                'journal_id':invoice_journal_id.id,
                 'line_ids': [(6, 0, [])],
            })
            line_id = self.env['account.move.line'].sudo().create([{
                'product_id':int(self.env['ir.config_parameter'].sudo().get_param('anyservice_master.product_id')) or 1,
                'name': 'Anyservice Bill Payment',
                'quantity':1,
                'tax_ids':False,
                'price_unit':amount,
                'price_subtotal':amount,
                'move_id':invoice_id.id,
                'account_id':invoice_journal_id.default_debit_account_id.id
            },{
                'quantity':1,
                'tax_ids':False,
                'debit':amount,
                'move_id':invoice_id.id,
                'exclude_from_invoice_tab':True,
                'account_id':user.property_account_receivable_id.id,
            }])
            invoice_sudo = invoice_id.sudo()
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
            # print(payment_link.link)
            return {
                'result':'Success',
                'link':payment_link.link,
            }
        else:
            return{
                'result':'Fail',
                'msg':'No user found.'
            }


    def get_transactions(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
            transactions = []
            user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)])
            for rec in self.env['anyservice.transaction'].search([('partner_id','=',user.id)],order="id desc",offset=vals.get('offset',0),limit=vals.get('limit',50)):
                transactions.append({
                        'name':rec.sudo().name+'\nDated - '+convertdatetolocal(self.env.user.tz or pytz.utc,rec.create_date),
                        'credit':str(rec.sudo().credit),
                        'debit':str(rec.sudo().debit),
                        'total':str(rec.sudo().total),
                    })
            return {
                'result':'Success',
                'transactions':transactions
            }
        else:
            return {
                'result':'Fail',
                'msg':'User not found.'
            }
