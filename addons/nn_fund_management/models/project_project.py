"""Project extension for fund tracking placeholders."""

from odoo import api, fields, models


class ProjectProject(models.Model):
    """Extends projects with readonly fund balance placeholders."""

    _inherit = "project.project"

    fund_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
        string="Fund Currency",
    )
    total_allocated_fund = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Total approved fund allocations assigned to this project.",
    )
    available_fund = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount currently available for requisitions or transfers.",
    )
    requisition_hold = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount held by submitted requisitions pending approval.",
    )
    transfer_hold = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount held by submitted transfers pending approval.",
    )
    approved_unspent_amount = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Approved requisition amount that remains billable and unspent.",
    )
    total_spent_amount = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Amount spent through posted bills linked to this project.",
    )
    incoming_transfer_amount = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Total approved incoming transfers received by this project.",
    )
    outgoing_transfer_amount = fields.Monetary(
        currency_field="fund_currency_id",
        compute="_compute_fund_balance_fields",
        store=True,
        readonly=True,
        help="Total approved outgoing transfers sent from this project.",
    )
    allocation_ids = fields.One2many(
        comodel_name="nn.fund.allocation",
        inverse_name="project_id",
        string="Fund Allocations",
    )
    requisition_ids = fields.One2many(
        comodel_name="nn.fund.requisition",
        inverse_name="project_id",
        string="Fund Requisitions",
    )
    bill_ids = fields.One2many(
        comodel_name="nn.fund.bill",
        inverse_name="project_id",
        string="Fund Bills",
    )
    source_transfer_ids = fields.One2many(
        comodel_name="nn.fund.transfer",
        inverse_name="source_project_id",
        string="Outgoing Fund Transfers",
    )
    destination_transfer_ids = fields.One2many(
        comodel_name="nn.fund.transfer",
        inverse_name="destination_project_id",
        string="Incoming Fund Transfers",
    )

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
        for project in self:
            approved_allocations = project.allocation_ids.filtered(lambda allocation: allocation.state == "approved")
            requisition_holds = project.requisition_ids.filtered(
                lambda requisition: requisition.state in ("submitted", "gm_approval", "finance_approval", "md_approval")
            )
            approved_requisitions = project.requisition_ids.filtered(lambda requisition: requisition.state == "approved")
            total_allocated = sum(approved_allocations.mapped("amount"))
            requisition_hold = sum(requisition_holds.mapped("amount"))
            approved_unspent = sum(approved_requisitions.mapped("remaining_billable_amount"))
            posted_bills = project.bill_ids.filtered(lambda bill: bill.state == "posted")
            total_spent = sum(posted_bills.mapped("amount"))
            pending_source_transfers = project.source_transfer_ids.filtered(
                lambda transfer: transfer.state in ("submitted", "gm_approval", "finance_approval", "md_approval")
            )
            approved_source_transfers = project.source_transfer_ids.filtered(lambda transfer: transfer.state == "approved")
            approved_destination_transfers = project.destination_transfer_ids.filtered(
                lambda transfer: transfer.state == "approved"
            )
            transfer_hold = sum(pending_source_transfers.mapped("amount"))
            outgoing_transfer_amount = sum(approved_source_transfers.mapped("amount"))
            incoming_transfer_amount = sum(approved_destination_transfers.mapped("amount"))
            project.total_allocated_fund = total_allocated
            project.requisition_hold = requisition_hold
            project.transfer_hold = transfer_hold
            project.approved_unspent_amount = approved_unspent
            project.total_spent_amount = total_spent
            project.incoming_transfer_amount = incoming_transfer_amount
            project.outgoing_transfer_amount = outgoing_transfer_amount
            project.available_fund = (
                total_allocated
                + incoming_transfer_amount
                - outgoing_transfer_amount
                - requisition_hold
                - transfer_hold
                - approved_unspent
            )
