"""Fund transfer model."""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FundTransfer(models.Model):
    """Transfers allocated available funds between projects and expense heads."""

    _name = "nn.fund.transfer"
    _description = "Fund Transfer"
    _inherit = ["mail.thread", "mail.activity.mixin", "nn.fund.company.access.mixin"]
    _order = "request_date desc, id desc"
    _rec_name = "transfer_number"

    transfer_number = fields.Char(readonly=True, copy=False, default="New", tracking=True)
    source_project_id = fields.Many2one(comodel_name="project.project", ondelete="restrict", tracking=True)
    source_expense_head_id = fields.Many2one(comodel_name="nn.expense.head", ondelete="restrict", tracking=True)
    destination_project_id = fields.Many2one(comodel_name="project.project", ondelete="restrict", tracking=True)
    destination_expense_head_id = fields.Many2one(comodel_name="nn.expense.head", ondelete="restrict", tracking=True)
    company_id = fields.Many2one(comodel_name="res.company", compute="_compute_company_currency", store=True, readonly=True)
    currency_id = fields.Many2one(comodel_name="res.currency", compute="_compute_company_currency", store=True, readonly=True)
    amount = fields.Monetary(required=True, tracking=True)
    reason = fields.Text(required=True)
    requested_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    request_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
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
        ],
        required=True,
        default="draft",
        tracking=True,
    )
    approval_config_id = fields.Many2one(comodel_name="nn.approval.config", readonly=True)
    current_approval_line_id = fields.Many2one(comodel_name="nn.approval.config.line", readonly=True)
    approval_history_ids = fields.One2many(
        comodel_name="nn.approval.history",
        inverse_name="transfer_id",
        string="Approval History",
        readonly=True,
    )
    approval_comment = fields.Text(help="Optional comment used for the next approval or rejection action.")
    source_name = fields.Char(compute="_compute_display_names")
    destination_name = fields.Char(compute="_compute_display_names")

    @api.depends(
        "source_project_id",
        "source_expense_head_id",
        "destination_project_id",
        "destination_expense_head_id",
    )
    def _compute_company_currency(self):
        for record in self:
            source_company = record.source_project_id.company_id or record.source_expense_head_id.company_id
            destination_company = record.destination_project_id.company_id or record.destination_expense_head_id.company_id
            company = source_company or destination_company
            record.company_id = company
            record.currency_id = company.currency_id if company else False

    @api.depends(
        "source_project_id",
        "source_expense_head_id",
        "destination_project_id",
        "destination_expense_head_id",
    )
    def _compute_display_names(self):
        for record in self:
            record.source_name = record.source_project_id.display_name or record.source_expense_head_id.display_name or False
            record.destination_name = (
                record.destination_project_id.display_name or record.destination_expense_head_id.display_name or False
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("transfer_number", "New") == "New":
                vals["transfer_number"] = self.env["ir.sequence"].next_by_code("nn.fund.transfer") or "New"
        return super().create(vals_list)

    @api.constrains("source_project_id", "source_expense_head_id")
    def _check_single_source(self):
        for record in self:
            if bool(record.source_project_id) == bool(record.source_expense_head_id):
                raise ValidationError("Select either a source project or a source expense head, but not both.")

    @api.constrains("destination_project_id", "destination_expense_head_id")
    def _check_single_destination(self):
        for record in self:
            if bool(record.destination_project_id) == bool(record.destination_expense_head_id):
                raise ValidationError("Select either a destination project or a destination expense head, but not both.")

    @api.constrains(
        "source_project_id",
        "source_expense_head_id",
        "destination_project_id",
        "destination_expense_head_id",
        "company_id",
    )
    def _check_company_and_difference(self):
        for record in self:
            source_company = record.source_project_id.company_id or record.source_expense_head_id.company_id
            destination_company = record.destination_project_id.company_id or record.destination_expense_head_id.company_id
            if source_company and destination_company and source_company != destination_company:
                raise ValidationError("Source and destination must belong to the same company.")
            if source_company and record.company_id and source_company != record.company_id:
                raise ValidationError("The source must belong to the same company as the transfer.")
            if destination_company and record.company_id and destination_company != record.company_id:
                raise ValidationError("The destination must belong to the same company as the transfer.")

            same_source_dest = (
                record.source_project_id
                and record.destination_project_id
                and record.source_project_id == record.destination_project_id
            ) or (
                record.source_expense_head_id
                and record.destination_expense_head_id
                and record.source_expense_head_id == record.destination_expense_head_id
            )
            if same_source_dest:
                raise ValidationError("Source and destination cannot be the same.")

    @api.constrains("amount")
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Transfer amount must be greater than zero.")

    def _get_source_available_balance(self):
        self.ensure_one()
        if self.source_project_id:
            return self.source_project_id.available_fund
        return self.source_expense_head_id.available_fund

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
            raise UserError("There is no current approval step for this transfer.")
        if self.requested_by == self.env.user and not self.env.user.has_group("nn_fund_management.group_fund_administrator"):
            raise UserError("You cannot approve your own transfer request.")

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
                "request_type": "transfer",
                "res_model": self._name,
                "res_id": self.id,
                "reference": self.transfer_number,
                "approval_level": approval_level,
                "decision": decision,
                "action_by": self.env.user.id,
                "comment": comment or self.approval_comment,
                "old_state": old_state,
                "new_state": new_state,
                "amount": self.amount,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
                "project_id": self.source_project_id.id or self.destination_project_id.id,
                "expense_head_id": self.source_expense_head_id.id or self.destination_expense_head_id.id,
                "transfer_id": self.id,
            }
        )

    def _get_matching_config(self):
        self.ensure_one()
        config = self.env["nn.approval.config"].get_matching_config("transfer", self.company_id, self.amount)
        if not config:
            raise UserError("No active approval configuration matches this transfer amount and company.")
        lines = config.line_ids.sorted(key=lambda line: (line.sequence, line.id))
        if not lines:
            raise UserError("The selected approval configuration has no approval steps.")
        levels = lines.mapped("approval_level")
        if "gm" not in levels or "md" not in levels:
            raise UserError("Transfer approval configuration must include both GM and MD approval levels.")
        return config

    def action_submit(self):
        self._check_company_access()
        for record in self:
            if record.state != "draft":
                raise UserError("Only draft transfers can be submitted.")
            if record.amount > record._get_source_available_balance():
                raise UserError("The transfer amount exceeds the source's available balance.")
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
                raise UserError("Only transfers pending approval can be approved.")
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
                raise UserError("Only transfers pending approval can be rejected.")
            record._check_current_approver()
            old_state = record.state
            approval_level = record.current_approval_line_id.approval_level
            record.write({"state": "rejected", "current_approval_line_id": False})
            record._create_history_entry("rejected", approval_level, old_state, "rejected")

    def action_cancel(self):
        self._check_company_access()
        for record in self:
            if record.state == "approved":
                raise UserError("Approved transfers cannot be cancelled directly.")
            if record.state == "cancelled":
                continue
            if record.requested_by != self.env.user and not self.env.user.has_group("nn_fund_management.group_fund_administrator"):
                raise UserError("Only the requester or a fund administrator can cancel this transfer.")
            old_state = record.state
            approval_level = record.current_approval_line_id.approval_level if record.current_approval_line_id else "gm"
            record.write({"state": "cancelled", "current_approval_line_id": False})
            record._create_history_entry("cancelled", approval_level, old_state, "cancelled")

    def action_reset_to_draft(self):
        self._check_company_access()
        for record in self:
            if record.state not in ("rejected", "cancelled"):
                raise UserError("Only rejected or cancelled transfers can be reset to draft.")
            record.write(
                {
                    "state": "draft",
                    "approval_config_id": False,
                    "current_approval_line_id": False,
                    "approval_comment": False,
                }
            )
