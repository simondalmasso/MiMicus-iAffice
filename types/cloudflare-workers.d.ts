declare module "cloudflare:workers" {
  export interface WorkflowEvent<P = unknown> { payload: P; }
  export interface WorkflowStep {
    do<T>(name: string, callback: () => Promise<T>): Promise<T>;
    sleep(name: string, duration: number | string): Promise<void>;
    waitForEvent<T = unknown>(name: string, options: { type: string; timeout?: number | string }): Promise<{ payload: T }>;
  }
  export class WorkflowEntrypoint<Env = unknown, Params = unknown> {
    protected env: Env;
    constructor(ctx: unknown, env: Env);
    run(event: WorkflowEvent<Params>, step: WorkflowStep): Promise<unknown>;
  }
}
