# -*- coding: utf-8 -*-
from odoo import http


class AnyserviceMaster(http.Controller):

	@http.route('/order/print', methods=['POST', 'GET'], csrf=False, type='http', auth="public")
	def print_order_invoice(self, **kw):
		record_id = kw['id']
		order = http.request.env['anyservice.order'].sudo().search([('id','=',record_id)])
		if record_id:
			pdf, _ = http.request.env.ref('anyservice_master.order_invoices').sudo().render_qweb_pdf([order.id])
			pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
			return http.request.make_response(pdf, headers=pdfhttpheaders)
		else:
			return http.request.redirect('/')

	@http.route('/privacy', methods=['POST', 'GET'], csrf=False, type='http', auth="public")
	def print_order_invoice(self, **kw):
		instruction = http.request.env['ir.config_parameter'].sudo().get_param('anyservice_master.instruction')
		return "<h1>Privacy & Policy</h1><br/>"+instruction.replace('\n','<br/>')