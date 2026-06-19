# System Design - NN Fund Management

## Objective

The `nn_fund_management` module manages fund receiving, allocation, requisition, billing, transfer, approval, and balance tracking in Odoo 17 Community.

The system must ensure that the same money cannot be allocated, transferred, requisitioned, or spent more than once.

## Core Design Decisions

### 1. Reuse Odoo Project Model

The module will reuse Odoo's standard `project.project` model for projects instead of creating a custom project model.

Reason:
Odoo already provides project records, company support, views, access control, and future extensibility.

### 2. Create Custom Expense Head Model

Expense heads such as Salary, Rent, Utilities, Marketing, and Administration will be stored in a custom model:

`nn.expense.head`

### 3. Use Custom Bill Model

The module will create a custom bill model:

`nn.fund.bill`

Reason:
The assessment allows either Odoo Vendor Bills or a custom bill model. A custom model is simpler, easier to control, and easier to explain for this assessment.

### 4. Computed Balance Strategy

Balance fields will not be manually edited.

Balances will be computed from transaction records such as incoming funds, allocations, requisitions, bills, and transfers.

### 5. Approval Configuration

GM and MD approvers will be configurable through:

`nn.approval.config`

No user ID or database ID will be hardcoded.

## Core Models

| Model                 | Purpose                                                 |
| --------------------- | ------------------------------------------------------- |
| `nn.fund.account`     | Stores bank, cash, or other fund accounts               |
| `nn.incoming.fund`    | Records money received into fund accounts               |
| `project.project`     | Standard Odoo project model                             |
| `nn.expense.head`     | Stores expense categories                               |
| `nn.fund.allocation`  | Allocates unassigned funds to projects or expense heads |
| `nn.fund.requisition` | Requests funds from projects or expense heads           |
| `nn.fund.bill`        | Records bills against approved requisitions             |
| `nn.fund.transfer`    | Transfers funds between projects and/or expense heads   |
| `nn.approval.history` | Stores approval and rejection history                   |
| `nn.approval.config`  | Stores configurable GM and MD approvers                 |

## Money Lifecycle

Money moves through the system in this order:

Incoming Fund
→ Fund Account Unassigned Balance
→ Allocation Hold
→ Project or Expense Head Available Balance
→ Requisition Hold
→ Reserved for Bills
→ Bill Posted
→ Spent Amount

Transfers move available money from one project or expense head to another.

## Main Workflows

### Incoming Fund

Draft → Confirmed → Cancelled

Confirmed incoming funds increase the fund account's received amount.

### Fund Allocation

Draft → Submitted → GM Approved → MD Approved → Approved
Rejected / Cancelled

Submitted allocations place money on hold. Approved allocations move money to the selected project or expense head.

### Fund Requisition

Draft → Submitted → GM Approved → MD Approved → Approved → Closed
Rejected / Cancelled

Submitted requisitions place project or expense funds on hold. Approved requisitions reserve money for bills.

### Fund Bill

Draft → Posted → Cancelled

Posted bills reduce the requisition's remaining billable amount and increase spent amount.

### Fund Transfer

Draft → Submitted → GM Approved → MD Approved → Approved
Rejected / Cancelled

Submitted transfers place source money on transfer hold. Approved transfers move money to the destination.

## Menu Structure

Fund Management

* Dashboard
* Fund Accounts
* Incoming Funds
* Projects
* Expense Heads
* Allocations
* Requisitions
* Bills
* Transfers
* Approval History
* Configuration
  * Approval Configuration
