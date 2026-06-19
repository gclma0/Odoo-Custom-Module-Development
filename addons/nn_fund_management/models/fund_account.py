"""Fund account model."""

from odoo import api, fields, models


class FundAccount(models.Model):
    """Represents a source account that receives and distributes funds."""

    _name = "nn.fund.account"
    _description = "Fund Account"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    account_type = fields.Selection(
        selection=[
            ("bank", "Bank"),
            ("cash", "Cash"),
            ("other", "Other"),
        ],
        required=True,
        default="bank",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    incoming_fund_ids = fields.One2many(
        comodel_name="nn.incoming.fund",
        inverse_name="fund_account_id",
        string="Incoming Funds",
    )
    active = fields.Boolean(default=True)
    description = fields.Text()
    total_received = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_balance_fields",
        store=True,
        readonly=True,
        help="Total confirmed incoming funds received into this account.",
    )
    available_unassigned_balance = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_balance_fields",
        store=True,
        readonly=True,
        help="Amount currently available for new fund allocations.",
    )
    amount_on_hold = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_balance_fields",
        store=True,
        readonly=True,
        help="Amount temporarily reserved by pending transactions.",
    )
    total_assigned_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_balance_fields",
        store=True,
        readonly=True,
        help="Amount approved and assigned out of this account.",
    )

    _sql_constraints = [
        (
            "fund_account_code_company_uniq",
            "unique(code, company_id)",
            "The fund account code must be unique per company.",
        ),
    ]

    @api.depends("incoming_fund_ids.amount", "incoming_fund_ids.state")
    def _compute_balance_fields(self):
        for account in self:
            confirmed_incoming = account.incoming_fund_ids.filtered(lambda fund: fund.state == "confirmed")
            total_received = sum(confirmed_incoming.mapped("amount"))
            account.total_received = total_received
            account.available_unassigned_balance = total_received
            account.amount_on_hold = 0.0
            account.total_assigned_amount = 0.0
