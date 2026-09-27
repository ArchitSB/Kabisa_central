import assert from "node:assert/strict";
import test from "node:test";
import {
  cartItemSchema,
  cartSummary,
  canCancelOrder,
  mergeCart,
  normalizePhone,
  parseQuickOrder,
  passwordSchema,
  phoneSchema,
} from "./index";
const id = "a616ad13-a9ef-4b12-8e3c-33d369407d13";
test("cart maths uses decimal minor units and hides unknown prices", () => {
  assert.equal(
    cartSummary([{ product_id: id, quantity: 3, unit_price: "0.10" }]).subtotal,
    0.3,
  );
  assert.deepEqual(
    cartSummary([{ product_id: id, quantity: 4, unit_price: null }]),
    { quantity: 4, subtotal: null },
  );
  assert.equal(cartSummary([]).subtotal, 0);
});
test("cart contract refuses client money and invalid quantities", () => {
  for (const quantity of [0, -1, 1.5, 100001])
    assert.equal(
      cartItemSchema.safeParse({ product_id: id, quantity }).success,
      false,
    );
  assert.equal(
    cartItemSchema.safeParse({ product_id: id, quantity: 1, price: 0.01 })
      .success,
    false,
  );
  assert.deepEqual(
    mergeCart(
      [{ product_id: id, quantity: 4 }],
      [{ product_id: id, quantity: 2 }],
    ),
    [{ product_id: id, quantity: 6 }],
  );
});
test("quick order handles pasted CSV, tabs, multipliers and invalid quantities", () => {
  const result = parseQuickOrder(
    "PARA-500, 10\nAmoxicillin x 5\nVitamin C\t12\nTest -2\nDevice, 1.5",
  );
  assert.deepEqual(
    result.slice(0, 3).map(({ query, quantity }) => ({ query, quantity })),
    [
      { query: "PARA-500", quantity: 10 },
      { query: "Amoxicillin", quantity: 5 },
      { query: "Vitamin C", quantity: 12 },
    ],
  );
  assert.equal(result[3].error, "quantity");
  assert.equal(result[4].error, "quantity");
  assert.throws(
    () => parseQuickOrder(Array(101).fill("PARA 1").join("\n")),
    /100/,
  );
});
test("native-safe contact and password schemas match server limits", () => {
  assert.equal(normalizePhone("0712 345 678"), "+255712345678");
  assert.equal(phoneSchema.safeParse("255712345678").success, true);
  assert.equal(phoneSchema.safeParse("hello@example.com").success, false);
  assert.equal(passwordSchema.safeParse("💊".repeat(19)).success, false);
  assert.equal(passwordSchema.safeParse("💊".repeat(18)).success, true);
  assert.equal(canCancelOrder("PENDING"), true);
  assert.equal(canCancelOrder("APPROVED"), false);
});
