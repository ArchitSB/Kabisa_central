import assert from "node:assert/strict";
import test from "node:test";
import {
  ApiError,
  createApiClient,
  type Tokens,
  type TransportResponse,
} from "./index";
const response = (status: number, body: unknown): TransportResponse => ({
  status,
  ok: status >= 200 && status < 300,
  json: async () => body,
});
test("concurrent expiry rotates once, retries with new bearer and preserves headers", async () => {
  let tokens: Tokens | null = { access_token: "old", refresh_token: "secret" };
  let rotations = 0;
  const client = createApiClient({
    baseUrl: "https://api.example/store/",
    tokens: {
      get: () => tokens,
      set: (v) => {
        tokens = v;
      },
    },
    fetch: async (url, options) => {
      if (url.endsWith("/auth/refresh")) {
        rotations++;
        await new Promise((r) => setTimeout(r, 5));
        return response(200, { access_token: "new", refresh_token: "rotated" });
      }
      if (options?.headers?.Authorization === "Bearer old")
        return response(401, {});
      if (url.endsWith("/orders"))
        assert.equal(options?.headers?.["Idempotency-Key"], "same-key");
      return response(200, { ok: true });
    },
  });
  await Promise.all([
    client.get("/me"),
    client.get("/auth/sessions"),
    client.post(
      "/orders",
      { address_id: "owned" },
      { "Idempotency-Key": "same-key" },
    ),
  ]);
  assert.equal(rotations, 1);
  assert.equal(tokens?.refresh_token, "rotated");
});
test("failed refresh clears session and preserves structured error", async () => {
  let cleared = false;
  const client = createApiClient({
    baseUrl: "https://api.example",
    tokens: {
      get: () => ({ access_token: "bad", refresh_token: "revoked" }),
      set: (v) => {
        cleared = v === null;
      },
    },
    fetch: async () =>
      response(401, { code: "invalid_refresh", detail: "Sign in again." }),
  });
  await assert.rejects(
    client.get("/me"),
    (e) =>
      e instanceof ApiError &&
      e.code === "invalid_refresh" &&
      e.message === "Your session has expired. Please sign in again.",
  );
  assert.equal(cleared, true);
});
test("login never rotates and 204 does not parse JSON", async () => {
  const paths: string[] = [];
  const client = createApiClient({
    baseUrl: "https://api.example",
    tokens: {
      get: () => ({ access_token: "old", refresh_token: "old" }),
      set: () => {},
    },
    fetch: async (url) => {
      paths.push(url);
      return url.endsWith("/auth/login")
        ? response(401, { code: "invalid_credentials", detail: "Try again." })
        : {
            status: 204,
            ok: true,
            json: async () => {
              throw Error("no body");
            },
          };
    },
  });
  await assert.rejects(client.post("/auth/login", {}), ApiError);
  assert.equal(paths.length, 1);
  assert.equal(await client.delete("/cart"), undefined);
});
test("late 401 reuses an already refreshed token", async () => {
  let current: Tokens = { access_token: "old", refresh_token: "old" };
  let rotated = 0;
  const client = createApiClient({
    baseUrl: "https://api.example",
    tokens: {
      get: () => current,
      set: (v) => {
        current = v!;
      },
    },
    fetch: async (url, opts) => {
      if (url.endsWith("/auth/refresh")) {
        rotated++;
        return response(200, { access_token: "new", refresh_token: "new" });
      }
      if (opts?.headers?.Authorization === "Bearer old") {
        if (url.endsWith("/slow")) await new Promise((r) => setTimeout(r, 20));
        return response(401, {});
      }
      return response(200, {});
    },
  });
  await Promise.all([client.get("/slow"), client.get("/fast")]);
  assert.equal(rotated, 1);
});

test("transient GET retries once; writes and other HTTP failures never retry", async () => {
  for (const method of ["GET", "POST", "PATCH", "DELETE"]) {
    let calls = 0;
    const client = createApiClient({
      baseUrl: "https://offline.invalid",
      tokens: { get: () => null, set: () => {} },
      fetch: async () => {
        calls++;
        return { ...response(503, {}), headers: { get: () => "request-123" } };
      },
    });
    await assert.rejects(
      client.request("/example", { method }),
      (error) =>
        error instanceof ApiError &&
        error.status === 503 &&
        error.requestId === "request-123",
    );
    assert.equal(calls, method === "GET" ? 2 : 1);
  }
  for (const status of [400, 401, 403, 500]) {
    let calls = 0;
    const client = createApiClient({
      baseUrl: "https://offline.invalid",
      tokens: { get: () => null, set: () => {} },
      fetch: async () => {
        calls++;
        return response(status, {});
      },
    });
    await assert.rejects(client.get("/example"), ApiError);
    assert.equal(calls, 1);
  }
});

test("network errors retry once and timeout overrides abort without retrying writes", async () => {
  let calls = 0;
  const client = createApiClient({
    baseUrl: "https://offline.invalid",
    timeoutMs: 10000,
    tokens: { get: () => null, set: () => {} },
    fetch: async (_url, init) => {
      calls++;
      if (init?.method === "GET") throw new TypeError("Network unavailable");
      return new Promise((_resolve, reject) =>
        init?.signal?.addEventListener(
          "abort",
          () => reject(new Error("aborted")),
          { once: true },
        ),
      );
    },
  });
  await assert.rejects(
    client.get("/example"),
    (error) => error instanceof ApiError && error.code === "network",
  );
  assert.equal(calls, 2);
  calls = 0;
  await assert.rejects(
    client.request("/example", { method: "POST", timeoutMs: 5 }),
    (error) => error instanceof ApiError && error.code === "timeout",
  );
  assert.equal(calls, 1);
});
