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

class AnyserviceNotification(models.Model):
    _name = 'anyservice.notification'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner',required=True,domain=[('state','=','approved'),('is_anyservice_user','=',True)])
    name = fields.Char(required=True)
    message = fields.Text(required=True)
    read_notification = fields.Boolean()
    model_name = fields.Char()
    record_name = fields.Integer()

    def get_user_notification(self,vals):
        clean_str_data(vals)
        if vals.get('login'):
        	notifications = []
        	user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)],order="id desc")
        	records = self.search([('partner_id','=',user.id),('read','=',False)])
        	for record_id in records:
        		notifications.append({
						'title':record_id.name,
						'message':record_id.message,
						'model':record_id.model_name,
						'record':record_id.record_name,
					})
        	return {
				'result':'Success',
				'notification':notifications
			}