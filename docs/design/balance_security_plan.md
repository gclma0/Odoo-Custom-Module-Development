# Balance, Security, and Implementation Plan - NN Fund Management

## 1. Balance Strategy

Balances will be computed from transaction records.

Users must not manually edit balance fields.

Only incoming funds create new money. All other operations either hold, move, release, or spend existing money.

## 2. Fund Account Balance Formulas

### Total Received

Confirmed incoming funds only.

`total_received = sum(confirmed incoming funds)`

### Allocation Hold

Allocations waiting for final approval.

`allocation_hold = sum(submitted or GM-approved allocations)`

### Total Assigned

Approved allocations.

`total_assigned = sum(approved allocations)`

### Available Unassigned Balance

`available_unassigned = total_received - allocation_hold - total_assigned`

## 3. Project / Expense Head Balance Formulas

The same logic applies to both projects and expense heads.

### Total Allocated

`total_allocated = approved allocations`

### Incoming Transfers

`incoming_transfers = approved transfers into this project or expense head`

### Outgoing Transfers

`outgoing_transfers = approved transfers out of this project or expense head`

### Transfer Hold

`transfer_hold = submitted or GM-approved outgoing transfers`

### Requisition Hold

`requisition_hold = submitted or GM-approved requisitions`

### Total Spent

`total_spent = posted bills`

### Available Balance

`available_balance = total_allocated + incoming_transfers - outgoing_transfers - transfer_hold - requisition_hold - total_spent`

## 4. Requisition Remaining Billable Amount

For approved requisitions:

`remaining_billable_amount = requested_amount - posted_bills`

Cancelled bills should not reduce remaining billable amount.

## 5. Double-Spending Prevention

The system prevents double spending by:

1. Checking available balance before submitting allocations, requisitions, and transfers.
2. Treating submitted/pending amounts as held amounts.
3. Excluding held amounts from available balances.
4. Blocking bills that exceed remaining billable amount.
5. Blocking bills linked to the wrong project or expense head.
6. Preventing repeated approvals from creating duplicate financial effects.
7. Computing balances from approved and pending records instead of manually editing balance fields.

## 6. Approval Logic

The approval workflow applies to:

* Fund Allocations
* Fund Requisitions
* Fund Transfers

### Approval Order

Draft
→ Submitted
→ GM Approved
→ MD Approved
→ Approved

Rejected and Cancelled are terminal exception states.

### Rules

* GM approval must happen before MD approval.
* MD cannot approve before GM.
* Only the configured GM approver can perform GM approval.
* Only the configured MD approver can perform MD approval.
* Users cannot approve their own requests unless `allow_self_approval` is enabled.
* Each approval or rejection must create an approval history record.
* Repeated approval actions must be blocked.

## 7. Security Groups

The module will define these groups:

| Group              | Purpose                                 |
| ------------------ | --------------------------------------- |
| Fund User          | Create and view own fund requests       |
| Finance User       | Confirm incoming funds and manage bills |
| GM Approver        | GM-level approval                       |
| MD Approver        | MD-level approval                       |
| Fund Administrator | Full access and configuration           |

## 8. Security Matrix

| Action                       | Fund User | Finance User | GM  | MD  | Admin |
| ---------------------------- | --------- | ------------ | --- | --- | ----- |
| View own requests            | Yes       | Yes          | Yes | Yes | Yes   |
| Create allocation request    | Yes       | Yes          | Yes | Yes | Yes   |
| Submit allocation request    | Yes       | Yes          | Yes | Yes | Yes   |
| GM approve                   | No        | No           | Yes | No  | Yes   |
| MD approve                   | No        | No           | No  | Yes | Yes   |
| Create incoming fund         | No        | Yes          | No  | No  | Yes   |
| Confirm incoming fund        | No        | Yes          | No  | No  | Yes   |
| Create requisition           | Yes       | Yes          | Yes | Yes | Yes   |
| Create bill                  | No        | Yes          | No  | No  | Yes   |
| Post bill                    | No        | Yes          | No  | No  | Yes   |
| Create transfer              | Yes       | Yes          | Yes | Yes | Yes   |
| Cancel approved transactions | No        | No           | No  | No  | Yes   |
| Configure approvers          | No        | No           | No  | No  | Yes   |

## 9. Server-Side Security Rules

Button hiding in XML is not enough.

Every sensitive action must check permissions in Python methods.

Examples:

* `action_confirm()` for incoming funds must check Finance User or Admin.
* `action_gm_approve()` must check configured GM approver.
* `action_md_approve()` must check configured MD approver.
* `action_post()` for bills must check Finance User or Admin.
* Cancel actions must check Admin or authorized group.

## 10. Sequence Numbers

| Record           | Prefix | Example    |
| ---------------- | ------ | ---------- |
| Incoming Fund    | FUND   | FUND00001  |
| Fund Allocation  | ALLOC  | ALLOC00001 |
| Fund Requisition | REQ    | REQ00001   |
| Fund Bill        | BILL   | BILL00001  |
| Fund Transfer    | TRN    | TRN00001   |

Sequences will be defined in:

`data/sequence_data.xml`

## 11. Implementation Roadmap

### Phase 1: Foundation

* Confirm Docker environment works.
* Confirm module activates in Odoo.
* Finalize architecture and balance strategy.

### Phase 2: Master Data

* Implement Fund Account.
* Implement Expense Head.
* Extend Project with computed balance fields.
* Create basic menus and views.

### Phase 3: Incoming Funds

* Implement Incoming Fund model.
* Add confirmation workflow.
* Add duplicate transaction reference constraint.
* Add finance user permission checks.

### Phase 4: Allocation

* Implement Fund Allocation model.
* Add GM and MD approval workflow.
* Add allocation hold logic.
* Add approval history.

### Phase 5: Requisition

* Implement Fund Requisition model.
* Add balance check on submit.
* Add requisition hold logic.
* Add remaining billable amount.

### Phase 6: Bills

* Implement Fund Bill model.
* Add bill posting.
* Block bills exceeding remaining amount.
* Block wrong project or expense head usage.
* Add bill cancellation logic.

### Phase 7: Transfers

* Implement Fund Transfer model.
* Add source/destination validation.
* Add transfer hold logic.
* Add approval workflow.

### Phase 8: Security

* Add security groups.
* Add access control CSV.
* Add record rules.
* Add server-side permission checks.

### Phase 9: Testing

Add automated tests for:

* Duplicate incoming fund reference blocked.
* Allocation cannot exceed available unassigned balance.
* MD cannot approve before GM.
* Requisition cannot exceed project/expense balance.
* Bill cannot exceed remaining billable amount.
* Wrong project requisition cannot be used for bill.
* Transfer cannot exceed source balance.

### Phase 10: Final Documentation

* Update root README.
* Update module README.
* Write short architecture explanation.
* Document assumptions and known limitations.
* Prepare screen recording demo.
