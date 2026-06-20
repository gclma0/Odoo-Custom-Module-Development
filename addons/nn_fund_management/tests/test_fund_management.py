"""Core workflow integrity tests for nn_fund_management."""

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestFundManagement(TransactionCase):
    """Covers critical workflow and double-spending protections."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Users = cls.env["res.users"].with_context(no_reset_password=True)

        cls.group_fund_user = cls.env.ref("nn_fund_management.group_fund_user")
        cls.group_finance_user = cls.env.ref("nn_fund_management.group_finance_user")
        cls.group_gm = cls.env.ref("nn_fund_management.group_gm_approver")
        cls.group_md = cls.env.ref("nn_fund_management.group_md_approver")
        cls.group_internal_user = cls.env.ref("base.group_user")
        cls.group_project_user = cls.env.ref("project.group_project_user")

        cls.fund_user = cls._create_user("fund.user", [cls.group_fund_user.id])
        cls.finance_user = cls._create_user("finance.user", [cls.group_finance_user.id])
        cls.gm_user = cls._create_user("gm.user", [cls.group_gm.id])
        cls.md_user = cls._create_user("md.user", [cls.group_md.id])

        cls.project_a = cls.env["project.project"].create({"name": "Project A", "company_id": cls.company.id})
        cls.project_b = cls.env["project.project"].create({"name": "Project B", "company_id": cls.company.id})
        cls.expense_head = cls.env["nn.expense.head"].create(
            {"name": "Salary", "code": "SALARY_TEST", "company_id": cls.company.id}
        )

        cls.env["nn.approval.config"].search(
            [
                ("company_id", "=", cls.company.id),
                ("request_type", "in", ["allocation", "requisition", "transfer"]),
            ]
        ).unlink()

        cls._create_approval_config("allocation", "Allocation Default")
        cls._create_approval_config("requisition", "Requisition Default")
        cls._create_approval_config("transfer", "Transfer Default")

    @classmethod
    def _create_user(cls, login, group_ids):
        effective_groups = list(set(group_ids + [cls.group_internal_user.id, cls.group_project_user.id]))
        return cls.Users.create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "groups_id": [(6, 0, effective_groups)],
            }
        )

    @classmethod
    def _create_approval_config(cls, request_type, name):
        return cls.env["nn.approval.config"].create(
            {
                "name": name,
                "request_type": request_type,
                "company_id": cls.company.id,
                "min_amount": 0.0,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "approval_level": "gm",
                            "approver_user_id": cls.gm_user.id,
                            "required": True,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "sequence": 20,
                            "approval_level": "md",
                            "approver_user_id": cls.md_user.id,
                            "required": True,
                        },
                    ),
                ],
            }
        )

    def _create_fund_account(self, suffix):
        return self.env["nn.fund.account"].create(
            {
                "name": f"Main Fund {suffix}",
                "code": f"FA{suffix}",
                "account_type": "bank",
                "company_id": self.company.id,
            }
        )

    def _create_and_confirm_incoming(self, account, amount, reference):
        incoming = self.env["nn.incoming.fund"].create(
            {
                "fund_account_id": account.id,
                "amount": amount,
                "transaction_reference": reference,
                "sender_source": "Test Sender",
            }
        )
        incoming.with_user(self.finance_user).action_confirm()
        return incoming

    def _create_allocation(self, account, amount, project=None, expense_head=None, user=None):
        env = self.env["nn.fund.allocation"] if user is None else self.env["nn.fund.allocation"].with_user(user)
        return env.create(
            {
                "fund_account_id": account.id,
                "project_id": project.id if project else False,
                "expense_head_id": expense_head.id if expense_head else False,
                "amount": amount,
                "purpose": "Allocation for testing",
            }
        )

    def _submit_and_approve_allocation(self, allocation):
        allocation.action_submit()
        allocation.with_user(self.gm_user).action_approve()
        allocation.with_user(self.md_user).action_approve()
        return allocation

    def _create_requisition(self, amount, project=None, expense_head=None, user=None):
        env = self.env["nn.fund.requisition"] if user is None else self.env["nn.fund.requisition"].with_user(user)
        return env.create(
            {
                "project_id": project.id if project else False,
                "expense_head_id": expense_head.id if expense_head else False,
                "amount": amount,
                "purpose": "Requisition for testing",
                "required_date": "2026-06-30",
            }
        )

    def _submit_and_approve_requisition(self, requisition):
        requisition.action_submit()
        requisition.with_user(self.gm_user).action_approve()
        requisition.with_user(self.md_user).action_approve()
        return requisition

    def test_duplicate_incoming_reference_is_blocked_per_fund_account(self):
        account = self._create_fund_account("001")
        self.env["nn.incoming.fund"].create(
            {
                "fund_account_id": account.id,
                "amount": 1000.0,
                "transaction_reference": "TXN-001",
            }
        )

        with mute_logger("odoo.sql_db"):
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    self.env["nn.incoming.fund"].create(
                        {
                            "fund_account_id": account.id,
                            "amount": 500.0,
                            "transaction_reference": "TXN-001",
                        }
                    )

    def test_allocation_cannot_exceed_available_unassigned_balance(self):
        account = self._create_fund_account("002")
        self._create_and_confirm_incoming(account, 1000.0, "TXN-002")
        allocation = self._create_allocation(account, 1200.0, project=self.project_a)

        with self.assertRaises(UserError):
            allocation.action_submit()

    def test_requester_cannot_self_approve_allocation(self):
        account = self._create_fund_account("003")
        self._create_and_confirm_incoming(account, 1000.0, "TXN-003")
        allocation = self._create_allocation(account, 500.0, project=self.project_a, user=self.gm_user)

        allocation.action_submit()
        with self.assertRaises(UserError):
            allocation.with_user(self.gm_user).action_approve()

    def test_requisition_cannot_exceed_available_project_balance(self):
        account = self._create_fund_account("004")
        self._create_and_confirm_incoming(account, 1000.0, "TXN-004")
        allocation = self._create_allocation(account, 600.0, project=self.project_a)
        self._submit_and_approve_allocation(allocation)

        requisition = self._create_requisition(700.0, project=self.project_a)
        with self.assertRaises(UserError):
            requisition.action_submit()

    def test_bill_cannot_exceed_remaining_billable_amount(self):
        account = self._create_fund_account("005")
        self._create_and_confirm_incoming(account, 1000.0, "TXN-005")
        allocation = self._create_allocation(account, 800.0, project=self.project_b)
        self._submit_and_approve_allocation(allocation)
        requisition = self._create_requisition(500.0, project=self.project_b)
        self._submit_and_approve_requisition(requisition)

        bill = self.env["nn.fund.bill"].create(
            {
                "requisition_id": requisition.id,
                "project_id": self.project_b.id,
                "amount": 600.0,
                "description": "Overbilled",
            }
        )

        with self.assertRaises(UserError):
            bill.with_user(self.finance_user).action_post()

    def test_bill_cannot_use_wrong_project_for_requisition(self):
        account = self._create_fund_account("006")
        self._create_and_confirm_incoming(account, 1000.0, "TXN-006")
        allocation = self._create_allocation(account, 800.0, project=self.project_b)
        self._submit_and_approve_allocation(allocation)
        requisition = self._create_requisition(500.0, project=self.project_b)
        self._submit_and_approve_requisition(requisition)

        with self.assertRaises(ValidationError):
            self.env["nn.fund.bill"].create(
                {
                    "requisition_id": requisition.id,
                    "project_id": self.project_a.id,
                    "amount": 100.0,
                    "description": "Wrong project bill",
                }
            )

    def test_transfer_cannot_exceed_source_available_balance(self):
        account = self._create_fund_account("007")
        self._create_and_confirm_incoming(account, 1000.0, "TXN-007")
        allocation = self._create_allocation(account, 300.0, project=self.project_a)
        self._submit_and_approve_allocation(allocation)

        transfer = self.env["nn.fund.transfer"].create(
            {
                "source_project_id": self.project_a.id,
                "destination_project_id": self.project_b.id,
                "amount": 400.0,
                "reason": "Transfer over limit",
            }
        )

        with self.assertRaises(UserError):
            transfer.action_submit()

    def test_transfer_source_and_destination_cannot_be_same(self):
        with self.assertRaises(ValidationError):
            self.env["nn.fund.transfer"].create(
                {
                    "source_project_id": self.project_a.id,
                    "destination_project_id": self.project_a.id,
                    "amount": 100.0,
                    "reason": "Same source and destination",
                }
            )
