"""Project extension for fund tracking placeholders."""

from odoo import fields, models


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
        readonly=True,
        help="Total approved fund allocations assigned to this project.",
    )
    available_fund = fields.Monetary(
        currency_field="fund_currency_id",
        readonly=True,
        help="Amount currently available for requisitions or transfers.",
    )
    requisition_hold = fields.Monetary(
        currency_field="fund_currency_id",
        readonly=True,
        help="Amount held by submitted requisitions pending approval.",
    )
    transfer_hold = fields.Monetary(
        currency_field="fund_currency_id",
        readonly=True,
        help="Amount held by submitted transfers pending approval.",
    )
    approved_unspent_amount = fields.Monetary(
        currency_field="fund_currency_id",
        readonly=True,
        help="Approved requisition amount that remains billable and unspent.",
    )
    total_spent_amount = fields.Monetary(
        currency_field="fund_currency_id",
        readonly=True,
        help="Amount spent through posted bills linked to this project.",
    )
    incoming_transfer_amount = fields.Monetary(
        currency_field="fund_currency_id",
        readonly=True,
        help="Total approved incoming transfers received by this project.",
    )
    outgoing_transfer_amount = fields.Monetary(
        currency_field="fund_currency_id",
        readonly=True,
        help="Total approved outgoing transfers sent from this project.",
    )
