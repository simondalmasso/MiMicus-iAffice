# MiMicus Commercial Action Goal V1

ROLE=ARQ
BASE_SHA=81266bd94d1194cec735690959f18f90fb732c6d
BRANCH=arq/commercial-action-goal-v1
INTEGRATION_OWNER=ARQ commercial action goal

## Problem

`CommercialActionTicket` already tells a human closer what action is next, but it does not encode what observable transition counts as success. That makes execution auditable but leaves feedback/closure criteria implicit.

## Goal

Bind each `WORK_NOW` action ticket to one deterministic success target without generating sales copy, calling a model, sending a message, or issuing effect approval.

## Model

Add frozen `CommercialActionGoal`:

- `code`
- `target_lead_stage`
- `target_commercial_stages`
- `requires_stage_evidence`

Goal codes:

- `obtain_reply`
- `qualify`
- `advance_to_proposal`
- `resolve_proposal`

## Deterministic mapping

| next action / state | goal | success |
| --- | --- | --- |
| CONTACT | obtain_reply | LeadStage.REPLIED |
| QUALIFY | qualify | CommercialStage.QUALIFIED + matching evidence |
| PROPOSE | advance_to_proposal | CommercialStage.PROPOSAL + matching evidence |
| FOLLOW_UP while proposal | resolve_proposal | CommercialStage.WON or LOST + matching evidence |
| FOLLOW_UP before proposal | obtain_reply | LeadStage.REPLIED |

WAIT/NONE do not create `WORK_NOW` tickets and therefore have no action goal.

## Authority

- goal is derived only by `DeterministicLeadDecisionService`;
- source/setter cannot provide it;
- goal is bound into `ticket_hash` and therefore the batch hash;
- goal is success criteria, not permission to act;
- `requires_human_approval=true` remains unchanged;
- effect authorization remains independent.

## Non-goals

- message drafting;
- persuasion strategy;
- automatic send;
- provider call;
- CRM mutation;
- changing ranking or lane WIP;
- adding a closer-agent framework.
