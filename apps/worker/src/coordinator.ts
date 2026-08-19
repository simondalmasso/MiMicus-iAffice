import type { DurableObjectStateLike } from "./runtime-types.js";

export class AriaCoordinator {
  constructor(private readonly state: DurableObjectStateLike) {
    this.state.storage.sql.exec("CREATE TABLE IF NOT EXISTS coordinator_state (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)");
    this.state.storage.sql.exec("CREATE TABLE IF NOT EXISTS rate_windows (bucket TEXT PRIMARY KEY, window_start INTEGER NOT NULL, count INTEGER NOT NULL)");
  }
  put(key: string, value: unknown): { ok: true } { this.state.storage.sql.exec("INSERT INTO coordinator_state(key,value,updated_at) VALUES(?1,?2,datetime('now')) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",key,JSON.stringify(value)); return { ok: true }; }
  get(key: string): unknown { const rows=this.state.storage.sql.exec("SELECT value FROM coordinator_state WHERE key=?1",key).toArray() as Array<{value?:string}>; return rows[0]?.value?JSON.parse(rows[0].value):null; }
  checkRate(bucket: string, nowMs: number, limit: number, windowMs: number): { allowed: boolean; remaining: number } {
    const rows=this.state.storage.sql.exec("SELECT window_start,count FROM rate_windows WHERE bucket=?1",bucket).toArray() as Array<{window_start?:number;count?:number}>; const current=rows[0]; const start=current?.window_start??nowMs; const reset=nowMs-start>=windowMs; const count=reset?0:(current?.count??0); const next=count+1;
    this.state.storage.sql.exec("INSERT INTO rate_windows(bucket,window_start,count) VALUES(?1,?2,?3) ON CONFLICT(bucket) DO UPDATE SET window_start=excluded.window_start,count=excluded.count",bucket,reset?nowMs:start,next); return {allowed:next<=limit,remaining:Math.max(0,limit-next)};
  }
  async fetch(request: Request): Promise<Response> { const url=new URL(request.url); if(request.method==="POST"&&url.pathname==="/rate"){const body=await request.json() as {bucket?:string;limit?:number;windowMs?:number;nowMs?:number};if(!body.bucket||!Number.isFinite(body.limit)||!Number.isFinite(body.windowMs))return Response.json({error:"RATE_SCHEMA_INVALID"},{status:400});return Response.json(this.checkRate(body.bucket,body.nowMs??Date.now(),Number(body.limit),Number(body.windowMs)));}return Response.json({error:"NOT_FOUND"},{status:404}); }
}
