export class BudgetLedger {
  constructor(entropyFreeze = 4.5) {
    this.entropyFreeze = entropyFreeze;
    this.futures = new Map();
  }
  mint(id, maxTokens) {
    if (maxTokens < 1) throw new Error("max_tokens");
    if (this.futures.has(id)) throw new Error("EXISTS");
    this.futures.set(id, { maxTokens, spent: 0, frozen: false, freezeReason: null });
  }
  spend(id, tokens, entropy = null) {
    const f = this.futures.get(id);
    if (f.frozen) return { status: "FROZEN", remaining: f.maxTokens - f.spent, reason: f.freezeReason };
    if (tokens < 1) return { status: "REFUSED", remaining: f.maxTokens - f.spent, reason: "BAD_SPEND" };
    if (tokens > f.maxTokens - f.spent) return { status: "REFUSED", remaining: f.maxTokens - f.spent, reason: "OVER_BUDGET" };
    if (entropy != null && entropy >= this.entropyFreeze) {
      f.frozen = true; f.freezeReason = "ENTROPY_SPIKE";
      return { status: "FROZEN", remaining: f.maxTokens - f.spent, reason: "ENTROPY_SPIKE" };
    }
    f.spent += tokens;
    return { status: "OK", remaining: f.maxTokens - f.spent, reason: null };
  }
}
