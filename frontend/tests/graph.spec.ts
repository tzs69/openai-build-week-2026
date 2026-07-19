import { expect, test } from '@playwright/test'

test('renders every architecture node and edge', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'test_repo_2' })).toBeVisible()
  await expect(page.locator('.architecture-node')).toHaveCount(10)
  await expect(page.locator('.react-flow__edge')).toHaveCount(17)
  await expect(page.locator('[data-edge-label]')).toHaveCount(17)
  await expect(page.locator('.architecture-node__footer')).toHaveCount(0)
  await expect(page.getByLabel('Web Client, entrypoint')).toHaveCount(0)
  await expect(page.getByLabel('API Server, service')).toHaveCount(0)
  await expect(page.getByText('Generation warnings')).toHaveCount(0)
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

test('opens node and edge evidence in the details panel', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('Routing & Application Shell, component').click()
  const details = page.getByLabel('Node details')
  await expect(details.getByRole('heading', { name: 'Routing & Application Shell' })).toBeVisible()
  await expect(details.getByText('client/src/main.tsx', { exact: true })).toBeVisible()
  await expect(details.getByText(/Reverse index:/)).toHaveCount(0)

  const edge = page.locator('.react-flow__edge[data-id="client-auth-calls-server-auth"]')
  await edge.dispatchEvent('click')
  const edgeDetails = page.getByLabel('Edge details')
  await expect(edgeDetails.getByRole('heading', { name: 'calls' })).toBeVisible()
  await expect(edgeDetails.getByText('client-authentication', { exact: true })).toBeVisible()
  await expect(edgeDetails.getByText('server-authentication', { exact: true })).toBeVisible()
})

test('supports optional structured warnings', async ({ page }) => {
  await page.route('**/fixtures/test-repo-2/graph.json', async (route) => {
    const response = await route.fetch()
    const graph = await response.json()
    await route.fulfill({
      response,
      json: {
        ...graph,
        warnings: [{ type: 'test_warning', message: 'Fixture warning' }],
      },
    })
  })

  await page.goto('/')
  await expect(page.locator('.architecture-node')).toHaveCount(10)
  await page.getByLabel('Routing & Application Shell, component').click()
  await expect(page.getByText('Generation warnings')).toBeVisible()
  await expect(page.getByText('Fixture warning')).toBeVisible()
})

test('shows a clear fixture-load error', async ({ page }) => {
  await page.route('**/fixtures/test-repo-2/graph.json', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  )

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Architecture unavailable' })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('Unable to load')
})
