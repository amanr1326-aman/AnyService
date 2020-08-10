from odoo import models, fields, api, _
import requests, hashlib
from datetime import datetime
from odoo.tools import ustr
from odoo.exceptions import UserError
import urllib.parse
import json

HOST = "https://www.fast2sms.com/dev/bulk"
SECURE_KEY = "cO5o0yXUBNLR79Fune6Ybr1Kjdp3WqQvZfCxalPE4HTmhiGtDMANTWMgqSxivb6hcJGkZDF7yz4oj5U3"
SENDER_ID = "FSTSMS"
MESSAGE_ID = "32688"



class SmsServer(models.Model):
    _name = 'sms.server'

    name = fields.Char(string='Description', required=True, index=True)
    host = fields.Char(string='SMS server Server', required=True, help="Hostname or IP of SMS server server", default=HOST)
    senderid = fields.Char(string="Sender ID", default=SENDER_ID)
    secure_key = fields.Char(string="API Key", default=SECURE_KEY)
    message = fields.Char(string="Message ID", default=MESSAGE_ID)
    sequence = fields.Integer(string='Priority', default=10, help="When no specific mail server is requested for a mail, the highest priority one "
                                                                  "is used. Default priority is 10 (smaller number = higher priority)")

    _sql_constraints = [
        ('sequence_uniq', 'UNIQUE (sequence)', 'You can not have two server with same priority !'),
        ('name_uniq', 'UNIQUE (name)', 'You can not have two server with same name !'),
    ]

    def test_connection(self):
        try:
            requests.get(url=self.host,verify=False)
        except Exception as e:
            raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s") % ustr(e))
        raise UserError(_("Connection Test Succeeded! Everything seems properly set up!"))



    def send_sms(self, message, mobileno, message_id=False):
        self.ensure_one()
        if not message_id:
            message_id = self.env['sms.message'].create({
                'to_user': mobileno,
                'message': message,
                'server_id': self.id,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'state': 'draft',
            })
        payload = "sender_id=FSTSMS&message=%s&language=english&route=qt&numbers=%s&variables={#BB#}&variables_values=%s"%(self.message,str(mobileno),message)
        headers = {
            'authorization': self.secure_key,
            'Content-Type': "application/x-www-form-urlencoded",
            'Cache-Control': "no-cache",
            }
        try:
            result = requests.request("POST", self.host, data=payload, headers=headers,verify=False)
            print(result.text,payload)
            response = json.loads(result.text)
            if response:
                message_id.response = str(response)
                if response.get('return'):
                    message_id.state = 'sent'
                else:
                    message_id.state = 'failed'
            else:
                message_id.state = 'failed'
                raise UserError('SMS Server Error')
        except:
            message_id.state = 'failed'
            raise UserError('SMS Server Error')
