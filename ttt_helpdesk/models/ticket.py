from odoo import api, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "HelpDesk Ticket"

    name = fields.Char(string="Захиалгын нэр", required=True)
    desc = fields.Text(string="Тайлбар")
    state = fields.Selection(
        [
            ("draft", "Ноорог"),
            ("sent", "Илгээсэн"),
            ("in_progress", "Ажиллаж байна"),
            ("done", "Шийдвэрлэсэн"),
            ("cancelled", "Цуцалсан"),
        ],
        string="Төлөв",
        default="draft",
        track_visibility="onchange",
    )
    employee_id = fields.Many2one("hr.employee", "Захиалагч")
    location_id = fields.Many2one(
        "hr.work.location",
        "Байршил",
        default=lambda self: self.env["hr.employee"]
        .search([("user_id", "=", self.env.uid)], limit=1)
        .work_location_id.id,
    )
    type_id = fields.Many2one("helpdesk.ticket.type", "Төрөл")
    staff_id = fields.Many2one("hr.employee", "Хариуцагч")
    sent_date = fields.Datetime("Илгээсэн огноо")
    done_date = fields.Datetime("Хаасан огноо")
    editable = fields.Boolean(compute="_compute_editable")

    def _compute_editable(self):
        for record in self:
            record.editable = self.env.user.has_group(
                "base.group_system"
            ) or self.env.user.has_group("ttt_helpdesk.group_manager")

    @api.model
    def create(self, vals):
        if not vals.get("name"):
            raise UserError("Захиалгын нэр бөглөх шаардлагатай.")
        vals["state"] = "draft"
        vals["employee_id"] = (
            self.env["hr.employee"].search([("user_id", "=", self.env.uid)], limit=1).id
        )
        return super(HelpdeskTicket, self).create(vals)

    def write(self, vals):
        if "staff_id" in vals:
            for record in self:
                old_staff_id = record.staff_id.id
                new_staff_id = vals.get("staff_id")

                if new_staff_id and old_staff_id != new_staff_id:
                    old_staff_user_id = (
                        self.env["hr.employee"].browse(old_staff_id).user_id.id
                    )
                    new_staff_user_id = (
                        self.env["hr.employee"].browse(new_staff_id).user_id.id
                    )

                    activities = self.env["mail.activity"].search(
                        [
                            ("res_model", "=", "helpdesk.ticket"),
                            ("res_id", "=", record.id),
                            ("user_id", "=", old_staff_user_id),
                        ]
                    )
                    activities.write({"user_id": new_staff_user_id})

                    if record.staff_id and record.staff_id.user_id:
                        record.message_unsubscribe(
                            [record.staff_id.user_id.partner_id.id]
                        )

                    if new_staff_user_id:
                        new_user_partner_id = (
                            self.env["res.users"].browse(new_staff_id).partner_id.id
                        )
                        record.message_subscribe([new_user_partner_id])

                    new_staff_name = self.env["hr.employee"].browse(new_staff_id).name
                    record.message_post(
                        body=f"Захиалгыг шийдвэрлэхээр {new_staff_name}-д шилжүүллээ.",
                        partner_ids=[record.employee_id.user_id.partner_id.id],
                    )

        return super(HelpdeskTicket, self).write(vals)

    def _check_pending_activities(self):
        pending_activities = self.env["mail.activity"].search_count(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
            ]
        )
        return pending_activities == 0

    def action_send(self):
        for record in self:
            record.write({"state": "sent", "sent_date": datetime.now()})

    def action_start(self):
        for record in self:
            _logger.info(f"record staff_id: {record.staff_id}")
            record.write(
                {
                    "state": "in_progress",
                    "staff_id": (
                        record.staff_id
                        if record.staff_id.id
                        else self.env["hr.employee"]
                        .search([("user_id", "=", self.env.uid)], limit=1)
                        .id
                    ),
                }
            )
            record.message_post(
                body="Захиалгыг хүлээн авлаа.",
                partner_ids=[record.employee_id.user_id.partner_id.id],
            )
            record.message_subscribe(
                [
                    record.employee_id.user_id.partner_id.id,
                    record.staff_id.user_id.partner_id.id,
                ]
            )
            record.activity_schedule(
                "mail.mail_activity_dat_todo",
                user_id=record.staff_id.user_id.id,
                summary="HelpDesk-ийн захиалга шийдвэрлэх.",
                note=f"Захиалга: {self.name}",
                date_deadline=datetime.today() + timedelta(days=1),
            )

    def action_done(self):
        for record in self:
            if not record.type_id:
                raise UserError("Захиалгыг төрөлийг сонгох шаардлагатай.")
            if not record._check_pending_activities():
                raise UserError("Бүх ажилбар хаагдсан байх шаардлагатай.")
            record.write({"state": "done", "done_date": datetime.now()})
            record.message_post(
                body="Захиалгыг шийдвэрлэж хаалаа.",
                partner_ids=[record.employee_id.user_id.partner_id.id],
            )
            record.message_subscribe(
                [
                    record.employee_id.user_id.partner_id.id,
                    record.staff_id.user_id.partner_id.id,
                ]
            )

    def action_cancel(self):
        for record in self:
            if not record.type_id:
                raise UserError("Захиалгын төрөлийг сонгох шаардлагатай.")
            if not record._check_pending_activities():
                raise UserError("Бүх ажилбар хаагдсан байх шаардлагатай.")
            record.write(
                {
                    "state": "cancelled",
                    "staff_id": self.env["hr.employee"]
                    .search([("user_id", "=", self.env.uid)], limit=1)
                    .id,
                    "done_date": datetime.now(),
                }
            )
            record.message_post(
                body="Захиалгыг цуцаллаа.",
                partner_ids=[record.employee_id.user_id.partner_id.id],
            )
            record.message_subscribe(
                [
                    record.employee_id.user_id.partner_id.id,
                    record.staff_id.user_id.partner_id.id,
                ]
            )

    def check_overdue_activities(self):
        manager_group = self.env.ref("ttt_helpdesk.group_manager")
        managers = self.env["res.users"].search([("groups_id", "in", manager_group.id)])
        manager_partner_ids = managers.mapped("partner_id.id")
        overdue_activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", "helpdesk.ticket"),
                ("date_deadline", "<", datetime.now() - timedelta(hours=24)),
                ("user_id", "!=", False),
                ("state", "=", "overdue"),
            ]
        )
        for activity in overdue_activities:
            ticket = self.env["helpdesk.ticket"].browse(activity.res_id)
            if ticket.staff_id:
                message = f'{ticket.staff_id.name}-ны хариуцсан "{ticket.name}" захиалгыг шийдвэрлэх ажилбар хоцрогдолтой байна.'
                ticket.message_post(
                    body=message,
                    message_type="notification",
                    subtype_xmlid="mail.mt_comment",
                    partner_ids=manager_partner_ids,
                )
        sent_tickets = self.search(
            [
                ("state", "=", "sent"),
                ("staff_id", "=", False),
                ("sent_date", "<", datetime.now() - timedelta(hours=12)),
            ]
        )
        for ticket in sent_tickets:
            message = f"'{ticket.name}' захиалга хариуцагч томилогдоогүй удаж байна."
            ticket.message_post(
                body=message,
                message_type="notification",
                subtype_xmlid="mail.mt_comment",
                partner_ids=manager_partner_ids,
            )
