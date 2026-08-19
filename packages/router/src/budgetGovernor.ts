import type { QuotaResource } from "../../core/src/types.js";

export interface ResourceCap { soft: number; hard: number; officialFree: number; }
export type BudgetState = "OK" | "SOFT_CAP" | "HARD_CAP";

export const DEFAULT_CAPS: Record<QuotaResource, ResourceCap> = {
  worker_requests: { soft: 70_000, hard: 85_000, officialFree: 100_000 },
  d1_rows_read: { soft: 3_500_000, hard: 4_250_000, officialFree: 5_000_000 },
  d1_rows_write: { soft: 65_000, hard: 80_000, officialFree: 100_000 },
  queue_ops: { soft: 6_500, hard: 8_000, officialFree: 10_000 },
  workflow_steps: { soft: 2_000, hard: 2_400, officialFree: 3_000 },
  ai_neurons: { soft: 7_500, hard: 8_500, officialFree: 10_000 }
};

export class BudgetGovernor {
  private usage = new Map<QuotaResource, number>();
  constructor(readonly caps: Record<QuotaResource, ResourceCap> = DEFAULT_CAPS) {
    for (const [resource, cap] of Object.entries(caps) as Array<[QuotaResource, ResourceCap]>) {
      if (cap.hard > cap.officialFree * 0.85) throw new Error(`CAP_EXCEEDS_85_PERCENT:${resource}`);
      if (cap.soft > cap.hard) throw new Error(`SOFT_CAP_EXCEEDS_HARD:${resource}`);
      this.usage.set(resource, 0);
    }
  }

  current(resource: QuotaResource): number { return this.usage.get(resource) ?? 0; }

  state(resource: QuotaResource, additional = 0): BudgetState {
    const value = this.current(resource) + additional;
    const cap = this.caps[resource];
    if (value >= cap.hard) return "HARD_CAP";
    if (value >= cap.soft) return "SOFT_CAP";
    return "OK";
  }

  consume(resource: QuotaResource, amount: number, critical = false): BudgetState {
    if (!Number.isFinite(amount) || amount < 0) throw new Error("INVALID_BUDGET_AMOUNT");
    const nextState = this.state(resource, amount);
    if (nextState === "HARD_CAP" && !critical) throw new Error(`FREE_QUOTA_HARD_CAP:${resource}`);
    this.usage.set(resource, this.current(resource) + amount);
    return nextState;
  }

  reset(): void { for (const resource of this.usage.keys()) this.usage.set(resource, 0); }

  snapshot(): Record<QuotaResource, { used: number; soft: number; hard: number; officialFree: number; state: BudgetState }> {
    const out = {} as Record<QuotaResource, { used: number; soft: number; hard: number; officialFree: number; state: BudgetState }>;
    for (const [resource, cap] of Object.entries(this.caps) as Array<[QuotaResource, ResourceCap]>) {
      out[resource] = { used: this.current(resource), ...cap, state: this.state(resource) };
    }
    return out;
  }
}
