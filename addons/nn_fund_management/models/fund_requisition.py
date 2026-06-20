"""Fund requisition model."""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FundRequisition(models.Model):
    """Reserves allocated project or expense funds for later billing."""

    _name = "nn.fund.requisition"
    _description = "Fund Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin", "nn.fund.company.access.mixin"]
    _order = "request_date desc, id desc"
    _rec_name = "requisition_number"

    requisition_number = fields.Char(readonly=True, copy=False, default="New", tracking=True)
    project_id = fields.Many2one(comodel_name="project.project", ondelete="restrict", tracking=True)
    expense_head_id = fields.Many2one(comodel_name="nn.expense.head", ondelete="restrict", tracking=True)
    company_id = fields.Many2one(comodel_name="res.company", compute="_compute_company_currency", store=True, readonly=True)
    currency_id = fields.Many2one(comodel_name="res.currency", compute="_compute_company_currency", store=True, readonly=True)
    amount = fields.Monetary(required=True, tracking=True)
    purpose = fields.Text(required=True)
    request_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    required_date = fields.Date(required=True, tracking=True)
    requested_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    supporting_attachment = fields.Binary(attachment=True)
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
            ("closed", "Closed"),
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
        inverse_name="requisition_id",
        string="Approval History",
        readonly=True,
    )
    bill_ids = fields.One2many(
        comodel_name="nn.fund.bill",
        inverse_name="requisition_id",
        string="Bills",
        readonly=True,
    )
    approval_comment = fields.Text(help="Optional comment used for the next approval or rejection action.")
    released_amount = fields.Monetary(default=0.0, readonly=True, tracking=True)
    spent_amount = fields.Monetary(default=0.0, readonly=True, tracking=True)
    remaining_billable_amount = fields.Monetary(
        compute="_compute_remaining_billable_amount",
        store=True,
        readonly=True,
    )
    target_name = fields.Char(compute="_compute_target_name")

    @api.depends("project_id", "expense_head_id")
    def _compute_company_currency(self):
        for record in self:
            company = record.project_id.company_id or record.expense_head_id.company_id
            record.company_id = company
            record.currency_id = company.currency_id if company else False

    @api.depends("project_id", "expense_head_id")
    def _compute_target_name(self):
        for record in self:
            record.target_name = record.project_id.display_name or record.expense_head_id.display_name or False

    @api.depends("amount", "released_amount", "state", "bill_ids.amount", "bill_ids.state")
    def _compute_remaining_billable_amount(self):
        for record in self:
            posted_bills = record.bill_ids.filtered(lambda bill: bill.state == "posted")
            spent_amount = sum(posted_bills.mapped("amount"))
            record.spent_amount = spent_amount
            if record.state in ("approved", "closed"):
                record.remaining_billable_amount = max(record.amount - spent_amount - record.released_amount, 0.0)
            else:
                record.remaining_billable_amount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("requisition_number", "New") == "New":
                vals["requisition_number"] = self.env["ir.sequence"].next_by_code("nn.fund.requisition") or "New"
        return super().create(vals_list)

    @api.constrains("project_id", "expense_head_id")
    def _check_single_target(self):
        for record in self:
            if bool(record.project_id) == bool(record.expense_head_id):
                raise ValidationError("Select either a project or an expense head for the requisition, but not both.")

    @api.constrains("project_id", "expense_head_id", "company_id")
    def _check_target_company(self):
        for record in self:
            if record.project_id and record.project_id.company_id and record.project_id.company_id != record.company_id:
                raise ValidationError("The selected project must belong to the same company as the requisition.")
            if record.expense_head_id and record.expense_head_id.company_id and record.expense_head_id.company_id != record.company_id:
                raise ValidationError("The selected expense head must belong to the same company as the requisition.")

    @api.constrains("amount")
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Requisition amount must be greater than zero.")

    @api.constrains("required_date", "request_date")
    def _check_required_date(self):
        for record in self:
            if record.required_date and record.request_date and record.required_date < record.request_date:
                raise ValidationError("Required date cannot be earlier than request date.")

    def _get_available_balance(self):
        self.ensure_one()
        if self.project_id:
            return self.project_id.available_fund
        return self.expense_head_id.available_fund

    def _get_pending_lines(self):
        self.ensure_one()
        if not self.approval_config_id:
            return self.env["nn.approval.config.line"]
        return self.approval_config_id.line_ids.sorted(key=lambda line: (line.sequence, line.id))

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
        line = self.current_approval_line_id
        if not line:
            raise UserError("There is no current approval step for this requisition.")
        if self.requested_by == self.env.user and not self.env.user.has_group("nn_fund_management.group_fund_administrator"):
            raise UserError("You cannot approve your own requisition request.")
        allowed = False
        if line.approver_user_id and line.approver_user_id == self.env.user:
            allowed = True
        if line.approver_group_id and self.env.user in line.approver_group_id.users:
            allowed = True
        if not allowed:
            raise UserError("Only the current configured approver can perform this action.")

    def _create_history_entry(self, decision, approval_level, old_state, new_state, comment=False):
        self.ensure_one()
        self.env["nn.approval.history"].create(
            {
                "request_type": "requisition",
                "res_model": self._name,
                "res_id": self.id,
                "reference": self.requisition_number,
                "reference_document": self.requisition_number,
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
                "project_id": self.project_id.id,
                "expense_head_id": self.expense_head_id.id,
                "requisition_id": self.id,
            }
        )

    def _get_matching_config(self):
        self.ensure_one()
        config = self.env["nn.approval.config"].get_matching_config("requisition", self.company_id, self.amount)
        if not config:
            raise UserError("No active approval configuration matches this requisition amount and company.")
        lines = config.line_ids.sorted(key=lambda line: (line.sequence, line.id))
        if not lines:
            raise UserError("The selected approval configuration has no approval steps.")
        levels = lines.mapped("approval_level")
        if "gm" not in levels or "md" not in levels:
            raise UserError("Requisition approval configuration must include both GM and MD approval levels.")
        return config

    def action_submit(self):
        self._check_company_access()
        for record in self:
            if record.state != "draft":
                raise UserError("Only draft requisitions can be submitted.")
            if record.amount > record._get_available_balance():
                raise UserError("The requested amount exceeds the available balance of the selected project or expense head.")
            config = record._get_matching_config()
            first_line = config.line_ids.sorted(key=lambda line: (line.sequence, line.id))[:1]
            old_state = record.state
            record.write(
                {
                    "approval_config_id": config.id,
                    "current_approval_line_id": first_line.id,
                    "state": "submitted",
                }
            )
            record._create_history_entry("submitted", first_line.approval_level, old_state, "submitted")

    def action_approve(self):
        self._check_company_access()
        for record in self:
            if record.state not in ("submitted", "gm_approval", "finance_approval", "md_approval"):
                raise UserError("Only requisitions pending approval can be approved.")
            record._check_current_approver()
            current_line = record.current_approval_line_id
            old_state = record.state
            next_line = record._get_next_line()
            if next_line:
                new_state = record._map_state_from_line(next_line)
                record.write({"current_approval_line_id": next_line.id, "state": new_state})
            else:
                new_state = "approved"
                record.write({"current_approval_line_id": False, "state": new_state})
            record._create_history_entry("approved", current_line.approval_level, old_state, new_state)

    def action_reject(self):
        self._check_company_access()
        for record in self:
            if record.state not in ("submitted", "gm_approval", "finance_approval", "md_approval"):
                raise UserError("Only requisitions pending approval can be rejected.")
            record._check_current_approver()
            old_state = record.state
            approval_level = record.current_approval_line_id.approval_level
            record.write({"state": "rejected", "current_approval_line_id": False})
            record._create_history_entry("rejected", approval_level, old_state, "rejected")

    def action_cancel(self):
        self._check_company_access()
        for record in self:
            if record.state in ("approved", "closed"):
                raise UserError("Approved or closed requisitions cannot be cancelled directly.")
            if record.state == "cancelled":
                continue
            if record.requested_by != self.env.user and not self.env.user.has_group("nn_fund_management.group_fund_administrator"):
                raise UserError("Only the requester or a fund administrator can cancel this requisition.")
            old_state = record.state
            approval_level = record.current_approval_line_id.approval_level if record.current_approval_line_id else "gm"
            record.write({"state": "cancelled", "current_approval_line_id": False})
            record._create_history_entry("cancelled", approval_level, old_state, "cancelled")

    def action_close(self):
        self._check_company_access()
        for record in self:
            if record.state != "approved":
                raise UserError("Only approved requisitions can be closed.")
            old_state = record.state
            if record.remaining_billable_amount > 0:
                record.released_amount = record.released_amount + record.remaining_billable_amount
            record.write({"state": "closed"})
            record._create_history_entry("closed", "md", old_state, "closed", comment="Requisition closed and remaining amount released.")

    def action_reset_to_draft(self):
        self._check_company_access()
        for record in self:
            if record.state not in ("rejected", "cancelled"):
                raise UserError("Only rejected or cancelled requisitions can be reset to draft.")
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
            raise UserError("Only authorized finance users can reverse approved requisitions.")

        self._check_company_access()
        for record in self:
            if record.state != "approved":
                raise UserError("Only approved requisitions can be reversed.")
            if record.spent_amount > 0:
                raise UserError("A requisition with posted bills cannot be reversed.")
            if record.released_amount > 0:
                raise UserError("A requisition that has already released unused funds cannot be reversed.")
            old_state = record.state
            record.write({"state": "reversed"})
            record._create_history_entry("reversed", "finance", old_state, "reversed")
