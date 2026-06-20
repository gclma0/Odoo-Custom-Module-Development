"""Dashboard wizard for fund management summaries."""

from markupsafe import Markup

from odoo import api, fields, models


class FundDashboardWizard(models.TransientModel):
    """Provides a simple read-only operational dashboard."""

    _name = "nn.fund.dashboard.wizard"
    _description = "Fund Management Dashboard"

    currency_id = fields.Many2one(comodel_name="res.currency", default=lambda self: self.env.company.currency_id.id)
    total_funds_received = fields.Monetary(currency_field="currency_id", readonly=True)
    unassigned_balance = fields.Monetary(currency_field="currency_id", readonly=True)
    held_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    assigned_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    spent_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    pending_approvals = fields.Integer(readonly=True)
    project_balance_html = fields.Html(readonly=True, sanitize=False)
    expense_head_balance_html = fields.Html(readonly=True, sanitize=False)
    recent_movements_html = fields.Html(readonly=True, sanitize=False)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        company = self.env.company
        account_model = self.env["nn.fund.account"].search([("company_id", "=", company.id)])
        project_model = self.env["project.project"].search([("company_id", "=", company.id)])
        expense_head_model = self.env["nn.expense.head"].search([("company_id", "=", company.id)])

        values.update(
            {
                "currency_id": company.currency_id.id,
                "total_funds_received": sum(account_model.mapped("total_received")),
                "unassigned_balance": sum(account_model.mapped("available_unassigned_balance")),
                "held_amount": sum(account_model.mapped("amount_on_hold"))
                + sum(project_model.mapped("requisition_hold"))
                + sum(project_model.mapped("transfer_hold"))
                + sum(expense_head_model.mapped("requisition_hold"))
                + sum(expense_head_model.mapped("transfer_hold")),
                "assigned_amount": sum(account_model.mapped("total_assigned_amount")),
                "spent_amount": sum(project_model.mapped("total_spent_amount"))
                + sum(expense_head_model.mapped("total_spent_amount")),
                "pending_approvals": self._get_pending_approval_count(company),
                "project_balance_html": self._build_project_balance_html(project_model),
                "expense_head_balance_html": self._build_expense_head_balance_html(expense_head_model),
                "recent_movements_html": self._build_recent_movements_html(company),
            }
        )
        return values

    @api.model
    def action_open_dashboard(self):
        wizard = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": "Fund Dashboard",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "current",
        }

    @api.model
    def _get_pending_approval_count(self, company):
        pending_states = ["submitted", "gm_approval", "finance_approval", "md_approval"]
        return (
            self.env["nn.fund.allocation"].search_count([("company_id", "=", company.id), ("state", "in", pending_states)])
            + self.env["nn.fund.requisition"].search_count([("company_id", "=", company.id), ("state", "in", pending_states)])
            + self.env["nn.fund.transfer"].search_count([("company_id", "=", company.id), ("state", "in", pending_states)])
        )

    @api.model
    def _build_project_balance_html(self, projects):
        rows = "".join(
            f"<tr><td>{project.display_name}</td><td>{project.available_fund:.2f}</td><td>{project.approved_unspent_amount:.2f}</td><td>{project.total_spent_amount:.2f}</td></tr>"
            for project in projects
        ) or "<tr><td colspan='4'>No project balances available.</td></tr>"
        return Markup(
            "<table class='table table-sm table-striped'>"
            "<thead><tr><th>Project</th><th>Available</th><th>Approved Unspent</th><th>Spent</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @api.model
    def _build_expense_head_balance_html(self, expense_heads):
        rows = "".join(
            f"<tr><td>{head.display_name}</td><td>{head.available_fund:.2f}</td><td>{head.approved_unspent_amount:.2f}</td><td>{head.total_spent_amount:.2f}</td></tr>"
            for head in expense_heads
        ) or "<tr><td colspan='4'>No expense head balances available.</td></tr>"
        return Markup(
            "<table class='table table-sm table-striped'>"
            "<thead><tr><th>Expense Head</th><th>Available</th><th>Approved Unspent</th><th>Spent</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @api.model
    def _build_recent_movements_html(self, company):
        movements = []
        for record in self.env["nn.incoming.fund"].search([("company_id", "=", company.id)], limit=5, order="create_date desc"):
            movements.append((record.create_date, "Incoming Fund", record.transaction_reference, record.amount, record.state))
        for record in self.env["nn.fund.allocation"].search([("company_id", "=", company.id)], limit=5, order="create_date desc"):
            movements.append((record.create_date, "Allocation", record.request_number, record.amount, record.state))
        for record in self.env["nn.fund.requisition"].search([("company_id", "=", company.id)], limit=5, order="create_date desc"):
            movements.append((record.create_date, "Requisition", record.requisition_number, record.amount, record.state))
        for record in self.env["nn.fund.bill"].search([("company_id", "=", company.id)], limit=5, order="create_date desc"):
            movements.append((record.create_date, "Bill", record.bill_number, record.amount, record.state))
        for record in self.env["nn.fund.transfer"].search([("company_id", "=", company.id)], limit=5, order="create_date desc"):
            movements.append((record.create_date, "Transfer", record.transfer_number, record.amount, record.state))
        movements = sorted(movements, key=lambda item: item[0] or fields.Datetime.now(), reverse=True)[:10]
        rows = "".join(
            f"<tr><td>{date}</td><td>{kind}</td><td>{reference}</td><td>{amount:.2f}</td><td>{state}</td></tr>"
            for date, kind, reference, amount, state in movements
        ) or "<tr><td colspan='5'>No recent fund movements available.</td></tr>"
        return Markup(
            "<table class='table table-sm table-striped'>"
            "<thead><tr><th>Date</th><th>Type</th><th>Reference</th><th>Amount</th><th>Status</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
