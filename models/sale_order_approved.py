

from odoo import fields, models,api, _
from odoo.exceptions import ValidationError

class SaleApproval(models.Model):
    _name = "sale.order.approved"
    _description = "Sale order approved details"
    _rec_name = 'approval_level'

    approval_level = fields.Integer('Approval Level')
    user_ids = fields.Many2many('res.users', string='Users')
    group_ids = fields.Many2many('res.groups', string='Groups')
    state = fields.Boolean('State')
    is_optional = fields.Boolean()
    user_id = fields.Many2one('res.users', string='Extend User')
    is_reject = fields.Boolean()
    type = fields.Selection(
        selection=[
            ('amount', "Amount Approval"),
            ('customer', "Customer Credit Approval"),
            ('customer_exceed', "Customer Credit Exceed Approval"),
            ('quantity', "Quantity Approval"),
            ('discount', "Discount Approval"),
        ],
        string="Approval Type",)
    approved_date = fields.Datetime('Approved Date')
    approved_id = fields.Many2one('res.users', string='Approved By')
    sale_approval_id = fields.Many2one('sale.approval', string='Sale Approval')
    order_id = fields.Many2one('sale.order', string='Order')
