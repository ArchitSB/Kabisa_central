// Browser regression check with mocked API responses; never writes to a database.
// Pass a Playwright Page and the URL of a running admin Vite server.
const assert = {
  equal(actual, expected, message = 'Values differ') {
    if (actual !== expected) throw new Error(message);
  },
  deepEqual(actual, expected) {
    if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error('Request counts differ');
  },
  ok(value, message) { if (!value) throw new Error(message); },
};

module.exports = async function checkDeliveryAgentUI(page, baseURL = 'http://127.0.0.1:5179') {
  const origin = new URL(baseURL).origin;
  const calls = { creates: 0, edits: 0, uploads: 0 };
  const agents = [];
  let rejectUpload = true;
  await page.unrouteAll({ behavior: 'wait' });
  await page.addInitScript(() => {
    localStorage.setItem('kabisa-admin-auth', JSON.stringify({
      state: { accessToken: 'ui-test-only', refreshToken: null }, version: 0,
    }));
  });
  await page.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    if (url.pathname.endsWith('/auth/me')) {
      return route.fulfill({ json: {
        id: 'test-user', name: 'Test Staff', email: 'test@example.com', is_active: true,
        last_login_at: null,
        role: { id: 'test-role', name: 'manager', description: 'Test', is_system: true },
        permissions: ['delivery_agents.view', 'delivery_agents.create', 'delivery_agents.edit'],
      } });
    }
    if (url.pathname.includes('/api/v1/delivery-agents')) {
      if (url.pathname.endsWith('/id-proof')) {
        calls.uploads++;
        if (rejectUpload) {
          rejectUpload = false;
          return route.fulfill({ status: 503, json: { detail: 'Simulated upload failure' } });
        }
        agents[0].id_proof_path = 'delivery-agent-proofs/test.pdf';
        return route.fulfill({ json: agents[0] });
      }
      if (method === 'POST') {
        calls.creates++;
        const agent = {
          ...request.postDataJSON(), id: `test-agent-${calls.creates}`, id_proof_path: null,
          created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
        };
        agents.push(agent);
        return route.fulfill({ status: 201, json: agent });
      }
      if (method === 'PATCH') {
        calls.edits++;
        assert.ok(url.pathname.endsWith('/test-agent-1'), 'Retry must reuse the saved ID');
        Object.assign(agents[0], request.postDataJSON());
        return route.fulfill({ json: agents[0] });
      }
      return route.fulfill({ json: { items: agents, total: agents.length, page: 1, page_size: 100 } });
    }
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/health')) {
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 100 } });
    }
    return url.origin === origin ? route.continue() : route.abort();
  });
  await page.goto(`${origin}/delivery-agents`);
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill('Regression test rider');
  await page.getByLabel('Phone', { exact: true }).fill('0700000123');
  await page.getByLabel('Identity proof', { exact: true }).setInputFiles({
    name: 'identity.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4\nTest\n%%EOF'),
  });
  await page.getByRole('button', { name: 'Save agent', exact: true }).click();
  await page.getByRole('alert').filter({ hasText: 'Agent saved. Identity proof needs attention.' }).waitFor();
  assert.deepEqual(calls, { creates: 1, edits: 0, uploads: 1 });
  assert.equal(await page.getByLabel('Name', { exact: true }).inputValue(), 'Regression test rider');
  await page.getByRole('button', { name: 'Retry save & upload', exact: true }).click();
  await page.getByRole('dialog').waitFor({ state: 'hidden' });
  assert.deepEqual(calls, { creates: 1, edits: 1, uploads: 2 });
  assert.equal(agents.length, 1, 'Upload retry must not duplicate the agent');

  // Reopening Create must clear the previous identity/file and create a new record.
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  assert.equal(await page.getByLabel('Name', { exact: true }).inputValue(), '');
  assert.equal(await page.getByLabel('Identity proof', { exact: true }).inputValue(), '');
  await page.getByLabel('Name', { exact: true }).fill('Agent without proof');
  await page.getByLabel('Phone', { exact: true }).fill('0700000456');
  await page.getByRole('button', { name: 'Save agent', exact: true }).click();
  await page.getByRole('dialog').waitFor({ state: 'hidden' });
  assert.deepEqual(calls, { creates: 2, edits: 1, uploads: 2 });
  return { passed: true, checks: ['partial-save notice', 'retained form', 'retry without duplicates', 'create form reset', 'save without proof'], calls };
};
