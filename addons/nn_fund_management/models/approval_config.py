"""Approval configuration models."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ApprovalConfig(models.Model):
    """Defines configurable approval rules for fund workflows."""

    _name = "nn.approval.config"
    _description = "Approval Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_type, min_amount, id"

    name = fields.Char(required=True, tracking=True)
    request_type = fields.Selection(
        selection=[
            ("allocation", "Fund Allocation"),
            ("requisition", "Fund Requisition"),
            ("transfer", "Fund Transfer"),
        ],
        required=True,
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
    min_amount = fields.Monetary(currency_field="currency_id", default=0.0, tracking=True)
    max_amount = fields.Monetary(currency_field="currency_id", tracking=True)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        comodel_name="nn.approval.config.line",
        inverse_name="config_id",
        string="Approval Steps",
        copy=True,
    )
    notes = fields.Text()

    _sql_constraints = [
        (
            "approval_config_name_company_uniq",
            "unique(name, company_id)",
            "The approval configuration name must be unique per company.",
        ),
    ]

    @api.constrains("min_amount", "max_amount")
    def _check_amount_range(self):
        for record in self:
            if record.min_amount < 0:
                raise ValidationError("Minimum amount cannot be negative.")
            if record.max_amount and record.max_amount < record.min_amount:
                raise ValidationError("Maximum amount must be greater than or equal to minimum amount.")


class ApprovalConfigLine(models.Model):
    """Defines the ordered approval steps within a rule."""

    _name = "nn.approval.config.line"
    _description = "Approval Configuration Line"
    _order = "sequence, id"

    config_id = fields.Many2one(
        comodel_name="nn.approval.config",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10, required=True)
    approval_level = fields.Selection(
        selection=[
            ("gm", "General Manager"),
            ("finance", "Finance"),
            ("md", "Managing Director"),
        ],
        required=True,
    )
    approver_user_id = fields.Many2one(comodel_name="res.users", string="Approver User")
    approver_group_id = fields.Many2one(comodel_name="res.groups", string="Approver Group")
    required = fields.Boolean(default=True)

    @api.constrains("approver_user_id", "approver_group_id")
    def _check_approver_source(self):
        for line in self:
            if not line.approver_user_id and not line.approver_group_id:
                raise ValidationError("Each approval step must define an approver user or approver group.")

    @api.constrains("sequence", "config_id", "approval_level")
    def _check_unique_level_per_config(self):
        for line in self:
            duplicates = self.search_count(
                [
                    ("id", "!=", line.id),
                    ("config_id", "=", line.config_id.id),
                    ("approval_level", "=", line.approval_level),
                ]
            )
            if duplicates:
                raise ValidationError("Each approval level can appear only once per configuration.")
