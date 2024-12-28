from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CreditLimitApproval(models.Model):
    _name = 'credit.limit.approvals'
    _description = "Credit Limit Approvals"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(
        'Name', index=True, required=True,
        readonly=False)
    state = fields.Selection(
        selection=[
            ('draft', "New"),
            ('waiting', 'Waiting For Approval'),
            ('approved', 'Approved'),
            ('reject', 'Reject'),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')
    is_all_manager_approved = fields.Boolean('')
    company_id = fields.Many2one(
        'res.company', string='Company', index=True, readonly=False)
    approvals_lines = fields.One2many('credit.limit.approvals.line', 'approval_id', string='Credit Lines')
    approvers = fields.One2many('credit.limit.approver', 'approval_id', string='Approvers')
    approved_user_ids = fields.Many2many(
        'res.users', related='company_id.approved_user_ids', string='Manager Approval')
    directors_user_ids = fields.Many2many(
        'res.users', related='company_id.directors_user_ids', string='Directors Approval')
    is_approval_reject_button = fields.Boolean(
        'Approval Reject button', default=False, compute='_compute_is_approval_reject_button')
    is_rejected = fields.Boolean('Reject Credit Limit', default=False, copy=False)

    @api.depends('company_id', 'approved_user_ids', 'directors_user_ids')
    @api.onchange('company_id', 'approved_user_ids', 'directors_user_ids')
    def _set_approvers(self):
        for rec in self:
            approval_lines = []
            for approver in rec.approved_user_ids:
                approval_lines.append(
                    (0, 0, {
                        'user_id': approver.id,
                        'type': 'manager'
                    }))
            for director in rec.directors_user_ids:
                approval_lines.append(
                    (0, 0, {
                        'user_id': director.id,
                        'type': 'director'
                    }))
            if approval_lines:
                rec.write({'approvers': approval_lines})

    def _create_approval_activity(self, user_ids):
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        for user in user_ids:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                note='New Credit Limit Need to Approval.',
                user_id=user.id,
                summary=_('Approval Required')
            )

    @api.depends('approvers')
    def _compute_is_approval_reject_button(self):
        for record in self:
            record.is_approval_reject_button = False
            if record.state == 'waiting':
                managers = record.approvers.filtered(lambda l: l.type == 'manager' and not l.state)

                if managers:
                    if self.env.user.id in managers.user_id.ids or self.env.user.has_group(
                            "advicts_sales_approval.sale_order_approval_manager"):
                        record.is_approval_reject_button = True
                if record.is_all_manager_approved:
                    managers = record.approvers.filtered(lambda l: l.type != 'manager' and not l.state)
                    if self.env.user.id in managers.ids or self.env.user.has_group(
                            "advicts_sales_approval.sale_order_approval_manager"):
                        record.is_approval_reject_button = True

    def read(self, fields=None, load='_classic_read'):
        data = self.search([]).filtered(
            lambda l: l.is_approval_reject_button)
        data._compute_is_approval_reject_button()
        return super(CreditLimitApproval, self).read(fields=fields, load=load)

    def submit(self):
        for rec in self:
            self._set_approvers()
            if rec.approvers:
                rec.state = 'waiting'
                if rec.approvers.filtered(lambda l: l.type == 'manager'):
                    for app in rec.approvers.filtered(lambda l: l.type == 'manager'):
                        self._create_approval_activity(app.user_id)
                else:
                    raise ValidationError('There is No Approvers')
            else:
                raise ValidationError('There is No Approvers')

    def approve(self):
        for rec in self:
            if all(rec.approvers.mapped('state')):
                rec.state = 'approved'
            for line in rec.approvers:
                if self.env.user.id == line.user_id.id:
                    line.state = True
                    if all(rec.approvers.mapped('state')):
                        rec.state = 'approved'
            if not rec.is_all_manager_approved:
                if all(rec.approvers.filtered(lambda l: l.type == 'manager').mapped('state')):
                    rec.is_all_manager_approved = True
                    if rec.approvers.filtered(lambda l: l.type != 'manager'):
                        for app in rec.approvers.filtered(lambda l: l.type != 'manager'):
                            self._create_approval_activity(app.user_id)
                    else:
                        raise ValidationError('There is No Approvers')


class CreditLimitApprovalLine(models.Model):
    _name = 'credit.limit.approvals.line'
    _description = 'Credit Limit Approvals Lines'

    approval_id = fields.Many2one('credit.limit.approvals', string='approval_id')
    partner_id = fields.Many2one('res.partner', string='Name')
    company_currency_id = fields.Many2one('res.currency', 'Currency',
                                          default=lambda self: self.env.company.currency_id.id)
    customer_blocking_limit = fields.Monetary(related='partner_id.credit_blocking',
                                              currency_field='company_currency_id',
                                              string='Old Blocking limit')
    customer_maximum_repayment_period = fields.Integer(related='partner_id.maximum_repayment_period'
                                                       , string='Old Max Repayment Period')

    new_customer_blocking_limit = fields.Monetary(
        currency_field='company_currency_id',
        string='Blocking limit')
    new_customer_maximum_repayment_period = fields.Integer(string='Max Repayment Period')


class CreditLimitApprover(models.Model):
    _name = "credit.limit.approver"
    _description = "Credit Limit Approvers"

    user_id = fields.Many2one('res.users', string='Name')
    state = fields.Boolean('State')
    type = fields.Selection(
        selection=[
            ('manager', "Manager"),
            ('director', "Director"),
        ])
    approved_date = fields.Datetime('Approved Date')
    approval_id = fields.Many2one('credit.limit.approvals', string='approval_id')
