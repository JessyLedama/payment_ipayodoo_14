# -*- coding: utf-8 -*-
{
    'name': 'iPay Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'author': 'SDL',
    'summary': 'Payment Acquirer: iPay Gateway',
    'version': '1.1',
    'description': """iPay Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_template.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
