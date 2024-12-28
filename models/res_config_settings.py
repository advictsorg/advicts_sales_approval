# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dynamic_approval = fields.Boolean(
        string='Dynamic Approval', related='company_id.dynamic_approval', readonly=False)


class CreditApprovalSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    approved_user_ids = fields.Many2many(
        'res.users', related='company_id.approved_user_ids', string='Manager Approval', readonly=False)
    directors_user_ids = fields.Many2many(
        'res.users', related='company_id.directors_user_ids', string='Directors Approval', readonly=False)
