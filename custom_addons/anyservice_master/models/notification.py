from odoo import models, fields, api, _
from odoo.exceptions import UserError
STATES = {
    'draft':'Draft','pending':'Pending From Agent','accepted':'Accepted By Agent','progress':'In Progress','done':'Awaiting Payment','paid':'Paid','cancel':'Cancelled','Message From Agent':'Message From Agent','Message From Customer':'Message From Customer'
}



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
        	records = []
        	user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)],order="id desc")
        	if vals.get('read'):
        		records = self.search([('partner_id','=',user.id)],offset=vals.get('offset',0),limit=vals.get('limit',50))
        	else:
        		records = self.search([('partner_id','=',user.id),('read_notification','=',False)],offset=vals.get('offset',0),limit=vals.get('limit',50))
        	for record_id in records:
        		order = 'false'
	        	if record_id.model_name:
	        		if record_id.model_name == 'anyservice.order':
			            order_id = self.env['anyservice.order'].search([('id','=',int(record_id.record_name))])
			            if order_id.service_ids and order_id.date:
			            	if order_id.service_ids[0].partner_id:
			            		order ={
	                                'id':order_id.id,
	                                'name':order_id.name,
	                                'order_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
	                                'final_date':convertdatetolocal(self.env.user.tz or pytz.utc,order_id.remarks[len(order_id.remarks)-1].date) if order_id.remarks else convertdatetolocal(self.env.user.tz or pytz.utc,order_id.date),
	                                'cust_id':order_id.customer_id.id,
	                                'agent_id':order_id.service_ids[0].partner_id.id,
	                                'cust_name':order_id.customer_id.name,
	                                'agent_name':order_id.service_ids[0].partner_id.parent_id.name,
	                                'description':order_id.desc or '',
	                                'gps_address':order_id.gps_address or '',
	                                'full_address':order_id.full_address or '',
	                                'state':STATES[order_id.state],
	                                'total_price':order_id.total_price,
	                                'image':order_id.service_ids[0].service_id.image_128,
	                                'cust_phone':order_id.customer_id.phone,
	                                'agent_phone':order_id.service_ids[0].partner_id.phone,
	                                'rating':order_id.rating,
                            		'invoice_id':order_id.invoice_id.id or 0,
                                    'code':order_id.code,
	                                }
        		notifications.append({
						'title':record_id.name,
						'message':record_id.message,
						'model':record_id.model_name or '',
						'record':record_id.record_name or '',
						'date':convertdatetolocal(self.env.user.tz or pytz.utc,record_id.create_date),
						'order':order
					})
        		if not vals.get('read'):
        			record_id.read_notification = True
        	return {
				'result':'Success',
				'notification':notifications
			}
