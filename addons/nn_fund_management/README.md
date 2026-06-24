# NN Fund Management

## Module Purpose

`nn_fund_management` is an Odoo 17 Community custom module for controlled fund movement from receipt to allocation, requisition, billing, transfer, approval, and audit tracking.

The design goal is to prevent double spending while keeping balance fields derived from transactional records and workflow states.

## Features

- fund account management
- incoming fund recording and confirmation
- duplicate transaction reference protection per fund account
- allocation of unassigned funds to projects or expense heads
- configurable approval rules for allocation, requisition, and transfer
- approval history and broader financial audit entries
- requisition workflow with billable reserve tracking
- bill posting against approved requisitions
- partial billing with overbilling prevention
- transfer workflow between projects and expense heads
- company-based record rules and server-side access checks
- demo seed records for walkthrough preparation
- dashboard summaries
- activity notifications
- bank email import prototype
- approval rule filters by project / expense category style fields

## Models

Implemented business models:

- `nn.fund.account`
- `nn.incoming.fund`
- `nn.expense.head`
- `nn.fund.allocation`
- `nn.fund.requisition`
- `nn.fund.bill`
- `nn.fund.transfer`
- `nn.approval.config`
- `nn.approval.config.line`
- `nn.approval.history`

Extended standard models:

- `project.project`

## Views

Implemented UI areas:

- fund accounts
- incoming funds
- expense heads
- fund allocations
- fund requisitions
- fund bills
- fund transfers
- approval configurations
- approval history
- project form extension with `Fund Management` tab

## Security

Groups:

- `Fund User`
- `Finance User`
- `GM Approver`
- `MD Approver`
- `Fund Administrator`

Security implementation includes:

- ACLs in `ir.model.access.csv`
- company-based record rules
- server-side permission checks on confirm, post, approve, reject, cancel, close, and reverse actions

## Future Improvements

- broader record-rule filtering for assigned approvers only
- richer reversal workflow and accounting-style audit trails
- optional integration with Odoo vendor bills
- real mailbox polling for bank email processing
- a more polished dashboard frontend experience
