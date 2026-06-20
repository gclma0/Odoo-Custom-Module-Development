"""Fund allocation model."""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FundAllocation(models.Model):
    """Represents an allocation request from a fund account to a project or expense head."""

    _name = "nn.fund.allocation"
    _description = "Fund Allocation"
    _inherit = ["mail.thread", "mail.activity.mixin", "nn.fund.company.access.mixin"]
    _order = "request_date desc, id desc"
    _rec_name = "request_number"

    request_number = fields.Char(readonly=True, copy=False, default="New", tracking=True)
    fund_account_id = fields.Many2one(
        comodel_name="nn.fund.account",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="fund_account_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="fund_account_id.currency_id",
        store=True,
        readonly=True,
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        ondelete="restrict",
        tracking=True,
    )
    expense_head_id = fields.Many2one(
        comodel_name="nn.expense.head",
        ondelete="restrict",
        tracking=True,
    )
    amount = fields.Monetary(required=True, tracking=True)
    purpose = fields.Text(required=True)
    request_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    requested_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    attachment = fields.Binary(attachment=True)
    attachment_filename = fields.Char()
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("gm_approval", "GM Approval"),
            ("finance_approval", "Finance Approval"),
            ("md_approval", "MD Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("reversed", "Reversed"),
        ],
        required=True,
        default="draft",
        tracking=True,
    )
    approval_config_id = fields.Many2one(comodel_name="nn.approval.config", readonly=True)
    current_approval_line_id = fields.Many2one(comodel_name="nn.approval.config.line", readonly=True)
    approval_history_ids = fields.One2many(
        comodel_name="nn.approval.history",
        inverse_name="allocation_id",
        string="Approval History",
        readonly=True,
    )
    approval_comment = fields.Text(help="Optional comment used for the next approval or rejection action.")
    target_name = fields.Char(compute="_compute_target_name")

    @api.depends("project_id", "expense_head_id")
    def _compute_target_name(self):
        for record in self:
            record.target_name = record.project_id.display_name or record.expense_head_id.display_name or False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("request_number", "New") == "New":
                vals["request_number"] = self.env["ir.sequence"].sudo().next_by_code("nn.fund.allocation") or "New"
        return super().create(vals_list)

    @api.constrains("project_id", "expense_head_id")
    def _check_single_target(self):
        for record in self:
            if bool(record.project_id) == bool(record.expense_head_id):
                raise ValidationError("Select either a project or an expense head for the allocation, but not both.")

    @api.constrains("project_id", "expense_head_id", "company_id")
    def _check_target_company(self):
        for record in self:
            if record.project_id and record.project_id.company_id and record.project_id.company_id != record.company_id:
                raise ValidationError("The selected project must belong to the same company as the fund account.")
            if record.expense_head_id and record.expense_head_id.company_id and record.expense_head_id.company_id != record.company_id:
                raise ValidationError("The selected expense head must belong to the same company as the fund account.")

    @api.constrains("amount")
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Allocation amount must be greater than zero.")

    def _get_pending_lines(self):
        self.ensure_one()
        if not self.approval_config_id:
            return self.env["nn.approval.config.line"]
        return self.sudo().approval_config_id.line_ids.sorted(key=lambda line: (line.sequence, line.id))

    def _get_next_line(self):
        self.ensure_one()
        lines = self._get_pending_lines()
        if not self.current_approval_line_id:
            return lines[:1]
        next_lines = lines.filtered(lambda line: line.sequence > self.current_approval_line_id.sequence)
        return next_lines[:1]

    def _map_state_from_line(self, line):
        mapping = {
            "gm": "gm_approval",
            "finance": "finance_approval",
            "md": "md_approval",
        }
        return mapping.get(line.approval_level, "submitted")

    def _check_current_approver(self):
        self.ensure_one()
        line = self.sudo().current_approval_line_id
        if not line:
            raise UserError("There is no current approval step for this allocation.")
        if self.requested_by == self.env.user and not self.env.user.has_group("nn_fund_management.group_fund_administrator"):
            raise UserError("You cannot approve your own allocation request.")

        allowed = False
        line_sudo = line.sudo()
        if line_sudo.approver_user_id and line_sudo.approver_user_id.id == self.env.user.id:
            allowed = True
        if line_sudo.approver_group_id and self.env.user.id in line_sudo.approver_group_id.users.ids:
            allowed = True
        if not allowed:
            raise UserError("Only the current configured approver can perform this action.")

    def _create_history_entry(self, decision, approval_level, old_state, new_state, comment=False):
        self.ensure_one()
        self.env["nn.approval.history"].sudo().create(
            {
                "request_type": "allocation",
                "res_model": self._name,
                "res_id": self.id,
                "reference": self.request_number,
                "reference_document": self.request_number,
                "approval_level": approval_level,
                "decision": decision,
                "action_by": self.env.user.id,
                "record_creator_id": self.create_uid.id,
                "submitted_by_id": self.requested_by.id,
                "comment": comment or self.approval_comment,
                "old_state": old_state,
                "new_state": new_state,
                "amount": self.amount,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
                "fund_account_id": self.fund_account_id.id,
                "project_id": self.project_id.id,
                "expense_head_id": self.expense_head_id.id,
                "allocation_id": self.id,
            }
        )

    def _schedule_activity_for_line(self, line, note):
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        line_sudo = line.sudo()
        users = line_sudo.approver_user_id or line_sudo.approver_group_id.users
        for user in users:
            self.activity_schedule(activity_type_id=activity_type.id, user_id=user.id, note=note)

    def _schedule_requester_activity(self, note):
        self.ensure_one()
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        self.activity_schedule(activity_type_id=activity_type.id, user_id=self.requested_by.id, note=note)

    def _get_matching_config(self):
        self.ensure_one()
        config = self.env["nn.approval.config"].get_matching_config(
            "allocation", self.company_id, self.amount, project=self.project_id, expense_head=self.expense_head_id
        )
        if not config:
            raise UserError("No active approval configuration matches this allocation amount and company.")
        lines = config.line_ids.sorted(key=lambda line: (line.sequence, line.id))
        if not lines:
            raise UserError("The selected approval configuration has no approval steps.")
        levels = lines.mapped("approval_level")
        if "gm" not in levels or "md" not in levels:
            raise UserError("Allocation approval configuration must include both GM and MD approval levels.")
        return config

    def action_submit(self):
        self._check_company_access()
        for record in self:
            if record.state != "draft":
                raise UserError("Only draft allocations can be submitted.")
            if record.amount > record.fund_account_id.available_unassigned_balance:
                raise UserError("The requested amount exceeds the fund account's available unassigned balance.")

            config = record._get_matching_config()
            first_line = config.line_ids.sorted(key=lambda line: (line.sequence, line.id))[:1]
            new_state = "submitted"
            old_state = record.state
            record.write(
                {
                    "approval_config_id": config.id,
                    "current_approval_line_id": first_line.id,
                    "state": new_state,
                }
            )
            record._create_history_entry("submitted", first_line.approval_level, old_state, new_state)
            record._schedule_activity_for_line(first_line, "Fund allocation submitted and waiting for your approval.")

    def action_approve(self):
        self._check_company_access()
        for record in self:
            if record.state not in ("submitted", "gm_approval", "finance_approval", "md_approval"):
                raise UserError("Only allocations pending approval can be approved.")
            record._check_current_approver()

            current_line = record.sudo().current_approval_line_id
            old_state = record.state
            next_line = record._get_next_line()
            if next_line:
                new_state = record._map_state_from_line(next_line)
                record.write({"current_approval_line_id": next_line.id, "state": new_state})
                record._schedule_activity_for_line(next_line, "Fund allocation moved to your approval step.")
            else:
                new_state = "approved"
                record.write({"current_approval_line_id": False, "state": new_state})
                record._schedule_requester_activity("Your fund allocation has been approved.")
            record._create_history_entry("approved", current_line.approval_level, old_state, new_state)

    def action_reject(self):
        self._check_company_access()
        for record in self:
            if record.state not in ("submitted", "gm_approval", "finance_approval", "md_approval"):
                raise UserError("Only allocations pending approval can be rejected.")
            record._check_current_approver()
            old_state = record.state
            approval_level = record.sudo().current_approval_line_id.approval_level
            record.write({"state": "rejected", "current_approval_line_id": False})
            record._create_history_entry("rejected", approval_level, old_state, "rejected")
            record._schedule_requester_activity("Your fund allocation has been rejected.")

    def action_cancel(self):
        self._check_company_access()
        for record in self:
            if record.state == "approved":
                raise UserError("Approved allocations cannot be cancelled directly.")
            if record.state == "cancelled":
                continue
            if record.requested_by != self.env.user and not self.env.user.has_group("nn_fund_management.group_fund_administrator"):
                raise UserError("Only the requester or a fund administrator can cancel this allocation.")
            old_state = record.state
            current_line = record.sudo().current_approval_line_id
            approval_level = current_line.approval_level if current_line else "gm"
            record.write({"state": "cancelled", "current_approval_line_id": False})
            record._create_history_entry("cancelled", approval_level, old_state, "cancelled")

    def action_reset_to_draft(self):
        self._check_company_access()
        for record in self:
            if record.state not in ("rejected", "cancelled"):
                raise UserError("Only rejected or cancelled allocations can be reset to draft.")
            record.write(
                {
                    "state": "draft",
                    "approval_config_id": False,
                    "current_approval_line_id": False,
                    "approval_comment": False,
                }
            )

    def action_reverse(self):
        finance_group = "nn_fund_management.group_finance_user"
        admin_group = "nn_fund_management.group_fund_administrator"
        if not (self.env.user.has_group(finance_group) or self.env.user.has_group(admin_group)):
            raise UserError("Only authorized finance users can reverse approved allocations.")

        self._check_company_access()
        for record in self:
            if record.state != "approved":
                raise UserError("Only approved allocations can be reversed.")
            target_available = record.project_id.available_fund if record.project_id else record.expense_head_id.available_fund
            if target_available < record.amount:
                raise UserError("This allocation cannot be reversed because the target no longer has enough free available balance.")
            old_state = record.state
            record.write({"state": "reversed"})
            record._create_history_entry("reversed", "finance", old_state, "reversed")

    def unlink(self):
        for record in self:
            if record.state != "draft":
                raise UserError("Only draft fund allocations can be deleted. Submitted or completed records must remain in history.")
        return super().unlink()
