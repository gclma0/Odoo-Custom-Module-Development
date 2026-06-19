# Entity Relationship Design - NN Fund Management

## 1. Fund Account

Model: `nn.fund.account`

Represents a bank, cash, or other financial account where funds are received.

### Fields

| Field                  | Type                          | Notes                             |
| ---------------------- | ----------------------------- | --------------------------------- |
| `name`                 | Char                          | Required                          |
| `account_type`         | Selection                     | Bank, Cash, Other                 |
| `company_id`           | Many2one `res.company`        | Required                          |
| `currency_id`          | Many2one `res.currency`       | Related to company currency       |
| `active`               | Boolean                       | Archive support                   |
| `incoming_fund_ids`    | One2many `nn.incoming.fund`   | Incoming funds                    |
| `allocation_ids`       | One2many `nn.fund.allocation` | Fund allocations                  |
| `total_received`       | Monetary, computed            | Confirmed incoming funds          |
| `allocation_hold`      | Monetary, computed            | Submitted/GM-approved allocations |
| `total_assigned`       | Monetary, computed            | Approved allocations              |
| `available_unassigned` | Monetary, computed            | Remaining unassigned balance      |

## 2. Incoming Fund

Model: `nn.incoming.fund`

Represents money received into a fund account.

### Fields

| Field                   | Type                       | Notes                       |
| ----------------------- | -------------------------- | --------------------------- |
| `name`                  | Char                       | Sequence                    |
| `fund_account_id`       | Many2one `nn.fund.account` | Required                    |
| `date`                  | Date                       | Required                    |
| `amount`                | Monetary                   | Required, must be positive  |
| `transaction_reference` | Char                       | Required                    |
| `sender_source`         | Char                       | Sender/source               |
| `description`           | Text                       | Optional                    |
| `attachment`            | Binary                     | Optional                    |
| `company_id`            | Many2one `res.company`     | Required                    |
| `currency_id`           | Many2one `res.currency`    | Related                     |
| `state`                 | Selection                  | Draft, Confirmed, Cancelled |

### Constraint

Transaction reference must be unique within the same fund account.

## 3. Expense Head

Model: `nn.expense.head`

Represents expense categories such as Salary, Rent, Utilities, Marketing, and Administration.

### Fields

| Field                | Type                           | Notes                      |
| -------------------- | ------------------------------ | -------------------------- |
| `name`               | Char                           | Required                   |
| `company_id`         | Many2one `res.company`         | Required                   |
| `active`             | Boolean                        | Archive support            |
| `allocation_ids`     | One2many `nn.fund.allocation`  | Allocations                |
| `requisition_ids`    | One2many `nn.fund.requisition` | Requisitions               |
| `total_allocated`    | Monetary, computed             | Approved allocations       |
| `available_balance`  | Monetary, computed             | Available usable balance   |
| `requisition_hold`   | Monetary, computed             | Pending requisitions       |
| `transfer_hold`      | Monetary, computed             | Pending outgoing transfers |
| `total_spent`        | Monetary, computed             | Posted bills               |
| `incoming_transfers` | Monetary, computed             | Approved transfers in      |
| `outgoing_transfers` | Monetary, computed             | Approved transfers out     |

## 4. Project

Model: `project.project`

The module reuses Odoo's standard project model.

The module may extend `project.project` with computed fund balance fields:

| Field                  | Type                           | Notes                      |
| ---------------------- | ------------------------------ | -------------------------- |
| `fund_allocation_ids`  | One2many `nn.fund.allocation`  | Allocations                |
| `fund_requisition_ids` | One2many `nn.fund.requisition` | Requisitions               |
| `total_allocated`      | Monetary, computed             | Approved allocations       |
| `available_balance`    | Monetary, computed             | Available usable balance   |
| `requisition_hold`     | Monetary, computed             | Pending requisitions       |
| `transfer_hold`        | Monetary, computed             | Pending outgoing transfers |
| `total_spent`          | Monetary, computed             | Posted bills               |
| `incoming_transfers`   | Monetary, computed             | Approved transfers in      |
| `outgoing_transfers`   | Monetary, computed             | Approved transfers out     |

## 5. Fund Allocation

Model: `nn.fund.allocation`

Allocates unassigned fund account balance to either a project or an expense head.

### Fields

| Field                  | Type                           | Notes                                                                     |
| ---------------------- | ------------------------------ | ------------------------------------------------------------------------- |
| `name`                 | Char                           | Sequence, e.g. ALLOC00001                                                 |
| `fund_account_id`      | Many2one `nn.fund.account`     | Required                                                                  |
| `project_id`           | Many2one `project.project`     | Optional                                                                  |
| `expense_head_id`      | Many2one `nn.expense.head`     | Optional                                                                  |
| `amount`               | Monetary                       | Required, positive                                                        |
| `purpose`              | Text                           | Required                                                                  |
| `request_date`         | Date                           | Required                                                                  |
| `requested_by`         | Many2one `res.users`           | Default current user                                                      |
| `attachment`           | Binary                         | Optional                                                                  |
| `company_id`           | Many2one `res.company`         | Required                                                                  |
| `state`                | Selection                      | Draft, Submitted, GM Approved, MD Approved, Approved, Rejected, Cancelled |
| `approval_history_ids` | One2many `nn.approval.history` | Approval logs                                                             |

### Constraints

* Must select either project or expense head.
* Cannot select both project and expense head.
* Amount cannot exceed fund account available unassigned balance on submit.

## 6. Fund Requisition

Model: `nn.fund.requisition`

Requests funds from a project or expense head.

### Fields

| Field                       | Type                       | Notes                                                                             |
| --------------------------- | -------------------------- | --------------------------------------------------------------------------------- |
| `name`                      | Char                       | Sequence, e.g. REQ00001                                                           |
| `project_id`                | Many2one `project.project` | Optional                                                                          |
| `expense_head_id`           | Many2one `nn.expense.head` | Optional                                                                          |
| `requested_amount`          | Monetary                   | Required, positive                                                                |
| `purpose`                   | Text                       | Required                                                                          |
| `request_date`              | Date                       | Required                                                                          |
| `required_date`             | Date                       | Optional                                                                          |
| `requested_by`              | Many2one `res.users`       | Default current user                                                              |
| `attachment`                | Binary                     | Optional                                                                          |
| `company_id`                | Many2one `res.company`     | Required                                                                          |
| `state`                     | Selection                  | Draft, Submitted, GM Approved, MD Approved, Approved, Rejected, Cancelled, Closed |
| `bill_ids`                  | One2many `nn.fund.bill`    | Related bills                                                                     |
| `remaining_billable_amount` | Monetary, computed         | Approved amount minus posted bills                                                |

### Constraints

* Must select either project or expense head.
* Cannot select both project and expense head.
* Requested amount cannot exceed available balance on submit.

## 7. Fund Bill

Model: `nn.fund.bill`

Records bills against approved requisitions.

### Fields

| Field             | Type                           | Notes                    |
| ----------------- | ------------------------------ | ------------------------ |
| `name`            | Char                           | Sequence, e.g. BILL00001 |
| `requisition_id`  | Many2one `nn.fund.requisition` | Required                 |
| `project_id`      | Many2one `project.project`     | Related/validated        |
| `expense_head_id` | Many2one `nn.expense.head`     | Related/validated        |
| `amount`          | Monetary                       | Required, positive       |
| `bill_date`       | Date                           | Required                 |
| `description`     | Text                           | Optional                 |
| `attachment`      | Binary                         | Optional                 |
| `company_id`      | Many2one `res.company`         | Required                 |
| `state`           | Selection                      | Draft, Posted, Cancelled |

### Constraints

* Bill must be linked to an approved requisition.
* Bill must use the same project or expense head as the requisition.
* Bill amount cannot exceed remaining billable amount.
* Posted bills cannot be deleted directly.

## 8. Fund Transfer

Model: `nn.fund.transfer`

Transfers available balance between projects and/or expense heads.

### Fields

| Field                         | Type                           | Notes                                                                     |
| ----------------------------- | ------------------------------ | ------------------------------------------------------------------------- |
| `name`                        | Char                           | Sequence, e.g. TRN00001                                                   |
| `source_project_id`           | Many2one `project.project`     | Optional                                                                  |
| `source_expense_head_id`      | Many2one `nn.expense.head`     | Optional                                                                  |
| `destination_project_id`      | Many2one `project.project`     | Optional                                                                  |
| `destination_expense_head_id` | Many2one `nn.expense.head`     | Optional                                                                  |
| `amount`                      | Monetary                       | Required, positive                                                        |
| `reason`                      | Text                           | Required                                                                  |
| `requested_by`                | Many2one `res.users`           | Default current user                                                      |
| `request_date`                | Date                           | Required                                                                  |
| `company_id`                  | Many2one `res.company`         | Required                                                                  |
| `state`                       | Selection                      | Draft, Submitted, GM Approved, MD Approved, Approved, Rejected, Cancelled |
| `approval_history_ids`        | One2many `nn.approval.history` | Approval logs                                                             |

### Constraints

* Source must be either project or expense head.
* Destination must be either project or expense head.
* Source and destination cannot be the same.
* Amount cannot exceed source available balance on submit.

## 9. Approval History

Model: `nn.approval.history`

Stores approval and rejection records.

### Fields

| Field            | Type                   | Notes                             |
| ---------------- | ---------------------- | --------------------------------- |
| `res_model`      | Char                   | Related model name                |
| `res_id`         | Integer                | Related record ID                 |
| `request_type`   | Selection              | Allocation, Requisition, Transfer |
| `approval_level` | Selection              | GM, MD                            |
| `approver_id`    | Many2one `res.users`   | Approver                          |
| `date`           | Datetime               | Decision date                     |
| `comment`        | Text                   | Approval/rejection comment        |
| `result`         | Selection              | Approved, Rejected                |
| `previous_state` | Char                   | Old state                         |
| `new_state`      | Char                   | New state                         |
| `amount`         | Monetary               | Related amount                    |
| `company_id`     | Many2one `res.company` | Company                           |

## 10. Approval Configuration

Model: `nn.approval.config`

Stores company-wise approval settings.

### Fields

| Field                 | Type                   | Notes            |
| --------------------- | ---------------------- | ---------------- |
| `company_id`          | Many2one `res.company` | Required, unique |
| `gm_approver_id`      | Many2one `res.users`   | Required         |
| `md_approver_id`      | Many2one `res.users`   | Required         |
| `allow_self_approval` | Boolean                | Default False    |
| `active`              | Boolean                | Archive support  |
