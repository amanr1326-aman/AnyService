# -*- coding: utf-8 -*-
{
    'name': "Any service Master",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Aman Kumar",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales Management',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['sale_management'],

    # always loaded
    'data': [
        'demo/demo.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/services.xml',
        'views/orders.xml',
        'views/templates.xml',
        'views/notification.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'is_application':True,
}
