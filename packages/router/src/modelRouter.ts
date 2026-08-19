import { sha256, stableId } from "../../core/src/hash.js";
import type { AgentRole, ModelCallRecord, ModelTier } from "../../core/src/types.js";
import { BudgetGovernor } from "./budgetGovernor.js";

export const FREE_MODEL_ALLOWLIST = [
  "@cf/zai-org/glm-4.7-flash",
  "@cf/qwen/qwen3-30b-a3b-fp8",
  "@cf/openai/gpt-oss-20b",
  "@cf/openai/gpt-oss-120b",
  "@cf/nvidia/nemotron-3-120b-a12b"
] as const;

export const PAID_MODEL_DENYLIST = [
  "@cf/zai-org/glm-5.2",
  "@cf/moonshotai/kimi-k2.6",
  "@cf/moonshotai/kimi-k2.7-code"
] as const;

export interface ModelRequest {
  role: AgentRole;
  taskId: string;
  tier: ModelTier;
  prompt: string;
  reason: string;
  critical?: boolean;
}

export interface ModelProviderResult { text: string; inputTokens: number; outputTokens: number; latencyMs: number; }
export interface ModelProvider { run(modelId: string, prompt: string): Promise<ModelProviderResult>; }

export class FakeModelProvider implements ModelProvider {
  async run(modelId: string, prompt: string): Promise<ModelProviderResult> {
    const normalized = prompt.replace(/\s+/g, " ").trim();
    return { text: `FAKE:${modelId}:${normalized.slice(0, 120)}`, inputTokens: Math.ceil(normalized.length / 4), outputTokens: 24, latencyMs: 1 };
  }
}

export interface WorkersAiBinding { run(model: string, input: Record<string, unknown>): Promise<unknown>; }
export class WorkersAiProvider implements ModelProvider {
  constructor(private readonly ai: WorkersAiBinding) {}
  async run(modelId: string, prompt: string): Promise<ModelProviderResult> {
    const started = Date.now();
    try {
      const raw = await this.ai.run(modelId, { prompt, max_tokens: 256, temperature: 0 });
      const obj = raw as Record<string, unknown>;
      const response = String(obj.response ?? obj.result ?? JSON.stringify(raw));
      const usage = (obj.usage ?? {}) as Record<string, unknown>;
      return {
        text: response,
        inputTokens: Number(usage.prompt_tokens ?? usage.input_tokens ?? Math.ceil(prompt.length / 4)),
        outputTokens: Number(usage.completion_tokens ?? usage.output_tokens ?? Math.ceil(response.length / 4)),
        latencyMs: Date.now() - started
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      if (/3036|free allocation|quota|429/i.test(message)) throw new Error("FREE_QUOTA_EXHAUSTED");
      if (/5035|paid plan|403/i.test(message)) throw new Error("PAID_MODEL_FORBIDDEN_OR_ACCOUNT_DENIED");
      throw error;
    }
  }
}

const neuronsPerMillion: Record<string, { input: number; output: number }> = {
  "@cf/qwen/qwen3-30b-a3b-fp8": { input: 4625, output: 30475 },
  "@cf/openai/gpt-oss-20b": { input: 18182, output: 27273 },
  "@cf/openai/gpt-oss-120b": { input: 31818, output: 68182 },
  "@cf/zai-org/glm-4.7-flash": { input: 5500, output: 36364 },
  "@cf/nvidia/nemotron-3-120b-a12b": { input: 32000, output: 65000 }
};

export class ModelRouter {
  constructor(private readonly provider: ModelProvider, private readonly budget: BudgetGovernor) {}

  select(tier: ModelTier, role: AgentRole): string {
    if (tier === "T0") return "NO_MODEL";
    if (tier === "T4") throw new Error("EXTERNAL_PROVIDER_DISABLED_BY_DEFAULT");
    if (tier === "T1") return "@cf/zai-org/glm-4.7-flash";
    if (tier === "T2") return role === "DEV" ? "@cf/openai/gpt-oss-20b" : "@cf/qwen/qwen3-30b-a3b-fp8";
    return role === "DEV" ? "@cf/nvidia/nemotron-3-120b-a12b" : "@cf/openai/gpt-oss-120b";
  }

  async run(request: ModelRequest): Promise<{ text: string; record: ModelCallRecord }> {
    if (request.tier === "T0") throw new Error("T0_MUST_NOT_CALL_MODEL");
    const modelId = this.select(request.tier, request.role);
    if ((PAID_MODEL_DENYLIST as readonly string[]).includes(modelId)) throw new Error("PAID_MODEL_DENIED");
    if (!(FREE_MODEL_ALLOWLIST as readonly string[]).includes(modelId)) throw new Error("MODEL_NOT_FREE_ALLOWLISTED");
    if (this.budget.state("ai_neurons") === "HARD_CAP") throw new Error("FREE_QUOTA_HARD_CAP:ai_neurons");
    const result = await this.provider.run(modelId, request.prompt);
    const rate = neuronsPerMillion[modelId] ?? { input: 50_000, output: 100_000 };
    const estimatedNeurons = (result.inputTokens * rate.input + result.outputTokens * rate.output) / 1_000_000;
    const quotaState = this.budget.consume("ai_neurons", estimatedNeurons, request.critical === true);
    const textHash = await sha256(result.text);
    const record: ModelCallRecord = {
      id: await stableId("model", { taskId: request.taskId, modelId, textHash }), role: request.role, taskId: request.taskId,
      modelId, tier: request.tier, inputTokens: result.inputTokens, outputTokens: result.outputTokens, estimatedNeurons,
      latencyMs: result.latencyMs, reasonSelected: request.reason, resultHash: textHash,
      quotaState: quotaState === "OK" ? "OK" : quotaState
    };
    return { text: result.text, record };
  }
}
