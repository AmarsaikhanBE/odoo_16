from odoo import models, fields


class HelpdeskTicketType(models.Model):
    _name = "helpdesk.ticket.type"
    _description = "Helpdesk Ticket Type"

    name = fields.Char("Name", required=True)
