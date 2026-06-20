"""Bank email import prototype."""

import re

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class BankEmailImport(models.Model):
    """Prototype parser for bank transaction notification emails."""

    _name = "nn.bank.email.import"
    _description = "Bank Email Import"
    _inherit = ["mail.thread", "mail.activity.mixin", "nn.fund.company.access.mixin"]
    _order = "create_date desc, id desc"
    _rec_name = "message_id"

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
    fund_account_id = fields.Many2one(comodel_name="nn.fund.account", ondelete="restrict", tracking=True)
    message_id = fields.Char(required=True, tracking=True)
    email_subject = fields.Char(tracking=True)
    email_from = fields.Char(string="Sender Information", tracking=True)
    raw_email_body = fields.Text(required=True)
    bank_name = fields.Char(readonly=True, tracking=True)
    account_number = fields.Char(readonly=True, tracking=True)
    transaction_reference = fields.Char(readonly=True, tracking=True)
    transaction_date = fields.Date(readonly=True, tracking=True)
    received_amount = fields.Monetary(currency_field="currency_id", readonly=True, tracking=True)
    state = fields.Selection(
        selection=[("draft", "Draft"), ("processed", "Processed"), ("failed", "Failed")],
        default="draft",
        required=True,
        tracking=True,
    )
    failure_reason = fields.Text(readonly=True)
    incoming_fund_id = fields.Many2one(comodel_name="nn.incoming.fund", readonly=True)

    _sql_constraints = [
        (
            "bank_email_message_id_uniq",
            "unique(message_id)",
            "The same bank email message cannot be processed twice.",
        )
    ]

    @api.constrains("fund_account_id", "company_id")
    def _check_account_company(self):
        for record in self:
            if record.fund_account_id and record.fund_account_id.company_id != record.company_id:
                raise ValidationError("The selected fund account must belong to the same company as the bank email import.")

    def _parse_email(self):
        self.ensure_one()
        body = self.raw_email_body or ""
        bank_match = re.search(r"bank\s*[:\-]\s*(?P<value>.+)", body, re.IGNORECASE)
        account_match = re.search(r"account(?:\s*number)?\s*[:\-]\s*(?P<value>.+)", body, re.IGNORECASE)
        reference_match = re.search(r"(?:transaction\s*reference|reference)\s*[:\-]\s*(?P<value>.+)", body, re.IGNORECASE)
        date_match = re.search(r"(?:transaction\s*date|date)\s*[:\-]\s*(?P<value>\d{4}-\d{2}-\d{2})", body, re.IGNORECASE)
        amount_match = re.search(r"(?:received\s*amount|amount)\s*[:\-]\s*(?P<value>[0-9]+(?:\.[0-9]+)?)", body, re.IGNORECASE)

        bank_name = bank_match.group("value").strip() if bank_match else False
        account_number = account_match.group("value").strip() if account_match else False
        transaction_reference = reference_match.group("value").strip() if reference_match else False
        transaction_date = date_match.group("value").strip() if date_match else False
        received_amount = float(amount_match.group("value")) if amount_match else 0.0

        if not transaction_reference or not transaction_date or not received_amount:
            raise UserError("Email parsing failed. Required fields: transaction reference, transaction date, and received amount.")

        return {
            "bank_name": bank_name,
            "account_number": account_number,
            "transaction_reference": transaction_reference,
            "transaction_date": transaction_date,
            "received_amount": received_amount,
        }

    def action_process_email(self):
        self._check_company_access()
        for record in self:
            if record.state != "draft":
                raise UserError("Only draft bank emails can be processed.")
            if not record.fund_account_id:
                raise UserError("Select a fund account before processing the bank email.")
            try:
                parsed = record._parse_email()
                incoming_fund = self.env["nn.incoming.fund"].create(
                    {
                        "fund_account_id": record.fund_account_id.id,
                        "date": parsed["transaction_date"],
                        "amount": parsed["received_amount"],
                        "transaction_reference": parsed["transaction_reference"],
                        "sender_source": record.email_from,
                        "description": record.email_subject or "Imported from bank email",
                        "state": "pending_verification",
                    }
                )
                record.write({**parsed, "state": "processed", "failure_reason": False, "incoming_fund_id": incoming_fund.id})
            except Exception as exc:
                record.write({"state": "failed", "failure_reason": str(exc)})
