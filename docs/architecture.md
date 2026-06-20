# NN Fund Management - Architecture

## 1. Objective

The module manages the controlled movement of money across these stages:

1. funds are received into a fund account
2. money remains unassigned until allocated
3. allocations move money to a project or expense head
4. requisitions reserve allocated funds for later billing
5. bills consume approved requisition balances
6. transfers move available funds between projects and expense heads

The architectural priority is financial integrity:

- balances are computed from workflow records
- pending amounts are held and excluded from reuse
- approved reserved amounts remain unavailable for other requests
- reversal is conservative when downstream balances already consumed the money

## 2. Core Models

- `nn.fund.account`
  - source account for incoming money
- `nn.incoming.fund`
  - records received money and confirmation status
- `project.project`
  - standard Odoo project model extended with fund balance fields
- `nn.expense.head`
  - non-project allocation target such as salary, rent, or utilities
- `nn.fund.allocation`
  - moves unassigned fund account money to a project or expense head
- `nn.fund.requisition`
  - reserves available project or expense balance for later billing
- `nn.fund.bill`
  - custom bill record linked to an approved requisition
- `nn.fund.transfer`
  - moves available balance between projects and expense heads
- `nn.approval.config`
  - stores approval rules by request type, company, and amount range
- `nn.approval.config.line`
  - stores ordered approval steps
- `nn.approval.history`
  - stores workflow approvals and broader audit events

## 3. Entity Relationships

### Fund Account

- one fund account has many incoming funds
- one fund account has many allocation requests
- its balance is derived from confirmed incoming funds plus allocation workflow state

### Project and Expense Head

- projects and expense heads are parallel allocation targets
- both can receive approved allocations
- both can issue requisitions
- both can be source or destination in transfers
- both can accumulate spent amounts through posted bills

### Requisition and Bill

- one requisition belongs to exactly one project or one expense head
- one approved requisition can have many partial bills
- posted bills consume requisition remaining billable amount

### Approval Models

- one approval configuration has many approval lines
- allocation, requisition, and transfer records store the matched approval config and current approval line
- approval history links back to allocation, requisition, transfer, and bill records as needed

## 4. Money Flow

### Incoming Fund

- `draft` incoming fund: no balance effect
- `confirmed` incoming fund:
  - increases `fund account total received`
  - increases `fund account available unassigned balance`
- `reversed` incoming fund:
  - drops out of confirmed totals

### Allocation

- `submitted` / approval-pending allocation:
  - decreases fund account available unassigned balance
  - increases fund account hold
- `approved` allocation:
  - decreases fund account unassigned capacity permanently
  - increases target allocated/available balance
- `rejected` / `cancelled` allocation:
  - releases hold back to fund account
- `reversed` allocation:
  - removes approved allocation effect if downstream target balance is still safely reversible

### Requisition

- `submitted` / approval-pending requisition:
  - increases target requisition hold
  - decreases target available balance
- `approved` requisition:
  - removes hold
  - increases approved unspent reserve
- `closed` requisition:
  - releases unused remaining billable amount
- `reversed` requisition:
  - allowed only when nothing has been billed and nothing was already released

### Bill

- `posted` bill:
  - increases requisition spent amount
  - decreases requisition remaining billable amount
  - increases target total spent amount
- `cancelled` bill:
  - drops out of posted totals
  - restores remaining billable balance

### Transfer

- `submitted` / approval-pending transfer:
  - increases source transfer hold
  - decreases source available balance
- `approved` transfer:
  - increases source outgoing transfer total
  - increases destination incoming transfer total
  - moves effective available balance from source to destination
- `rejected` / `cancelled` transfer:
  - releases source hold
- `reversed` transfer:
  - allowed only if destination still has enough free available balance

## 5. Balance Calculation Logic

### Fund Account

- `total_received`
  - sum of confirmed incoming funds
- `amount_on_hold`
  - sum of pending allocations
- `total_assigned_amount`
  - sum of approved allocations
- `available_unassigned_balance`
  - confirmed incoming
  - minus pending allocation hold
  - minus approved assigned amount

### Project / Expense Head

- `total_allocated_fund`
  - sum of approved allocations to the target
- `requisition_hold`
  - sum of pending requisitions
- `transfer_hold`
  - sum of pending outgoing transfers
- `approved_unspent_amount`
  - sum of remaining billable amounts on approved requisitions
- `total_spent_amount`
  - sum of posted bills
- `incoming_transfer_amount`
  - sum of approved incoming transfers
- `outgoing_transfer_amount`
  - sum of approved outgoing transfers
- `available_fund`
  - approved allocations
  - plus approved incoming transfers
  - minus approved outgoing transfers
  - minus requisition hold
  - minus transfer hold
  - minus approved unspent requisition reserve

## 6. Workflow States

### Incoming Fund

- `draft -> confirmed / cancelled -> reversed`

### Allocation

- `draft -> submitted -> gm_approval -> finance_approval -> md_approval -> approved / rejected / cancelled / reversed`

### Requisition

- `draft -> submitted -> gm_approval -> finance_approval -> md_approval -> approved / rejected / cancelled / closed / reversed`

### Bill

- `draft -> posted -> cancelled`

### Transfer

- `draft -> submitted -> gm_approval -> finance_approval -> md_approval -> approved / rejected / cancelled / reversed`

Note:
- the minimum required approver chain is `GM -> MD`
- the model also supports an optional `Finance` approval level through configuration

## 7. Approval Logic

- approvers are not hardcoded in business models
- approval config is matched by:
  - request type
  - company
  - amount range
- approval lines are processed in sequence order
- current approver is enforced server-side
- self-approval is blocked for requesters unless specially privileged
- audit entries are written for submit, approve, reject, cancel, reverse, confirm, post, and close events

## 8. Security Groups

- `Fund User`
  - basic create/view access to allowed workflow records
- `Finance User`
  - can confirm incoming funds, post/cancel bills, and handle finance-level actions
- `GM Approver`
  - approves configured GM steps
- `MD Approver`
  - approves configured MD steps
- `Fund Administrator`
  - full access and setup authority

## 9. Security Design

Security is enforced at multiple layers:

- model ACLs
- company-based record rules
- server-side action checks via a shared company access mixin
- workflow-specific permission checks inside methods

This means hidden buttons alone are not trusted.

## 10. Menu Structure

`Fund Management`

- `Operations`
  - Incoming Funds
  - Fund Allocations
  - Fund Requisitions
  - Fund Bills
  - Fund Transfers
  - Approval History
- `Configuration`
  - Fund Accounts
  - Expense Heads
  - Approval Configurations

## 11. Double-Spending Prevention

Double spending is prevented by a combination of:

- computed balances from transactional records
- workflow-state-dependent hold logic
- amount validation before submit/post actions
- remaining billable amount enforcement on bills
- transfer hold and requisition hold reducing available balances
- conservative reversal rules that block undoing records once downstream balances are already consumed

## 12. Known Architectural Tradeoffs

- custom `Fund Bill` model is used instead of vendor bills to keep workflow control simpler for this assessment
- approval history acts as a generalized audit log instead of a full accounting journal
- reversal flows are intentionally strict to protect integrity over convenience
