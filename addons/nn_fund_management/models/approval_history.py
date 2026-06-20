"""Approval history model."""

from odoo import fields, models


class ApprovalHistory(models.Model):
    """Stores approval and rejection decisions for fund workflows."""

    _name = "nn.approval.history"
    _description = "Approval History"
    _order = "action_date desc, id desc"

    request_type = fields.Selection(
        selection=[
            ("incoming_fund", "Incoming Fund"),
            ("allocation", "Fund Allocation"),
            ("requisition", "Fund Requisition"),
            ("bill", "Fund Bill"),
            ("transfer", "Fund Transfer"),
        ],
        required=True,
        index=True,
    )
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    reference = fields.Char(help="Business document number or label for the related request.")
    approval_level = fields.Selection(
        selection=[
            ("gm", "General Manager"),
            ("finance", "Finance"),
            ("md", "Managing Director"),
        ],
        required=True,
    )
    decision = fields.Selection(
        selection=[
            ("submitted", "Submitted"),
            ("confirmed", "Confirmed"),
            ("approved", "Approved"),
            ("posted", "Posted"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("closed", "Closed"),
            ("reversed", "Reversed"),
        ],
        required=True,
        index=True,
    )
    action_by = fields.Many2one(comodel_name="res.users", required=True, readonly=True)
    record_creator_id = fields.Many2one(comodel_name="res.users", readonly=True)
    submitted_by_id = fields.Many2one(comodel_name="res.users", readonly=True)
    action_date = fields.Datetime(required=True, readonly=True, default=fields.Datetime.now)
    comment = fields.Text()
    old_state = fields.Char()
    new_state = fields.Char()
    reference_document = fields.Char(help="Reference document or transaction identifier.")
    amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(comodel_name="res.currency")
    company_id = fields.Many2one(comodel_name="res.company", required=True, index=True)
    fund_account_id = fields.Many2one(comodel_name="nn.fund.account", ondelete="set null")
    project_id = fields.Many2one(comodel_name="project.project", ondelete="set null")
    expense_head_id = fields.Many2one(comodel_name="nn.expense.head", ondelete="set null")
    allocation_id = fields.Many2one(comodel_name="nn.fund.allocation", ondelete="cascade")
    requisition_id = fields.Many2one(comodel_name="nn.fund.requisition", ondelete="cascade")
    bill_id = fields.Many2one(comodel_name="nn.fund.bill", ondelete="cascade")
    transfer_id = fields.Many2one(comodel_name="nn.fund.transfer", ondelete="cascade")
