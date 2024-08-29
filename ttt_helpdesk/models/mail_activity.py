from odoo import fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    state = fields.Selection(store=True)
