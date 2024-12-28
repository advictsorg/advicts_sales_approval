# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleApprovalLine(models.Model):
    _name = "sale.approval.line"
    _description = "Sale Approval Line"
    _order = 'level'
    _rec_name = 'level'

    group_approve = fields.Selection(string='Approve Process By', selection=[
        ('group', 'Group'), ('user', 'User')], default="user")
    level = fields.Integer(string='Level')
    is_optional = fields.Boolean()
    group_ids = fields.Many2many(
        string='Group Name', comodel_name='res.groups', ondelete='restrict')
    user_ids = fields.Many2many('res.users')
    user_id = fields.Many2one('res.users', 'Send To')
    sale_approval_id = fields.Many2one('sale.approval', string='Approvals')
