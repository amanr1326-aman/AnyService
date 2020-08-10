# -*- coding: utf-8 -*-
{
    'name': "SMS Gateway",

    'summary': "To send sms and manage sms server. ",
    'author': "Aman Kumar",

    'description': """
        This module manage sms server and handle all sms.
    """,
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['base'],

    'data': [
        'security/ir.model.access.csv',
        'views/sms_server_view.xml',
        'views/sms_message_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}