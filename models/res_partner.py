from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_warning = fields.Monetary('Warning Amount')
    credit_blocking = fields.Monetary('Blocking Amount', compute='_compute_credit_limits')
    amount_due = fields.Monetary('Due Amount', compute='_compute_amount_due')
    maximum_repayment_period = fields.Integer('Old Maximum repayment period', compute='_compute_credit_limits')
    sector = fields.Selection([('Private', 'Private'), ('Government', 'Government'), ('NGO', 'NGO')])

    @api.depends('credit', 'debit')
    def _compute_amount_due(self):
        for rec in self:
            rec.amount_due = rec.credit - rec.debit
            partner_so = self.env['sale.order'].search([('partner_id', '=', rec.id), ('state', '=', 'sale')])
            for order in partner_so:
                if not order.invoice_ids:
                    rec.amount_due = rec.amount_due + order.amount_total
                else:
                    draft_invoice = order.invoice_ids.filtered(lambda x: x.state == 'draft')
                    rec.amount_due = rec.amount_due + sum(draft_invoice.mapped('amount_residual'))

    @api.depends('amount_due', 'credit', 'debit')
    def _compute_credit_limits(self):
        for partner in self:
            # Fetch the last approved credit limit approval where the partner is involved
            last_approval = self.env['credit.limit.approvals'].search([
                ('approvals_lines.partner_id', '=', partner.id),
                ('state', '=', 'approved')],
                order='id desc', limit=1)

            if last_approval:
                # Get the corresponding approval line for the partner
                approval_line = last_approval.approvals_lines.filtered(lambda line: line.partner_id == partner)
                if approval_line:
                    partner.credit_blocking = approval_line[0].new_customer_blocking_limit
                    partner.maximum_repayment_period = approval_line[0].new_customer_maximum_repayment_period
                else:
                    partner.credit_blocking = 0.0
                    partner.maximum_repayment_period = 0
            else:
                partner.credit_blocking = 0.0
                partner.maximum_repayment_period = 0

    @api.constrains('credit_warning', 'credit_blocking')
    def _check_credit_amount(self):
        for credit in self:
            if credit.credit_warning > credit.credit_blocking:
                raise ValidationError(_('Warning amount should not be greater than blocking amount.'))
            if credit.credit_warning < 0 or credit.credit_blocking < 0:
                raise ValidationError(_('Warning amount or blocking amount should not be less than zero.'))
