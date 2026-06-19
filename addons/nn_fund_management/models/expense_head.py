"""Expense head model."""

from odoo import fields, models


class ExpenseHead(models.Model):
    """Represents a non-project spending category for fund allocation."""

    _name = "nn.expense.head"
    _description = "Expense Head"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
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
    active = fields.Boolean(default=True)
    description = fields.Text()
    total_allocated_fund = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Total approved fund allocations assigned to this expense head.",
    )
    available_fund = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Amount currently available for requisitions or transfers.",
    )
    requisition_hold = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Amount held by submitted requisitions pending approval.",
    )
    transfer_hold = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Amount held by submitted transfers pending approval.",
    )
    approved_unspent_amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Approved requisition amount that remains billable and unspent.",
    )
    total_spent_amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Amount spent through posted bills linked to this expense head.",
    )
    incoming_transfer_amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Total approved incoming transfers received by this expense head.",
    )
    outgoing_transfer_amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Total approved outgoing transfers sent from this expense head.",
    )

    _sql_constraints = [
        (
            "expense_head_code_company_uniq",
            "unique(code, company_id)",
            "The expense head code must be unique per company.",
        ),
    ]
