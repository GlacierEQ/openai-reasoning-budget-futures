import { BudgetLedger } from "./budget_futures.mjs";
import assert from "node:assert/strict";
const led = new BudgetLedger(3.0);
led.mint("f1", 100);
assert.equal(led.spend("f1", 120).status, "REFUSED");
assert.equal(led.spend("f1", 10, 4.0).status, "FROZEN");
assert.equal(led.spend("f1", 1).status, "FROZEN");
console.log("ok");
