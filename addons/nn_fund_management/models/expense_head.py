"""Expense head model."""

from odoo import api, fields, models


class ExpenseHead(models.Model):
    """Represents a non-project spending category for fund allocation."""

    _name = "nn.expense.head"
    _description = "Expense Head"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    expense_category = fields.Char(
        string="Expense Category",
        tracking=True,
        help="Optional category used by approval rules and reporting.",
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
    active = fields.Boolean(default=True)
    description = fields.Text()
    allocation_ids = fields.One2many(
        comodel_name="nn.fund.allocation",
        inverse_name="expense_head_id",
        string="Fund Allocations",
    )
    requisition_ids = fields.One2many(
        comodel_name="nn.fund.requisition",
        inverse_name="expense_head_id",
        string="Fund Requisitions",
    )
    bill_ids = fields.One2many(
        comodel_name="nn.fund.bill",
        inverse_name="expense_head_id",
        string="Fund Bills",
    )
    source_transfer_ids = fields.One2many(
        comodel_name="nn.fund.transfer",
        inverse_name="source_expense_head_id",
        string="Outgoing Fund Transfers",
    )
    destination_transfer_ids = fields.One2many(
        comodel_name="nn.fund.transfer",
        inverse_name="destination_expense_head_id",
        string="Incoming Fund Transfers",
    )
    total_allocated_fund = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Total approved fund allocations assigned to this expense head.",
    )
    available_fund = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount currently available for requisitions or transfers.",
    )
    requisition_hold = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount held by submitted requisitions pending approval.",
    )
    transfer_hold = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount held by submitted transfers pending approval.",
    )
    approved_unspent_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Approved requisition amount that remains billable and unspent.",
    )
    total_spent_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount spent through posted bills linked to this expense head.",
    )
    incoming_transfer_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Total approved incoming transfers received by this expense head.",
    )
    outgoing_transfer_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
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

    @api.depends(
        "allocation_ids.amount",
        "allocation_ids.state",
        "requisition_ids.amount",
        "requisition_ids.state",
        "requisition_ids.remaining_billable_amount",
        "bill_ids.amount",
        "bill_ids.state",
        "source_transfer_ids.amount",
        "source_transfer_ids.state",
        "destination_transfer_ids.amount",
        "destination_transfer_ids.state",
    )
    def _compute_fund_balance_fields(self):
        for expense_head in self:
            approved_allocations = expense_head.allocation_ids.filtered(lambda allocation: allocation.state == "approved")
            requisition_holds = expense_head.requisition_ids.filtered(
                lambda requisition: requisition.state in ("submitted", "gm_approval", "finance_approval", "md_approval")
            )
            approved_requisitions = expense_head.requisition_ids.filtered(lambda requisition: requisition.state == "approved")
            total_allocated = sum(approved_allocations.mapped("amount"))
            requisition_hold = sum(requisition_holds.mapped("amount"))
            approved_unspent = sum(approved_requisitions.mapped("remaining_billable_amount"))
            posted_bills = expense_head.bill_ids.filtered(lambda bill: bill.state == "posted")
            total_spent = sum(posted_bills.mapped("amount"))
            pending_source_transfers = expense_head.source_transfer_ids.filtered(
                lambda transfer: transfer.state in ("submitted", "gm_approval", "finance_approval", "md_approval")
            )
            approved_source_transfers = expense_head.source_transfer_ids.filtered(lambda transfer: transfer.state == "approved")
            approved_destination_transfers = expense_head.destination_transfer_ids.filtered(
                lambda transfer: transfer.state == "approved"
            )
            transfer_hold = sum(pending_source_transfers.mapped("amount"))
            outgoing_transfer_amount = sum(approved_source_transfers.mapped("amount"))
            incoming_transfer_amount = sum(approved_destination_transfers.mapped("amount"))
            expense_head.total_allocated_fund = total_allocated
            expense_head.requisition_hold = requisition_hold
            expense_head.transfer_hold = transfer_hold
            expense_head.approved_unspent_amount = approved_unspent
            expense_head.total_spent_amount = total_spent
            expense_head.incoming_transfer_amount = incoming_transfer_amount
            expense_head.outgoing_transfer_amount = outgoing_transfer_amount
            expense_head.available_fund = (
                total_allocated
                + incoming_transfer_amount
                - outgoing_transfer_amount
                - requisition_hold
                - transfer_hold
                - approved_unspent
            )
