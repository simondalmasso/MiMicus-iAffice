import { stableId } from "./hash.js";
import type { SystemState, Task } from "./types.js";

export type ScheduledJobName = "business_tick" | "daily_ceo" | "nightly_memory" | "weekly_security";

const priority: Record<ScheduledJobName, number> = {
  business_tick: 20,
  daily_ceo: 90,
  nightly_memory: 40,
  weekly_security: 100
};

export class Scheduler {
  constructor(private readonly state: SystemState) {}

  async enqueue(name: ScheduledJobName, slot: string): Promise<{ task: Task; duplicate: boolean }> {
    const id = await stableId("scheduled-task", { name, slot });
    const existing = this.state.tasks.find((task) => task.id === id);
    if (existing) return { task: existing, duplicate: true };
    const task: Task = {
      id,
      type: name,
      priority: priority[name],
      risk: name === "weekly_security" ? "HIGH" : "LOW",
      status: "QUEUED",
      requestedBy: "SYSTEM",
      input: { scheduleSlot: slot },
      createdAt: slot
    };
    this.state.tasks.push(task);
    return { task, duplicate: false };
  }

  defer(taskId: string, reason: string): boolean {
    const task = this.state.tasks.find((item) => item.id === taskId);
    if (!task) return false;
    task.status = "DEFERRED";
    task.input = { ...task.input, deferredReason: reason };
    return true;
  }
}
