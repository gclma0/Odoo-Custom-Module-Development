"""Incoming fund model."""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class IncomingFund(models.Model):
    """Represents a fund receipt into a fund account."""

    _name = "nn.incoming.fund"
    _description = "Incoming Fund"
    _inherit = ["mail.thread", "mail.activity.mixin", "nn.fund.company.access.mixin"]
    _order = "date desc, id desc"
    _rec_name = "transaction_reference"

    fund_account_id = fields.Many2one(
        comodel_name="nn.fund.account",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="fund_account_id.currency_id",
        store=True,
        readonly=True,
    )
    transaction_reference = fields.Char(required=True, tracking=True)
    sender_source = fields.Char(string="Sender / Source", tracking=True)
    description = fields.Text()
    attachment = fields.Binary(attachment=True)
    attachment_filename = fields.Char()
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="fund_account_id.company_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        tracking=True,
    )
    confirmed_by = fields.Many2one(comodel_name="res.users", readonly=True, tracking=True)
    confirmed_date = fields.Datetime(readonly=True, tracking=True)

    _sql_constraints = [
        (
            "incoming_fund_reference_account_uniq",
            "unique(fund_account_id, transaction_reference)",
            "The transaction reference must be unique within the selected fund account.",
        ),
    ]

    @api.constrains("amount")
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Incoming fund amount must be greater than zero.")

    def action_confirm(self):
        finance_group = "nn_fund_management.group_finance_user"
        admin_group = "nn_fund_management.group_fund_administrator"
        if not (self.env.user.has_group(finance_group) or self.env.user.has_group(admin_group)):
            raise UserError("Only authorized finance users can confirm incoming funds.")

        self._check_company_access()

        for record in self:
            if record.state != "draft":
                raise UserError("Only draft incoming funds can be confirmed.")

        self.write(
            {
                "state": "confirmed",
                "confirmed_by": self.env.user.id,
                "confirmed_date": fields.Datetime.now(),
            }
        )

    def action_cancel(self):
        self._check_company_access()
        for record in self:
            if record.state != "draft":
                raise UserError("Only draft incoming funds can be cancelled.")
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self._check_company_access()
        for record in self:
            if record.state != "cancelled":
                raise UserError("Only cancelled incoming funds can be reset to draft.")
        self.write({"state": "draft", "confirmed_by": False, "confirmed_date": False})
