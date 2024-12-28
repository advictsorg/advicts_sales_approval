{
    "name": "Advicts Sales Order Approval",
    "version": "17.0.0.1",
    "category": "Sales",
    "summary": """
        Dynamic approval process for Sale Orders based on amount, discount,
        salesperson, customer balance, and product quantities.
        """,
    "description": """
        Dynamic approval process for Sale Orders based on amount, discount, salesperson,
        customer balance, and product quantities..
    """,
    'author': "GhaithAhmed@Advicts",
    'website': 'http://advicts.com/',
    "depends": ["base", "sale", "sale_management"],
    "data": [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/approval_email_template.xml',
        'wizard/sale_order_reject_views.xml',
        'views/res_partner.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_approval_line_views.xml',
        'views/sale_approval_views.xml',
        'views/credit_limit_approvals.xml',
    ],
    'installable': True,
    'auto_install': False,
}
