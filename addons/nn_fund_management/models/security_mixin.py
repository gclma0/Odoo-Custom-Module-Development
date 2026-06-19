"""Shared server-side security helpers for fund models."""

from odoo import models
from odoo.exceptions import AccessError


class FundCompanyAccessMixin(models.AbstractModel):
    """Provides server-side company access validation for financial records."""

    _name = "nn.fund.company.access.mixin"
    _description = "Fund Company Access Mixin"

    def _check_company_access(self):
        allowed_companies = self.env.companies
        for record in self:
            company = getattr(record, "company_id", False)
            if company and company not in allowed_companies:
                raise AccessError("You do not have access to this company's financial records.")
