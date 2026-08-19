import type { ActionIntent, EffectReceipt } from "../../core/src/types.js";
import type { D1Like } from "../../memory/src/store.js";
import type { ReceiptStore } from "./kernel.js";

export class D1ReceiptStore implements ReceiptStore {
  constructor(private readonly db: D1Like) {}
  async findByIdempotencyKey(key: string): Promise<EffectReceipt | undefined> {
    const row = await this.db.prepare("SELECT receipt_json FROM effect_receipts WHERE idempotency_key=?1 AND status='EXECUTED' LIMIT 1").bind(key).first<{receipt_json:string}>();
    return row ? JSON.parse(row.receipt_json) as EffectReceipt : undefined;
  }
  async persist(receipt: EffectReceipt, intentStatus: ActionIntent["status"]): Promise<void> {
    await this.db.batch([
      this.db.prepare("INSERT INTO effect_receipts (receipt_id,intent_id,action_digest,idempotency_key,connector,operation,status,result_hash,executed_at,attempt,detail,receipt_json) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12) ON CONFLICT(idempotency_key) DO UPDATE SET status=excluded.status,result_hash=excluded.result_hash,executed_at=excluded.executed_at,attempt=excluded.attempt,detail=excluded.detail,receipt_json=excluded.receipt_json").bind(receipt.receiptId,receipt.intentId,receipt.actionDigest,receipt.idempotencyKey,receipt.connector,receipt.operation,receipt.status,receipt.resultHash,receipt.executedAt,receipt.attempt,receipt.detail,JSON.stringify(receipt)),
      this.db.prepare("UPDATE action_intents SET status=?1 WHERE intent_id=?2").bind(intentStatus,receipt.intentId),
      this.db.prepare("INSERT INTO events (id,type,observed_at,created_at,source,actor,idempotency_key,hash,trust,evidence_type,payload_json) VALUES (?1,'effect_result',?2,?2,'aria-effects','SYSTEM',?3,?4,'TRUSTED_INTERNAL','LIVE_DEPLOYED',?5) ON CONFLICT(id) DO NOTHING").bind(`effect-result:${receipt.receiptId}`,receipt.executedAt,`effect-result:${receipt.idempotencyKey}`,receipt.resultHash,JSON.stringify(receipt))
    ]);
  }
}
