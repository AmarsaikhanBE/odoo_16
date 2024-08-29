from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    notification_type = fields.Selection(default="inbox")
