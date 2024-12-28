from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SaleApproval(models.Model):
    _name = "sale.approval"
    _description = "Sale Approval"

    name = fields.Char(required=True, index=True, string="Name")
    type = fields.Selection(
        selection=[
            ('amount', "Sales Amount"),
            ('customer', "Customer Credit Amount"),
            ('customer_exceed', "Customer Credit Exceed Approval"),
            ('quantity', "Sales Quantity"),
            ('discount', "Sales Discount"),
        ],
        string="Type",
        copy=False, index=True, required=True,
        default='amount')
    is_cash_activate = fields.Boolean('Activate in Cash Sale Order')

    group_limit = fields.Many2many('res.groups', string='Apply On Groups')

    company_currency_id = fields.Many2one('res.currency', 'Currency',
                                          default=lambda self: self.env.company.currency_id.id)
    team_id = fields.Many2one('crm.team', 'Sales Team')
    days_limit = fields.Integer('Days Limit')
    minimum_amount = fields.Monetary(string='Minimum Amount', currency_field='company_currency_id')
    minimum_qty = fields.Float('Minimum Quantity')
    minimum_qty_type = fields.Selection(
        selection=[
            ('above', "Above minimum stock"),
            ('under', "Under minimum stock"),
        ],
        string="Minimum Stock Type",
        index=True,
        default='above')
    max_qty = fields.Float('Max Quantity')
    minimum_discount = fields.Float('Minimum Discount')
    is_sale_person = fields.Boolean('Sales Person Always in CC')
    sale_approval_line_ids = fields.One2many('sale.approval.line', 'sale_approval_id', string='Approval Lines')

    @api.onchange('sale_approval_line_ids')
    def _onchange_sale_approval_line_ids(self):
        approval_level = []
        for approval in self.sale_approval_line_ids:
            if approval.level in approval_level:
                raise ValidationError(_('Make sure approval levels are must be unique!'))
            approval_level.append(approval.level)
