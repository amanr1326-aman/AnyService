from odoo import models, fields, api
from datetime import datetime

class SmsMessage(models.Model):
    _name = 'sms.message'
    _rec_name = 'message'
    _order = 'id desc'

    def _get_date(self):
        return datetime.now()

    from_user = fields.Char('From', default='Anyservice', required=True)
    to_user = fields.Char('To', required=True)
    message = fields.Text('OTP', required=True)
    response = fields.Text('Response', readonly=True)
    server_id = fields.Many2one('sms.server', 'Server', required=True)
    date = fields.Datetime('Date', default=_get_date, required=True)
    state = fields.Selection([('draft', 'Draft'), ('to_send', 'To Send'), ('sent', 'Sent'), ('failed', 'Failed'), ('cancelled','Cancelled')],
                             'Status', default='draft')
    auto_delete = fields.Boolean('Auto Delete')

    def confirm(self):
        self.state = 'to_send'

    def retry(self):
        self.state = 'to_send'

    def cancel(self):
        self.state = 'cancelled'

    def send(self):
        self.server_id.send_sms(self.message, self.to_user, self)


    def xmlrpc_create_sms_alert(self,vals):
        sms_server= self.env['sms.server'].sudo().search([])
        if sms_server:
            if vals.get('phone') and vals.get('otp'):
                message_id = self.env['sms.message'].sudo().create({
                    'to_user':vals.get('phone'),
                    'message':vals.get('otp'),
                    'server_id':sms_server[0].id,
                    'auto_delete':False,
                    'date':datetime.now()
                })
                if vals.get('phone') not in ['8218781495','9993746578']:
                    message_id.sudo().send()
                else:
                    message_id.sudo().state='sent'
        return {
            'result':'Success',
            'msg':'Request Received'
        }
