# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from geopy import distance


def check_distance(lat1,long1,lat2,long2,radius):
    dis = distance.distance((lat1,long1),(lat2,long2)).km
    if dis<=radius:
        return True
    else:
        return True


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
    state = fields.Selection([('draft','Draft'),('pending','Pending For KYC'),('approved','Approved'),('banned','Banned')], default='draft')
    # user_role = fields.Many2one('res.users', string="User Role")
    aadhar_number = fields.Char()
    aadhar_front = fields.Binary(string="Aadhar Front Image")
    aadhar_back = fields.Binary(string="Aadhar Back Image")

    place = fields.Char('Place')
    lat = fields.Char('Latitude')
    long = fields.Char('Longitude')

    radius = fields.Integer('Service Distance', default=5)

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
        if vals.get('app_version',False)!=app_version:
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
                    values.pop('login')
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
                        'radius':user.radius,
                        'place':user.place
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
            user = self.search([('phone','=',vals.get('phone')),('state','!=','banned'),('is_anyservice_user','=',True)])
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
        agent_id = vals.get('agent_id')
        id = decrypt(vals.get('login'))
        user = self.search([('id','=',id),('is_anyservice_user','=',True)])
        services = []
        service_records = self.env['anyservice.service'].sudo().search([('partner_id','=',agent_id)])
        for rec in service_records:
            cost=0
            if rec.delivery_charge:
                cost = 10+4*(distance.distance((user.lat,user.long),(rec.partner_id.lat,rec.partner_id.long)).km)
            services.append({
                'id':rec.id,
                'name':rec.name,
                'agent_id':rec.partner_id.id,
                'category':rec.category_id.name,
                'price':rec.price,
                'is_measurable':rec.is_measurable,
                'charge':round(cost),
            })
        return {
            'result':'Success',
            'company':service_records[0].partner_id.parent_id.name,
            'rating':service_records[0].partner_id.supplier_rank,
            'categories':', '.join(set([rec.get('category') for rec in services])),
            'address':(service_records[0].partner_id.street+' '+service_records[0].partner_id.parent_id.street2+'\n'+service_records[0].partner_id.parent_id.city+' '+service_records[0].partner_id.parent_id.state_id.name+' '+str(service_records[0].partner_id.parent_id.zip)).replace('\n\n','\n').replace('  ',' ').strip(),
            'image':service_records[0].partner_id.parent_id.image_1920,
            'services':services
        }


    def search_services(self,vals):
        clean_str_data(vals)
        id = decrypt(vals.get('login'))
        user = self.search([('id','=',id),('is_anyservice_user','=',True)])
        domain = ['&']
        services = []
        if vals.get('key'):
            domain.append('|')
            domain.append(('name','ilike',vals.get('key')))
        categ = vals.get('categ')
        category_ids = False
        if categ:
            category_id = self.env['product.category'].search([('name','ilike',categ)])
            if vals.get('key'):
                category_ids = self.env['product.category'].search(['|','|',('name','ilike',categ),('id','child_of',category_id.ids),('name','ilike',vals.get('key'))])
            else:
                category_ids = self.env['product.category'].search(['|',('name','ilike',categ),('id','child_of',category_id.ids)])
        elif vals.get('key'):
            category_ids = self.env['product.category'].search([('name','ilike',vals.get('key'))])

        
        domain.append(('category_id','in',category_ids.ids))
        partner_ids = self.env['res.partner'].search([('active_mode','=',True),('is_anyservice_user','=',True),('user_type','=','agent')])
        temp_partner_ids = partner_ids
        partner_ids = partner_ids.filtered(lambda x:check_distance(float(user.lat),float(user.long),float(x.lat),float(x.long),min(user.radius,x.radius))==True)
        domain.append(('partner_id','in',partner_ids.ids))
        service_records = self.env['anyservice.service'].sudo().search(domain)
        for rec in service_records:
            cost=0
            if rec.delivery_charge:
                cost = 10+4*(distance.distance((user.lat,user.long),(rec.partner_id.lat,rec.partner_id.long)).km)
            services.append({
                'id':rec.id,
                'name':rec.name,
                'agent_id':rec.partner_id.id,
                'category':rec.category_id.name,
                'price':rec.price,
                'rating':rec.partner_id.supplier_rank,
                'company':rec.partner_id.parent_id.name,
                'image':rec.partner_id.parent_id.image_1920,
                'charge':round(cost),
            })
        partners = False
        if vals.get('key'):
        	partners = temp_partner_ids.filtered(lambda x:vals.get('key').lower() in x.parent_id.name.lower())
        if partners:
            for rec in self.env['anyservice.service'].sudo().search([('partner_id','in',partners.ids),('id','not in',service_records.ids)]):
                cost=0
                if rec.delivery_charge:
                    cost = 10+4*(distance.distance((user.lat,user.long),(rec.partner_id.lat,rec.partner_id.long)).km)
                services.append({
                    'id':rec.id,
                    'name':rec.name,
                    'agent_id':rec.partner_id.id,
                    'category':rec.category_id.name,
                    'price':rec.price,
                    'rating':rec.partner_id.supplier_rank,
                    'company':rec.partner_id.parent_id.name,
                    'image':rec.partner_id.parent_id.image_1920,
                    'charge':round(cost),
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
    product_id = fields.Many2one('product.product','Any Service Product')
    journal_id = fields.Many2one('account.journal','Any Service Journal')
    invoice_journal_id = fields.Many2one('account.journal','Any Service Invoice Journal',domain=[('type','=','sale')])

    @api.model
    def get_values(self):
        res = super(AnyserviceConfiguration, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        version = params.get_param('anyservice_master.version', default=False)
        description = params.get_param('anyservice_master.description', default=False)
        product_id = params.get_param('anyservice_master.product_id', default=False)
        journal_id = params.get_param('anyservice_master.journal_id', default=False)
        invoice_journal_id = params.get_param('anyservice_master.invoice_journal_id', default=False)
        res.update(version=version,description=description,product_id=int(product_id),journal_id=int(journal_id),invoice_journal_id=int(invoice_journal_id))
        return res


    def set_values(self):
        super(AnyserviceConfiguration, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.version", self.version)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.description", self.description)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.product_id", self.product_id and self.product_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.journal_id", self.journal_id and self.journal_id.id or False)
        self.env['ir.config_parameter'].sudo().set_param("anyservice_master.invoice_journal_id", self.invoice_journal_id and self.invoice_journal_id.id or False)
