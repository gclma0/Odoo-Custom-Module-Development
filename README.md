# Odoo Custom Module Development

## Project Overview

This repository contains an Odoo 17 Community custom module project for `nn_fund_management`.

The module covers the main fund management lifecycle requested in the technical assessment:

- fund accounts
- incoming funds
- fund allocations
- fund requisitions
- fund bills
- fund transfers
- configurable approvals
- approval and audit history
- company-based access control
- computed balance tracking

Current Odoo version:
- `Odoo 17 Community`

Module technical name:
- `nn_fund_management`

## Prerequisites

- Docker Desktop
- Docker Compose
- Git

## Installation

1. Clone the repository.
2. Start Docker Desktop.
3. From the project root, run:

```powershell
docker compose up -d
```

4. Open Odoo at `http://localhost:8069`.
5. Create or open a database.
6. Install `NN Fund Management` from Apps.

## Docker Setup

The stack includes:

- `postgres:15`
- `odoo:17.0`

Project files used by Docker:

- `docker-compose.yml`
- `config/odoo.conf`

Useful commands:

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail 200 odoo
docker compose restart odoo
```

## Module Installation

1. Open `Apps` in Odoo.
2. Remove the default Apps filter if needed.
3. Search for `NN Fund Management`.
4. Click `Install`.

If code changes were made and you need to reload the module:

```powershell
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d fund_management_db -u nn_fund_management --stop-after-init
docker compose restart odoo
```

## Required Dependencies

The module depends on:

- `base`
- `mail`
- `project`

## Configuration Steps

Minimum configuration for normal workflow testing:

1. Create or review users and assign groups:
   - `Fund User`
   - `Finance User`
   - `GM Approver`
   - `MD Approver`
   - `Fund Administrator`
2. Create approval configurations for:
   - fund allocation
   - fund requisition
   - fund transfer
3. Use the demo records or create your own:
   - `Main Fund Account`
   - `Project A`
   - `Project B`
   - expense heads

## Testing

Automated test command:

```powershell
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d fund_management_db -u nn_fund_management --test-enable --test-tags nn_fund_management --http-port=8070 --stop-after-init
```

Current automated tests cover:

- duplicate incoming transaction reference blocking
- over-allocation blocking
- self-approval blocking
- requisition over-request blocking
- bill overbilling blocking
- wrong-project bill blocking
- transfer over-limit blocking
- same source and destination transfer blocking

Manual functional test flow:

1. confirm an incoming fund
2. allocate funds to Project A
3. create and approve a requisition
4. post a partial bill
5. create and approve a transfer to Project B

## Assumptions

- the module uses a custom bill model instead of Odoo vendor bills
- approval rules are configured per request type, company, and amount range
- projects without an explicit company can still be used when there is no conflicting company value
- reversals are blocked when downstream balances have already consumed the amount being reversed

## Known Limitations

- dashboard and notifications are not implemented
- bank email integration is not implemented
- approval workflow model supports an optional `Finance` level even though the minimum required chain is `GM -> MD`
- some reversal flows are intentionally conservative to preserve balance integrity
- audit history is implemented through a generalized custom audit model rather than a full accounting journal structure
