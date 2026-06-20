"""Fund bill model."""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FundBill(models.Model):
    """Represents a bill posted against an approved requisition."""

    _name = "nn.fund.bill"
    _description = "Fund Bill"
    _inherit = ["mail.thread", "mail.activity.mixin", "nn.fund.company.access.mixin"]
    _order = "bill_date desc, id desc"
    _rec_name = "bill_number"

    bill_number = fields.Char(readonly=True, copy=False, default="New", tracking=True)
    requisition_id = fields.Many2one(
        comodel_name="nn.fund.requisition",
        required=True,
        ondelete="restrict",
        tracking=True,
        domain="[('state', '=', 'approved')]",
    )
    project_id = fields.Many2one(comodel_name="project.project", tracking=True)
    expense_head_id = fields.Many2one(comodel_name="nn.expense.head", tracking=True)
    company_id = fields.Many2one(comodel_name="res.company", compute="_compute_company_currency", store=True, readonly=True)
    currency_id = fields.Many2one(comodel_name="res.currency", compute="_compute_company_currency", store=True, readonly=True)
    amount = fields.Monetary(required=True, tracking=True)
    bill_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    vendor_name = fields.Char(tracking=True)
    description = fields.Text(required=True)
    attachment = fields.Binary(attachment=True)
    attachment_filename = fields.Char()
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        tracking=True,
    )
    posted_by = fields.Many2one(comodel_name="res.users", readonly=True, tracking=True)
    posted_date = fields.Datetime(readonly=True, tracking=True)
    cancelled_by = fields.Many2one(comodel_name="res.users", readonly=True, tracking=True)
    cancelled_date = fields.Datetime(readonly=True, tracking=True)

    @api.depends("requisition_id")
    def _compute_company_currency(self):
        for record in self:
            record.company_id = record.requisition_id.company_id
            record.currency_id = record.requisition_id.currency_id

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        for record in self:
            record.project_id = record.requisition_id.project_id
            record.expense_head_id = record.requisition_id.expense_head_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("bill_number", "New") == "New":
                vals["bill_number"] = self.env["ir.sequence"].sudo().next_by_code("nn.fund.bill") or "New"
        return super().create(vals_list)

    @api.constrains("amount")
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Bill amount must be greater than zero.")

    @api.constrains("project_id", "expense_head_id")
    def _check_single_target(self):
        for record in self:
            if bool(record.project_id) == bool(record.expense_head_id):
                raise ValidationError("Select either a project or an expense head for the bill, but not both.")

    @api.constrains("requisition_id", "project_id", "expense_head_id")
    def _check_matches_requisition_target(self):
        for record in self:
            if not record.requisition_id:
                continue
            if record.requisition_id.project_id and record.project_id != record.requisition_id.project_id:
                raise ValidationError("The bill must use the same project as the selected requisition.")
            if record.requisition_id.expense_head_id and record.expense_head_id != record.requisition_id.expense_head_id:
                raise ValidationError("The bill must use the same expense head as the selected requisition.")

    def _check_can_post(self):
        for record in self:
            if record.requisition_id.state != "approved":
                raise UserError("Only approved requisitions can be used for bills.")
            if record.amount > record.requisition_id.remaining_billable_amount:
                raise UserError("The bill amount cannot exceed the requisition's remaining billable amount.")

    def _create_audit_entry(self, decision, old_state, new_state):
        self.ensure_one()
        self.env["nn.approval.history"].sudo().create(
            {
                "request_type": "bill",
                "res_model": self._name,
                "res_id": self.id,
                "reference": self.bill_number,
                "reference_document": self.bill_number,
                "approval_level": "finance",
                "decision": decision,
                "action_by": self.env.user.id,
                "record_creator_id": self.create_uid.id,
                "submitted_by_id": self.create_uid.id,
                "comment": self.description,
                "old_state": old_state,
                "new_state": new_state,
                "amount": self.amount,
                "currency_id": self.currency_id.id,
                "company_id": self.company_id.id,
                "project_id": self.project_id.id,
                "expense_head_id": self.expense_head_id.id,
                "requisition_id": self.requisition_id.id,
                "bill_id": self.id,
            }
        )

    def action_post(self):
        finance_group = "nn_fund_management.group_finance_user"
        admin_group = "nn_fund_management.group_fund_administrator"
        if not (self.env.user.has_group(finance_group) or self.env.user.has_group(admin_group)):
            raise UserError("Only authorized finance users can post fund bills.")

        self._check_company_access()

        for record in self:
            if record.state != "draft":
                raise UserError("Only draft bills can be posted.")
            record._check_can_post()
            old_state = record.state
            record.write(
                {
                    "state": "posted",
                    "posted_by": self.env.user.id,
                    "posted_date": fields.Datetime.now(),
                }
            )
            record._create_audit_entry("posted", old_state, "posted")

    def action_cancel(self):
        finance_group = "nn_fund_management.group_finance_user"
        admin_group = "nn_fund_management.group_fund_administrator"
        if not (self.env.user.has_group(finance_group) or self.env.user.has_group(admin_group)):
            raise UserError("Only authorized finance users can cancel fund bills.")

        self._check_company_access()

        for record in self:
            if record.state != "posted":
                raise UserError("Only posted bills can be cancelled.")
            old_state = record.state
            record.write(
                {
                    "state": "cancelled",
                    "cancelled_by": self.env.user.id,
                    "cancelled_date": fields.Datetime.now(),
                }
            )
            record._create_audit_entry("cancelled", old_state, "cancelled")

    def action_reset_to_draft(self):
        self._check_company_access()
        for record in self:
            if record.state != "cancelled":
                raise UserError("Only cancelled bills can be reset to draft.")
            record.write(
                {
                    "state": "draft",
                    "cancelled_by": False,
                    "cancelled_date": False,
                    "posted_by": False,
                    "posted_date": False,
                }
            )

    def unlink(self):
        for record in self:
            if record.state != "draft":
                raise UserError("Only draft fund bills can be deleted. Posted or cancelled records must remain in history.")
        return super().unlink()
