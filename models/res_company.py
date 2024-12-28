from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    dynamic_approval = fields.Boolean(string='Dynamic Approval', default=False)

    approved_user_ids = fields.Many2many(
        'res.users', 'approved_credit_limit_rel', string='Manager Approval')
    directors_user_ids = fields.Many2many(
        'res.users', 'approved_credit_limit_dir_rel', string='Directors Approval')
