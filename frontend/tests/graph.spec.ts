import { expect, test } from '@playwright/test'

test('loads the canonical backend projection and inspects executor scope', async ({ page }) => {
  const fixtureRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/fixtures/')) {
      fixtureRequests.push(request.url())
    }
  })

  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'merge-marshal-demo-api' })).toBeVisible()
  await expect(page.locator('.architecture-node')).toHaveCount(5)
  await expect(page.locator('.react-flow__edge')).toHaveCount(3)
  await expect(page.getByText('Depth 1')).toBeVisible()

  await page.getByLabel('User Domain, component').click()
  const details = page.getByLabel('Node details')
  await expect(details.getByRole('heading', { name: 'User Domain' })).toBeVisible()
  await expect(details.getByText('src/demo_app/schemas/user.py', { exact: true })).toBeVisible()
  await expect(details.getByText('primary', { exact: true }).first()).toBeVisible()
  expect(fixtureRequests).toEqual([])
})

test('drills into a component and returns through the hierarchy breadcrumb', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('User Domain, component').click()
  await page.getByRole('button', { name: 'Explore this component' }).click()

  const hierarchy = page.getByRole('navigation', { name: 'Graph hierarchy' })
  await expect(hierarchy.getByRole('button', { name: 'User Domain' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  await expect(page.locator('.architecture-node')).toHaveCount(5)
  await expect(page.getByLabel('User Endpoint, service')).toBeVisible()
  await expect(page.getByLabel('User Service, service')).toBeVisible()
  await expect(page.getByLabel('User Response Schema, component')).toBeVisible()

  await page.getByLabel('User Response Schema, component').click()
  const details = page.getByLabel('Node details')
  await expect(details.getByText('UserResponse.user_id', { exact: true })).toBeVisible()
  await expect(details.getByText('shared', { exact: true })).toBeVisible()

  await hierarchy.getByRole('button', { name: 'Architecture' }).click()
  await expect(page.getByLabel('Payment Domain, component')).toBeVisible()
  await expect(page.locator('.architecture-node')).toHaveCount(5)
})

test('shows the derived plan, blocking reason, and conditional schedule', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chrome')
  await page.goto('/')

  const plan = page.getByLabel('Coordination plan')
  await expect(plan.getByRole('button', { name: /Rename the canonical user identity/ })).toContainText('READY')
  await expect(plan.getByRole('button', { name: /Add user caching/ })).toContainText(
    'BLOCKED · replan required',
  )
  await expect(plan.getByRole('button', { name: /structured payment logging/i })).toContainText('READY')
  await expect(plan.getByText('A + C', { exact: true })).toBeVisible()
  await expect(plan.getByText('A compatible replanned contract is required')).toBeVisible()

  await plan.getByRole('button', { name: /Add user caching/ }).click()
  await expect(plan.getByText('Blocking conflict')).toBeVisible()
  await expect(plan).toContainText('retires a resource that task-b still consumes')
})

test('renders proposed architecture without treating it as verified graph data', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chrome')
  await page.goto('/')

  await page.getByLabel('Coordination plan').getByRole('button', { name: /Add user caching/ }).click()
  const proposedCache = page.getByLabel('User Cache, store')
  await expect(proposedCache).toBeVisible()
  await expect(proposedCache).toHaveClass(/is-proposed/)
  await expect(page.locator('.react-flow__edge.is-proposed-edge')).toHaveCount(1)

  await proposedCache.click()
  const details = page.getByLabel('Node details')
  await expect(details.getByText('Proposed change')).toBeVisible()
  await expect(details).toContainText('No verified artifact exists yet')
})

test('remaps one canonical task impact when the hierarchy projection changes', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chrome')
  await page.goto('/')

  const userDomain = page.getByLabel('User Domain, component')
  await expect(userDomain).toHaveClass(/impact-direct/)
  await userDomain.click()
  await page.getByRole('button', { name: 'Explore this component' }).click()

  const schema = page.getByLabel('User Response Schema, component')
  await expect(schema).toHaveClass(/impact-direct/)
  await schema.click()
  await expect(page.getByLabel('Node details')).toContainText('Task A impact')
  await expect(page.getByLabel('Node details')).toContainText(
    'The renamed symbol belongs to the response schema',
  )
})

test('opens aggregated edge evidence in the details panel', async ({ page }) => {
  await page.goto('/')

  const edge = page.locator(
    '.react-flow__edge[data-id="projected-api-entrypoint-serves-user-domain"]',
  )
  await edge.dispatchEvent('click')

  const details = page.getByLabel('Edge details')
  await expect(details.getByRole('heading', { name: 'serves' })).toBeVisible()
  await expect(details.getByText('Dispatches user requests')).toBeVisible()
  await expect(details.getByText('src/demo_app/app.py', { exact: true })).toBeVisible()
  await expect(details.getByText('Canonical edges').locator('..')).toContainText('1')
})

test('keeps relationship labels clear of nodes and one another', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chrome')
  await page.goto('/')

  const collisions = await page.evaluate(() => {
    const labels = [...document.querySelectorAll<HTMLElement>('[data-edge-label]')].map(
      (element) => ({ id: element.dataset.edgeLabel, bounds: element.getBoundingClientRect() }),
    )
    const nodes = [...document.querySelectorAll<HTMLElement>('.architecture-node')].map(
      (element) => ({ id: element.ariaLabel, bounds: element.getBoundingClientRect() }),
    )
    const intersects = (first: DOMRect, second: DOMRect) =>
      Math.min(first.right, second.right) > Math.max(first.left, second.left) &&
      Math.min(first.bottom, second.bottom) > Math.max(first.top, second.top)

    return {
      labels: labels.flatMap((label, index) =>
        labels
          .slice(index + 1)
          .filter((candidate) => intersects(label.bounds, candidate.bounds))
          .map((candidate) => [label.id, candidate.id]),
      ),
      nodes: labels.flatMap((label) =>
        nodes
          .filter((node) => intersects(label.bounds, node.bounds))
          .map((node) => [label.id, node.id]),
      ),
    }
  })

  expect(collisions).toEqual({ labels: [], nodes: [] })
})

test('shows a clear backend error', async ({ page }) => {
  await page.route('**/api/graph?**', (route) =>
    route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'graph is invalid' }),
    }),
  )

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Architecture unavailable' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('graph is invalid')
})

test('rejects a malformed backend graph response', async ({ page }) => {
  await page.route('**/api/graph?**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ schema_version: '0.1', nodes: [], edges: [] }),
    }),
  )

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Architecture unavailable' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('canonical projection contract')
})
