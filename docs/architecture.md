# NN Fund Management - Architecture

## 1. Objective

## 2. Core Models

## 2. Core Models

The module will use the following models:

- `nn.fund.account` - stores bank, cash or other fund accounts.
- `nn.incoming.fund` - records incoming funds received into a fund account.
- `project.project` - Odoo's standard project model used for project-based allocation.
- `nn.expense.head` - custom model for expense categories such as salary, rent, utility, marketing and administration.
- `nn.fund.allocation` - handles allocation of unassigned funds to a project or expense head.
- `nn.fund.requisition` - handles fund requests from a project or expense head.
- `nn.fund.bill` - custom bill model linked to approved requisitions.
- `nn.fund.transfer` - handles transfers between projects and/or expense heads.
- `nn.approval.history` - stores approval and rejection history.
- `nn.approval.config` - stores configurable GM and MD approvers.

## 3. Entity Relationships

### Fund Account

- One fund account can have many incoming funds.
- One fund account can have many fund allocation requests.
- Fund account balances are calculated from confirmed incoming funds and allocation records.

### Incoming Fund

- Each incoming fund belongs to one fund account.
- Incoming funds increase the fund account's total received amount after confirmation.
- Transaction reference must be unique within the same fund account.

### Project

- Projects use Odoo's standard `project.project` model.
- A project can receive fund allocations.
- A project can have fund requisitions.
- A project can have bills through approved requisitions.
- A project can be a source or destination in fund transfers.

### Expense Head

- Expense heads are stored in `nn.expense.head`.
- An expense head can receive fund allocations.
- An expense head can have fund requisitions.
- An expense head can have bills through approved requisitions.
- An expense head can be a source or destination in fund transfers.

### Fund Allocation

- Each allocation belongs to one fund account.
- Each allocation must target either one project or one expense head.
- An allocation cannot target both project and expense head at the same time.
- Approved allocations increase the available fund of the selected project or expense head.

### Fund Requisition

- Each requisition must belong to either one project or one expense head.
- A requisition cannot belong to both project and expense head at the same time.
- Approved requisitions reserve money for bills.
- A requisition can have multiple partial bills.

### Fund Bill

- Each bill must be linked to one approved fund requisition.
- A bill must use the same project or expense head as its requisition.
- Posted bills reduce the remaining billable amount of the requisition.
- Posted bills increase the spent amount of the related project or expense head.

### Fund Transfer

- Each transfer has one source and one destination.
- The source can be a project or an expense head.
- The destination can be a project or an expense head.
- The source and destination cannot be the same.
- Approved transfers reduce the source balance and increase the destination balance.

### Approval History

- Approval history records are linked to allocation, requisition, and transfer records.
- Each approval history entry stores the approver, approval level, decision, comment, date, previous state, and new state.

### Approval Configuration

- Approval configuration stores the GM and MD approvers per company.
- Approval users are configurable and not hardcoded.

## 4. Money Flow

## 5. Balance Calculation Logic

## 6. Workflow States

## 7. Approval Logic

## 8. Security Groups

## 9. Menu Structure

## 10. Double-Spending Prevention