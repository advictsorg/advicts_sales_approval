# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from markupsafe import Markup
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def read(self, fields=None, load='_classic_read'):
        if self.env.user.company_id.dynamic_approval:
            data = self.sudo().search([]).filtered(
                lambda l: l.is_approval_reject_button)
            data._compute_is_approval_reject_button()
        return super(SaleOrder, self).read(fields=fields, load=load)

    is_approval = fields.Boolean(related='company_id.dynamic_approval')
    sector = fields.Selection(related='partner_id.sector')
    state = fields.Selection(
        selection=[
            ('draft', "Quotation"),
            ('waiting', 'Waiting For Approval'),
            ('manager_approved', 'Approved'),
            ('customer_waiting', 'Waiting For Customer Approval'),
            ('approved', 'Customer Approved'),
            ('reject', 'Reject'),
            ('sent', "Quotation Sent"),
            ('sale', "Sales Order"),
            ('done', "Locked"),
            ('cancel', "Cancelled"),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')

    cash_type = fields.Selection(
        selection=[
            ('cash', "Cash"),
            ('deferred', "Deferred"),
        ],
        string="Cash Type",
        copy=False, index=True,
        required=True,
        default='cash')

    company_currency_id = fields.Many2one('res.currency', 'Currency',
                                          default=lambda self: self.env.company.currency_id.id)
    customer_amount_due = fields.Monetary(related='partner_id.amount_due', currency_field='company_currency_id')
    customer_blocking_limit = fields.Monetary(related='partner_id.credit_blocking',
                                              currency_field='company_currency_id')
    customer_maximum_repayment_period = fields.Integer(related='partner_id.maximum_repayment_period')
    sale_approval_id = fields.Many2one(
        'sale.approval', string='Amount Approval Level', copy=False)
    quantity_approval_id = fields.Many2one(
        'sale.approval', string='QTY Approval Level', copy=False)
    discount_approval_id = fields.Many2one(
        'sale.approval', string='Discount Approval Level', copy=False)
    customer_approval_id = fields.Many2one(
        'sale.approval', string='Customer Credit Approval Level', copy=False)
    customer_exceed_approval_id = fields.Many2one(
        'sale.approval', string='Customer Exceeds Credit Approval Level', copy=False)

    user_ids = fields.Many2many('res.users', string='Users', copy=False)
    group_ids = fields.Many2many('res.groups', string='Groups', copy=False)
    next_approval_level = fields.Char(string='Next Approval Level', copy=False)
    reject_date = fields.Datetime('Reject Date', copy=False)
    rejected_user_id = fields.Many2one(
        'res.users', string='Reject By', copy=False)
    reject_reason = fields.Text('Reject Reason', copy=False)
    current_waiting_approval_line_id = fields.Many2one(
        'sale.order.approved', string='Current approval line', copy=False)
    sale_approved_ids = fields.One2many(
        'sale.order.approved', 'order_id', string='Sale Approval Details')
    current_approval_state = fields.Boolean(
        'Current approval state', copy=False)
    is_saleperson_in_cc = fields.Boolean('Sales Person in CC', default=False)
    approved_user_ids = fields.Many2many(
        'res.users', 'approved_user_sale_order_rel', string='Approved Users', copy=False)
    is_approval_reject_button = fields.Boolean(
        'Approval Reject button', default=False, compute='_compute_is_approval_reject_button')
    is_rejected = fields.Boolean('Reject Order', default=False, copy=False)
    all_level_approved = fields.Boolean(
        'All Level Approved', default=False, compute='_compute_all_level_approved')
    is_display = fields.Boolean()

    def _create_approval_activity(self):
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        for user in self.user_ids:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                note='A sale order requires approval.',
                user_id=user.id,
                summary=_('Approval Required')
            )

    def _get_user_emails(self):
        self.ensure_one()
        if self.user_ids and not self.group_ids:
            send_users = self.user_ids.mapped(
                'partner_id').filtered(lambda l: l.email)
            return ", ".join([e for e in send_users.mapped("email") if e])
        if not self.user_ids and self.group_ids:
            approval_users = []
            users = self.env['res.users'].sudo().search([])
            for user in users:
                if (set(self.group_ids.ids).issubset(set(user.groups_id.ids))):
                    approval_users.append(user.id)
            user_data = self.env['res.users'].browse(approval_users).mapped(
                'partner_id').filtered(lambda l: l.email)
            if user_data:
                return ",".join([e for e in user_data.mapped("email") if e])

    @api.depends('sale_approved_ids')
    def _compute_all_level_approved(self):
        for record in self:
            if record.sale_approved_ids and all(
                    record.sale_approved_ids.filtered(lambda r: not r.is_reject).mapped('state')):
                record.all_level_approved = True
            else:
                record.all_level_approved = False

    @api.depends('approved_user_ids', 'user_ids')
    def _compute_is_approval_reject_button(self):
        for record in self:
            record.is_display = False
            record.is_approval_reject_button = False
            if record.user_ids:
                if self.env.user.id in record.user_ids.ids or self.env.user.has_group(
                        "advicts_sales_approval.sale_order_approval_manager"):
                    record.is_display = True
                    record.is_approval_reject_button = True
            elif record.group_ids:
                if (set(record.group_ids.ids).issubset(set(self.env.user.groups_id.ids))):
                    record.is_approval_reject_button = True
                    record.is_display = True

    def action_reject(self):
        if self.is_approval != True:
            raise ValidationError(_('Change approval Settings!'))
        return {
            'name': _('Sale Order Reject'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.reject',
            'target': 'new',
            'context': {'default_order_id': self.id}
        }

    def send_to_customer(self):
        for order in self:
            order.state = 'customer_waiting'

    def customer_approve(self):
        for order in self:
            order.state = 'approved'

    def final_confirm(self):
        self.action_confirm()

    def action_approve(self):
        if self.current_waiting_approval_line_id and not self.current_waiting_approval_line_id.state and not self.current_approval_state and not self.current_waiting_approval_line_id.is_reject:
            self.current_approval_state = True
            self.current_waiting_approval_line_id.state = True
            self.current_waiting_approval_line_id.approved_date = fields.Datetime.now()
            self.current_waiting_approval_line_id.approved_id = self.env.user.id
            self.approved_user_ids = [(4, self.env.user.id)]
            self.action_confirm()
        return True

    def _prepare_approved_line(self, line, type):
        if line:
            return {
                'approval_level': line.level,
                'is_optional': line.is_optional,
                'user_id': line.user_id.id if line.user_id else False,
                'type': type,
                'user_ids': line.user_ids.ids if line.user_ids else [],
                'group_ids': line.group_ids.ids if line.group_ids else [],
            }

    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent', 'waiting', 'manager_approved', 'customer_waiting', 'approved', 'reject'}

    def _check_credit_limit(self):
        for order in self:
            if order.cash_type != 'cash':
                if not self.env.user.has_group(
                        "advicts_sales_approval.sale_order_approval_manager"):
                    customer_credit = order.amount_total + order.customer_amount_due
                    if order.customer_blocking_limit:
                        if customer_credit > order.customer_blocking_limit:
                            raise ValidationError('The Customer exceed the credit limit!')
                    if order.customer_maximum_repayment_period and order.customer_amount_due:
                        last_payment = self.env['account.payment'].sudo().search(
                            [('partner_id', '=', order.partner_id.id), ('date', '<=', fields.Datetime.now())],
                            limit=1, order="date desc")

                        if last_payment:
                            last_payment_date = last_payment.date
                            max_date = fields.Datetime.now()

                            # Calculate the difference in days
                            diff = relativedelta(max_date, last_payment_date)
                            days_diff = diff.days

                            if days_diff > order.maximum_repayment_period:
                                raise ValidationError('Customer has exceeded the maximum repayment period!')
                        else:
                            raise ValidationError('No previous payment found for this customer!')

    # def action_quotation_send(self):
    #     for order in self:
    #         if order.is_approval:
    #
    #     return super(SaleOrder, self).action_quotation_send()
    def action_confirm(self):

        self._compute_amounts()
        for order in self:
            # self._check_credit_limit()
            if order.state == 'approved':
                return super(SaleOrder, self).action_confirm()
            elif order.is_approval:
                if ((order.sale_approval_id or order.quantity_approval_id or order.discount_approval_id
                     or order.customer_approval_id or order.customer_exceed_approval_id) and not order.sale_approved_ids):
                    if order.sale_approval_id and not order.sale_approval_id.sale_approval_line_ids:
                        raise ValidationError(_('No any approval level for Amount found!'))
                    if order.quantity_approval_id and not order.quantity_approval_id.sale_approval_line_ids:
                        raise ValidationError(_('No any approval level for Quantity found!'))
                    if order.discount_approval_id and not order.discount_approval_id.sale_approval_line_ids:
                        raise ValidationError(_('No any approval level for Discount found!'))
                    if order.customer_approval_id and not order.customer_approval_id.sale_approval_line_ids:
                        raise ValidationError(_('No any approval level for Customer Credit found!'))
                    if order.customer_exceed_approval_id and not order.customer_exceed_approval_id.sale_approval_line_ids:
                        raise ValidationError(_('No any approval level for Customer Credit found!'))
                    approval_lines = []
                    if order.sale_approval_id:
                        for record in order.sale_approval_id.sale_approval_line_ids:
                            approval_lines.append(
                                (0, 0, order._prepare_approved_line(record, 'amount')))
                    if order.quantity_approval_id:
                        for record in order.quantity_approval_id.sale_approval_line_ids:
                            approval_lines.append(
                                (0, 0, order._prepare_approved_line(record, 'quantity')))
                    if order.discount_approval_id:
                        for record in order.discount_approval_id.sale_approval_line_ids:
                            approval_lines.append(
                                (0, 0, order._prepare_approved_line(record, 'discount')))
                    if order.customer_approval_id:
                        for record in order.customer_approval_id.sale_approval_line_ids:
                            approval_lines.append(
                                (0, 0, order._prepare_approved_line(record, 'customer')))
                    if order.customer_exceed_approval_id:
                        for record in order.customer_exceed_approval_id.sale_approval_line_ids:
                            approval_lines.append(
                                (0, 0, order._prepare_approved_line(record, 'customer_exceed')))
                    if approval_lines:
                        order.write({'sale_approved_ids': approval_lines,
                                     'is_saleperson_in_cc': order.sale_approval_id.is_sale_person})
                        # template = order.env.ref(
                        #     'advicts_sales_approval.request_approval_email_template')
                        # if template:
                        #     if order.is_saleperson_in_cc:
                        #         template.email_cc = order.user_id.email if order.user_id else False
                        #     mail = template.send_mail(int(order.id))
                        #     if mail:
                        #         mail_id = order.env['mail.mail'].browse(mail)
                        #         order.message_post(body=Markup(mail_id.body_html))
                        #         mail_id[0].sudo().send()

                if order.sale_approved_ids:

                    if not all(order.sale_approved_ids.filtered(lambda r: not r.is_reject).mapped('state')):

                        approval_level = 0
                        for approval in order.sale_approved_ids.filtered(lambda l: not l.state and not l.is_reject):

                            if approval_level < approval.approval_level and (
                                    not order.current_waiting_approval_line_id or order.current_waiting_approval_line_id.state or order.current_waiting_approval_line_id.is_reject) and (
                                    order.current_approval_state or approval_level == 0
                                    or order.current_waiting_approval_line_id.is_reject):

                                approval_level = approval.approval_level
                                order.user_ids = False
                                order.group_ids = False
                                order.next_approval_level = str(
                                    approval.approval_level)
                                order.user_ids = approval.user_ids.ids
                                order.group_ids = approval.group_ids.ids
                                order.state = 'waiting'
                                order.current_waiting_approval_line_id = approval.id
                                order.current_approval_state = False
                        submit_template = order.env.ref(
                            'advicts_sales_approval.submit_for_approval_email_template')
                        self._create_approval_activity()
                        if submit_template:
                            mail = submit_template.send_mail(int(order.id))
                            if order.is_saleperson_in_cc:
                                submit_template.email_cc = order.user_id.email if order.user_id else False
                            if mail:
                                mail_id = order.env['mail.mail'].browse(mail)
                                order.message_post(body=Markup(mail_id.body_html))
                                mail_id[0].sudo().send()
                    else:
                        if order.all_level_approved:

                            template = order.env.ref(
                                'advicts_sales_approval.approved_sale_order_email_template')
                            if template:
                                if order.is_saleperson_in_cc:
                                    template.email_cc = order.user_id.email if order.user_id else False
                                mail = template.send_mail(int(order.id))
                                if mail:
                                    mail_id = order.env['mail.mail'].browse(mail)
                                    order.message_post(body=Markup(mail_id.body_html))
                                    mail_id[0].sudo().send()
                        if order.state == 'waiting':
                            order.state = 'manager_approved'
                else:
                    return super(SaleOrder, self).action_confirm()
            else:
                return super(SaleOrder, self).action_confirm()

    def _compute_amounts(self):
        res = super(SaleOrder, self)._compute_amounts()
        for record in self:
            if record.is_approval and record.state in ['draft', 'waiting']:
                amount_total = record.amount_total
                if record.sale_approval_id:
                    if record.sale_approval_id.days_limit:
                        sales_on_days = fields.Datetime.now() - timedelta(days=record.sale_approval_id.days_limit)
                        domain = [
                            ('state', 'in', ['draft', 'waiting']),
                            ('date_order', '>=', sales_on_days),
                            ('company_id', '=', record.company_id.id),
                            ('user_id', '=', record.user_id.id)
                        ]
                        total = sum(self.env['sale.order'].sudo().search(domain).mapped('amount_total'))
                        amount_total += total
                data = self.env['sale.approval'].sudo().search(
                    [('type', '=', 'amount'), ('minimum_amount', '<=', amount_total),('team_id', '=', record.team_id.id)],
                    order='minimum_amount desc'
                )

                if data:
                    if ((record.cash_type == 'cash' and data[0].is_cash_activate)
                        or record.cash_type == 'deferred') \
                            and record.sector != 'Government':
                        record.sale_approval_id = data[0].id

                discount_amount = sum(record.order_line.mapped('discount')) / len(
                    record.order_line) if record.order_line else 0
                data = self.env['sale.approval'].sudo().search(
                    [('type', '=', 'discount'), ('minimum_discount', '<=', discount_amount),('team_id', '=', record.team_id.id)],
                    order='minimum_discount desc')
                if data:
                    if ((record.cash_type == 'cash' and data[0].is_cash_activate
                         or record.cash_type == 'deferred')
                            and record.sector != 'Government'):
                        record.discount_approval_id = data[0].id

                for line in record.order_line:
                    min_qty = sum(self.env['stock.warehouse.orderpoint'].sudo().search(
                        [('product_id', '=', line.product_id.id)]).mapped('product_min_qty'))
                    on_hand = sum(self.env['stock.warehouse.orderpoint'].sudo().search(
                        [('product_id', '=', line.product_id.id)]).mapped('qty_on_hand'))
                    if min_qty and on_hand:
                        under_min_qty = on_hand - min_qty
                        if line.product_uom_qty >= under_min_qty:
                            qty_percentage_under = ((line.product_uom_qty - under_min_qty) / min_qty) * 100
                            data = self.env['sale.approval'].sudo().search(
                                [('type', '=', 'quantity'), ('minimum_qty_type', '=', 'under'),
                                 ('minimum_qty', '<=', qty_percentage_under),('team_id', '=', record.team_id.id)],
                                order='minimum_qty desc')
                            if data:
                                if ((record.cash_type == 'cash' and data[0].is_cash_activate)
                                    or record.cash_type == 'deferred') \
                                        and record.sector != 'Government':
                                    record.quantity_approval_id = data[0].id
                                break
                        else:
                            qty_percentage_above = (line.product_uom_qty / under_min_qty) * 100 if min_qty else 0.0
                            data = self.env['sale.approval'].sudo().search(
                                [('type', '=', 'quantity'), ('minimum_qty_type', '=', 'above'),
                                 ('minimum_qty', '<=', qty_percentage_above),('team_id', '=', record.team_id.id)],
                                order='minimum_qty desc')
                            if data:
                                if ((record.cash_type == 'cash' and data[0].is_cash_activate)
                                    or record.cash_type == 'deferred') \
                                        and record.sector != 'Government':
                                    record.quantity_approval_id = data[0].id

                                break
                    if record.cash_type != 'cash':
                        if not self.env.user.has_group(
                                "advicts_sales_approval.sale_order_approval_manager"):
                            customer_credit = record.amount_total + record.customer_amount_due
                            if record.customer_blocking_limit:
                                if customer_credit > record.customer_blocking_limit:
                                    data = self.env['sale.approval'].search(
                                        [('type', '=', 'customer_exceed'),('team_id', '=', record.team_id.id)])
                                    if data:
                                        record.customer_exceed_approval_id = data[0].id
                                else:
                                    data = self.env['sale.approval'].search(
                                        [('type', '=', 'customer'), ('team_id', '=', record.team_id.id)])
                                    if data:
                                        record.customer_approval_id = data[0].id
                            if record.customer_maximum_repayment_period and record.customer_amount_due:
                                last_payment = self.env['account.payment'].sudo().search(
                                    [('partner_id', '=', record.partner_id.id), ('date', '<=', fields.Datetime.now())],
                                    limit=1, order="date desc")

                                if last_payment:
                                    last_payment_date = last_payment.date
                                    max_date = fields.Datetime.now()

                                    # Calculate the difference in days
                                    diff = relativedelta(max_date, last_payment_date)
                                    days_diff = diff.days

                                    if days_diff > record.maximum_repayment_period:
                                        data = self.env['sale.approval'].search(
                                            [('type', '=', 'customer_exceed'),('team_id', '=', record.team_id.id)])
                                        if data:
                                            record.customer_exceed_approval_id = data[0].id
                                else:
                                    data = self.env['sale.approval'].search(
                                        [('type', '=', 'customer_exceed'),('team_id', '=', record.team_id.id)])
                                    if data:
                                        record.customer_exceed_approval_id = data[0].id
                # customer_credit = record.amount_total + record.customer_amount_due
                # if customer_credit > record.customer_blocking_limit:
                #     data = self.env['sale.approval'].search(
                #         [('type', '=', 'customer')])
                #     if data:
                #         record.customer_approval_id = data[0].id

        return res

    @api.onchange('sale_approval_id')
    def onchange_sale_approval_id(self):
        if self.sale_approval_id:
            if self.sale_approval_id.minimum_amount > self.amount_total:
                raise ValidationError(_('Selected Approval is not proper as per your order!'))
