import { chromium } from '@playwright/test'
import { ai } from '@zerostep/playwright'

async function automateDemoBooking() {
  // Launch the browser
  const browser = await chromium.launch({ headless: false })
  const context = await browser.newContext()
  const page = await context.newPage()
  
  try {
    // Initialize AI arguments
    const aiArgs = { page, test: baseTest }
    
    // Navigate to the website
    await page.goto('https://zerostep.com/')
    
    // Use AI to find and click the "Book a Demo" button
    await ai('Find and click the "Book a Demo" button in the navigation or hero section', aiArgs)
    await page.waitForLoadState('networkidle')
    
    // Fill out the demo request form using AI
    await ai('Fill out the demo request form with the following details: Name: John Doe, Email: john.doe@example.com, Company: Test Corp', aiArgs)
    
    // Wait for form submission and confirmation
    await page.waitForLoadState('networkidle')
    
    // Verify the submission was successful
    const successMessage = await ai('Check if there is a success message or confirmation on the page', aiArgs)
    console.log('Form submission status:', successMessage)
    
    // Optional: Take a screenshot of the confirmation
    await page.screenshot({ path: 'demo-booking-confirmation.png' })
    
  } catch (error) {
    console.error('Automation failed:', error)
    // Take a screenshot if something goes wrong
    await page.screenshot({ path: 'automation-error.png' })
  } finally {
    // Close the browser
    await browser.close()
  }
}

// Run the automation
automateDemoBooking().catch(console.error)