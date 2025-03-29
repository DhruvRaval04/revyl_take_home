import { test } from '@playwright/test'
import { ai } from '@zerostep/playwright'

test.describe('ZeroStep AI Tests', () => {
  test('should navigate to ZeroStep and get header text', async ({ page }) => {
    await page.goto('https://zerostep.com/')
    const aiArgs = { page, test }
    
    // Get the header text using AI
    const headerText = await ai('Get the header text', aiArgs)
    console.log('Header text:', headerText)
  })

  test('should perform Google search using ZeroStep', async ({ page }) => {
    await page.goto('https://google.com/')
    const aiArgs = { page, test }
    
    // Use AI to interact with the search box
    await ai('Type "ZeroStep AI testing" in the search box', aiArgs)
    await ai('Press enter', aiArgs)
    
    // Wait for results to load
    await page.waitForLoadState('networkidle')
  })

  test('should interact with ZeroStep website elements', async ({ page }) => {
    await page.goto('https://zerostep.com/')
    const aiArgs = { page, test }
    
    // Use AI to find and click on navigation elements
    await ai('Click on the "Documentation" link in the navigation', aiArgs)
    await page.waitForLoadState('networkidle')
    
    // Get the current page title
    const pageTitle = await ai('Get the current page title', aiArgs)
    console.log('Current page title:', pageTitle)
  })
})