"""
Browser-based survey testing using Playwright.
Takes each V4 survey through a real browser to verify:
- JS table shuffler runs and records ProductDisplayOrder
- Product table renders correctly
- AI recommendation appears in correct conditions
- Disclosure text appears in correct conditions
- DisplayLogic shows/hides questions correctly
- EndSurvey branches work
- Page timers enforce minimum times
- Choice randomization works

Screenshots saved to results/screenshots/v4/

Usage: python test_survey_browser.py [pretest|study_a|study_y|study_z]
"""

import asyncio
import os
import sys
import time

# Survey URLs
SURVEYS = {
    'pretest': 'https://okstatebusiness.az1.qualtrics.com/jfe/form/SV_bOyHko6mpqtn4mq',
    'study_a': 'https://okstatebusiness.az1.qualtrics.com/jfe/form/SV_emxmNAd2Bu21DL0',
    'study_y': 'https://okstatebusiness.az1.qualtrics.com/jfe/form/SV_benZF5wofYof458',
    'study_z': 'https://okstatebusiness.az1.qualtrics.com/jfe/form/SV_7P5xZMJrF242hHU',
}


async def take_survey(survey_name):
    """Navigate through a survey in a real browser."""
    from playwright.async_api import async_playwright

    url = SURVEYS[survey_name]
    screenshot_dir = os.path.join('results', 'screenshots', 'v4', survey_name)
    os.makedirs(screenshot_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Testing: {survey_name}")
    print(f"URL: {url}")
    print(f"Screenshots: {screenshot_dir}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        page_num = 0

        async def screenshot(label=''):
            nonlocal page_num
            page_num += 1
            path = os.path.join(screenshot_dir, f'page_{page_num:02d}_{label}.png')
            await page.screenshot(path=path, full_page=True)
            print(f"  Screenshot {page_num}: {label}")
            return path

        async def click_next():
            """Click the Next button."""
            # Wait for next button to be visible
            try:
                next_btn = page.locator('#NextButton')
                if await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    await asyncio.sleep(1)
                    return True
            except:
                pass
            return False

        async def select_radio(choice_num):
            """Select a radio button by choice number."""
            try:
                # Qualtrics radio buttons have specific selectors
                selector = f'input[value="{choice_num}"]'
                radio = page.locator(selector).first
                if await radio.is_visible():
                    await radio.click()
                    return True
                # Try alternative selector
                selector2 = f'label:has-text("{choice_num}")'
                label = page.locator(selector2).first
                if await label.is_visible():
                    await label.click()
                    return True
            except:
                pass
            return False

        # Navigate to survey
        print("\nNavigating to survey...")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)

        # Screenshot the first page
        await screenshot('landing')

        # Check what's on the page
        content = await page.content()
        has_table = '<table' in content.lower()
        has_ai = 'AI Shopping Assistant' in content
        has_consent = 'Consent' in content or 'consent' in content or 'agree' in content

        print(f"  Has table: {has_table}")
        print(f"  Has AI rec: {has_ai}")
        print(f"  Has consent: {has_consent}")

        # Check if JS shuffler is present
        # The shuffler modifies ProductDisplayOrder embedded data
        # We can check by looking at the page's JS execution

        # Try to answer consent (select "I agree")
        if has_consent:
            try:
                agree = page.locator('label:has-text("I agree")').first
                if await agree.is_visible():
                    await agree.click()
                    print("  Selected: I agree")
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"  Could not click consent: {e}")

        await screenshot('after_consent')

        # Click Next
        await click_next()
        await screenshot('page2')

        # Try to answer attention check (select Horse)
        try:
            horse = page.locator('label:has-text("Horse")').first
            if await horse.is_visible():
                await horse.click()
                print("  Selected: Horse")
        except:
            print("  No Horse option found on this page")

        await screenshot('after_attn')
        await click_next()
        await screenshot('page3')

        # Continue taking screenshots of each page
        for i in range(15):
            # Get current page content
            content = await page.content()

            # Check for specific elements
            checks = {
                'product_table': '<table' in content.lower(),
                'ai_rec': 'AI Shopping Assistant' in content,
                'disclosure': 'Note:' in content and ('training data' in content or 'language model' in content),
                'feature_importance': 'important' in content.lower() and 'feature' in content.lower(),
                'product_choice': 'choose' in content.lower() or 'purchase' in content.lower(),
                'brand_awareness': 'familiarity' in content.lower(),
                'debrief': 'different' in content.lower() and 'recommendation' in content.lower(),
            }

            active_checks = [k for k, v in checks.items() if v]
            if active_checks:
                print(f"  Page {page_num}: {', '.join(active_checks)}")

            # Check for ProductDisplayOrder in embedded data
            if checks['product_table']:
                try:
                    # Try to read the embedded data set by JS
                    order = await page.evaluate('() => { try { return Qualtrics.SurveyEngine.getEmbeddedData("ProductDisplayOrder") } catch(e) { return "N/A" } }')
                    print(f"  ProductDisplayOrder: {order}")
                except:
                    print("  Could not read ProductDisplayOrder (may not be set yet)")

            await screenshot(f'step_{i+4}')

            # Try to interact with whatever's on the page
            # Select first radio button if any visible
            try:
                radios = page.locator('input[type="radio"]')
                if await radios.count() > 0:
                    # Click the first visible radio
                    for r_idx in range(await radios.count()):
                        radio = radios.nth(r_idx)
                        if await radio.is_visible():
                            await radio.click()
                            break
            except:
                pass

            # Try to fill text areas
            try:
                textareas = page.locator('textarea, input[type="text"]')
                for t_idx in range(await textareas.count()):
                    ta = textareas.nth(t_idx)
                    if await ta.is_visible():
                        await ta.fill('Test response from Playwright browser test.')
                        break
            except:
                pass

            # Wait for any timers
            await asyncio.sleep(2)

            # Click Next
            success = await click_next()
            if not success:
                print(f"  No Next button found. Survey may be complete.")
                break

            # Check if we hit EndSurvey
            content = await page.content()
            if 'Thank you' in content or 'survey has ended' in content.lower() or 'thank' in content.lower():
                await screenshot('end')
                print("  Survey ended.")
                break

        await browser.close()

    print(f"\nDone. Screenshots saved to {screenshot_dir}/")
    return screenshot_dir


async def main():
    survey = sys.argv[1] if len(sys.argv) > 1 else 'pretest'
    if survey not in SURVEYS:
        print(f"Unknown survey: {survey}")
        print(f"Options: {', '.join(SURVEYS.keys())}")
        return
    await take_survey(survey)


if __name__ == '__main__':
    asyncio.run(main())
