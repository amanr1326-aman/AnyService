from odoo import models, fields, api, _
from odoo.exceptions import UserError
STATES = {
    'draft':'Draft','pending':'Pending From Agent','accepted':'Accepted By Agent','progress':'In Progress','done':'Awaiting Payment','paid':'Paid','cancel':'Cancelled','Message From Agent':'Message From Agent','Message From Customer':'Message From Customer'
}

import requests
import json



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
    response = fields.Text()
    record_name = fields.Integer()


    def send_notification(self,fcm_token=False):
    	serverToken = 'AAAAYfNc-Z4:APA91bEnxdem8P7oQnyYd8texxhY8o4ndot3cGDLtfkcXr6j1qBe83K1iHgKFqMK8OMG1ktgmYnhnGaHsOW2HmcM0TMeImni5WJwDq8Ppa8v4FpKwEgKcUvnE9s-rrilqv7F11FOlhis'
    	deviceToken = fcm_token or self.partner_id.fcm_token
    	if deviceToken:
	    	headers = {'Content-Type': 'application/json','Authorization': 'key=' + serverToken,}
	    	# body = {'collapse_key':'Any Service','priority':'high','ttl':'1s','notification': {'title': self.name,'body': self.message,},'to':deviceToken,'android':{'priority': 'high','ttl':'1s'},'webpush':{'urgency':'high','TTL':'1s'}}
	    	body = {'notification': {'title': self.name,'body': self.message,},'to':deviceToken,}
	    	#   'data': dataPayLoad,
	    	# print(body)
	    	response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body), verify=False)
	    	# print(response.text)
	    	self.response = str(response.text)
	    	self.read_notification = True
    	# push_service = FCMNotification(api_key="AAAAYfNc-Z4:APA91bFR3TlT9ofi_PmQm5fgkkxvWE6g1aBwm1ns9QnZ-UsMDzc3Anm06qq6KM8vlgNGkEOWQfcQESL8sSM7RCouC9o0sFdatZ_Y6IszIeQq8fNy0gEZdj1W81szSmQUWEX5axG4fn4U")
    	# result = push_service.notify_single_device(registration_id="elOqcKdZSSiirwjmn7oLOE:APA91bH8l4f7_CgbJ3V0JBsmmlO8TFklLTUWC3ovhMhysL3BNoT4kZsshcGfU-j4wVX2ST57HporzwvEZprOEIRpfzVq_aKSoo-lTacFRbva9fgDG5aW0yiyGYipo6usiF4kjs4dfKjw", message_title=self.name, message_body=self.message)
    	# print(response.text)
    	# self.response = str(response.text)
    	# self.read_notification = True


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

	# def clear_notifications(self,vals):
	# 	clean_str_data(vals)
	# 	if vals.get('login'):
	# 		records = []
	# 		user = self.env['res.partner'].search([('id','=',decrypt(vals.get('login'))),('state','!=','banned'),('is_anyservice_user','=',True)],order="id desc")
	# 		records = self.search([('partner_id','=',user.id),('read_notification','=',True)],limit=vals.get('limit',50))
	# 		records.sudo().unlink()
	# 	return {
	# 	'result':'Success',
	# 	'msg':'Done'
	# 	}
        	
