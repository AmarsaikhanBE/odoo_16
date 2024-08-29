{
    "name": "Helpdesk",
    "version": "1.0",
    "category": "Operations",
    "summary": "Tracking Support Tickets",
    "description": """
        A Helpdesk module to manage support tickets, with features similar to the Odoo Enterprise Helpdesk module.
    """,
    "author": "ABE",
    "depends": ["base", "hr", "mail"],
    "license": "LGPL-3",
    "data": [
        "security/groups.xml",
        "views/ticket_views.xml",
        "views/ticket_type_views.xml",
        "views/menu_views.xml",
        "data/ir_rule.xml",
        "security/ir.model.access.csv",
        "data/cron_overdue_activity.xml",
    ],
    "assets": {
        "web.assets_backend": ["ttt_helpdesk/static/src/scss/style.scss"],
    },
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
}
