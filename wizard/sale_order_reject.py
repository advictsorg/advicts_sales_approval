from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from markupsafe import Markup


class SaleOrderReject(models.TransientModel):
    _name = "sale.order.reject"
    _description = "Sale Order Reject Wizard"

    order_id = fields.Many2one('sale.order', string="Order")
    reason = fields.Text("Rejection Reason")

    def action_reject_sale_order(self):
        if not self.order_id:
            raise ValidationError(_('Sale Order not found!\n Refresh the page and try again.'))
        if self.order_id and self.order_id.current_waiting_approval_line_id and not self.order_id.current_waiting_approval_line_id.state and not self.order_id.current_approval_state:
            self.order_id.reject_date = fields.Datetime.now()
            self.order_id.rejected_user_id = self.env.user.id
            self.order_id.reject_reason = self.reason if self.reason else False
            if not self.order_id.current_waiting_approval_line_id.is_optional:
                self.order_id.state = 'reject'
                self.order_id.is_rejected = True

            else:
                other_user = self.order_id.current_waiting_approval_line_id.user_id
                if other_user:
                    approval_lines = [(0, 0, {
                        'approval_level': self.order_id.current_waiting_approval_line_id.approval_level + 1,
                        'type': self.order_id.current_waiting_approval_line_id.type,
                        'user_ids': [other_user.id],
                    })]
                    if approval_lines:
                        self.order_id.write({'sale_approved_ids': approval_lines,
                                     'is_saleperson_in_cc': self.order_id.sale_approval_id.is_sale_person})
                self.order_id.current_waiting_approval_line_id.is_reject = True
                self.order_id.action_confirm()

            template = self.env.ref('advicts_sales_approval.reject_approval_email_template')
            if template:
                if self.order_id.is_saleperson_in_cc:
                    template.email_cc = self.order_id.user_id.email if self.order_id.user_id else False
                mail = template.send_mail(int(self.order_id.id))
                if mail:
                    mail_id = self.env['mail.mail'].browse(mail)
                    self.order_id.message_post(body=Markup(mail_id.body_html))
                    mail_id[0].sudo().send()
        return True
