"""
Screenshot every page of Qualtrics Study 1 (SV_3mBQFO2Rlpq72LA).

Uses Playwright (async) to navigate the survey, answering required
questions so the Next button advances. Saves full-page PNGs.

Handles: MC (radio), TE (text entry), RO (rank order / drag-and-drop),
         Matrix (Likert), checkboxes, sliders, attention checks.
"""

import asyncio
import os
import re
from playwright.async_api import async_playwright

OUT_DIR = r'C:\Users\natal\Dropbox\Felipe\CLAUDE CODE\academic-research\projects\spec-resistance\nature-rr\results\screenshots\study1'
SURVEY_URL = 'https://okstatebusiness.az1.qualtrics.com/jfe/form/SV_3mBQFO2Rlpq72LA'
MAX_PAGES = 30


async def get_visible_question_ids(page):
    """Return list of visible question IDs on current page."""
    return await page.evaluate('''() => {
        const qs = document.querySelectorAll('.QuestionOuter');
        return Array.from(qs)
            .filter(q => q.offsetParent !== null && !q.classList.contains('Meta'))
            .map(q => q.getAttribute('questionid') || q.id);
    }''')


async def get_page_fingerprint(page):
    """Get a fingerprint to detect if the page actually changed."""
    qids = await get_visible_question_ids(page)
    return '|'.join(sorted(qids))


async def handle_rank_order(page):
    """Handle RO (rank order) questions by dragging first item down and back.
    This removes the NotEdited class, registering user interaction."""
    # Get bounding boxes via JS to avoid CSS selector escaping issues
    ro_coords = await page.evaluate('''() => {
        const lists = document.querySelectorAll('ul.ui-sortable');
        const results = [];
        for (const l of lists) {
            if (l.offsetParent === null) continue;
            const items = l.querySelectorAll('li');
            if (items.length < 2) continue;
            const r1 = items[0].getBoundingClientRect();
            const r2 = items[1].getBoundingClientRect();
            results.push({
                x1: r1.x + r1.width / 2, y1: r1.y + r1.height / 2,
                x2: r2.x + r2.width / 2, y2: r2.y + r2.height / 2,
            });
        }
        return results;
    }''')

    for coords in ro_coords:
        # Drag item2 above item1 to register interaction
        await page.mouse.move(coords['x2'], coords['y2'])
        await page.mouse.down()
        await page.wait_for_timeout(150)
        await page.mouse.move(coords['x1'], coords['y1'], steps=10)
        await page.wait_for_timeout(150)
        await page.mouse.up()
        await page.wait_for_timeout(300)


async def handle_attention_check(page):
    """Try to detect and answer attention check questions."""
    result = await page.evaluate('''() => {
        const texts = document.querySelectorAll('.QuestionText');
        for (const t of texts) {
            const txt = t.textContent;
            const lower = txt.toLowerCase();
            // Pattern: "please select X" or "choose X"
            if (lower.includes('to show that') || lower.includes('reading carefully') ||
                lower.includes('attention') || lower.includes('please select') ||
                lower.includes('please choose')) {
                // Extract target from quotes
                const quoteMatch = txt.match(/["\u201c]([^"\u201d]+)["\u201d]/);
                if (quoteMatch) return quoteMatch[1].trim();
                // Extract from "select X" pattern
                const selectMatch = lower.match(/(?:select|choose)\s+(?:the\s+)?["']?(\w[\w\s]*\w)["']?/);
                if (selectMatch) return selectMatch[1].trim();
            }
        }
        return null;
    }''')

    if result:
        clicked = await page.evaluate('''(target) => {
            const targetLower = target.toLowerCase();
            // Try labels
            const labels = document.querySelectorAll('label.SingleAnswer, label.MultipleAnswer');
            for (const l of labels) {
                if (l.textContent.trim().toLowerCase().includes(targetLower)) {
                    l.click();
                    return l.textContent.trim();
                }
            }
            // Try radio labels
            const radios = document.querySelectorAll('input[type="radio"]');
            for (const r of radios) {
                const label = document.querySelector('label[for="' + r.id + '"]');
                if (label && label.textContent.trim().toLowerCase().includes(targetLower)) {
                    label.click();
                    return label.textContent.trim();
                }
            }
            return null;
        }''', result)
        if clicked:
            print(f'    Attention check: selected "{clicked}"')
            return True
    return False


async def fill_all_fields(page):
    """Fill all visible required fields using JavaScript."""
    await page.evaluate('''() => {
        const handled = new Set();
        const questions = document.querySelectorAll('.QuestionOuter');

        for (const q of questions) {
            if (q.offsetParent === null) continue;
            const qid = q.getAttribute('questionid') || q.id;
            if (handled.has(qid)) continue;
            handled.add(qid);

            // --- Radio buttons (MC questions) ---
            const radios = q.querySelectorAll('input[type="radio"]');
            if (radios.length > 0) {
                const checked = q.querySelector('input[type="radio"]:checked');
                if (!checked) {
                    const firstLabel = q.querySelector('label.SingleAnswer');
                    if (firstLabel) firstLabel.click(); else radios[0].click();
                }
                continue;
            }

            // --- Checkboxes ---
            const checks = q.querySelectorAll('input[type="checkbox"]');
            if (checks.length > 0) {
                const checked = q.querySelector('input[type="checkbox"]:checked');
                if (!checked) {
                    const firstLabel = q.querySelector('label.MultipleAnswer');
                    if (firstLabel) firstLabel.click(); else checks[0].click();
                }
                continue;
            }

            // --- Text inputs ---
            const textInputs = q.querySelectorAll('input[type="text"], textarea');
            for (const inp of textInputs) {
                if (!inp.value.trim() && inp.offsetParent !== null) {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(inp, 'Good battery life under $100');
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    inp.dispatchEvent(new Event('blur', {bubbles: true}));
                }
            }

            // --- Sliders ---
            const sliders = q.querySelectorAll('.Slider .track, .slider-container');
            for (const s of sliders) {
                if (s.offsetParent !== null) s.click();
            }
        }

        // --- Matrix / Likert rows ---
        const matrixRows = document.querySelectorAll('tr.ChoiceRow');
        for (const row of matrixRows) {
            if (row.offsetParent === null) continue;
            const checked = row.querySelector('input[type="radio"]:checked');
            if (!checked) {
                const rowRadios = row.querySelectorAll('input[type="radio"]');
                if (rowRadios.length > 0) {
                    const mid = Math.floor(rowRadios.length / 2);
                    const label = document.querySelector('label[for="' + rowRadios[mid].id + '"]');
                    if (label) label.click(); else rowRadios[mid].click();
                }
            }
        }

        // --- Select dropdowns ---
        const selects = document.querySelectorAll('select');
        for (const s of selects) {
            if (s.offsetParent !== null && s.options.length > 1 && s.selectedIndex <= 0) {
                s.selectedIndex = 1;
                s.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }
    }''')


async def fill_and_advance(page):
    """Fill all required fields on current page, then click Next.
    Returns True if page advanced, False if stuck."""

    prev_fingerprint = await get_page_fingerprint(page)

    # Handle attention checks first
    await handle_attention_check(page)
    await page.wait_for_timeout(300)

    # Handle rank-order (drag-and-drop) questions
    await handle_rank_order(page)
    await page.wait_for_timeout(300)

    # Fill all standard fields
    await fill_all_fields(page)
    await page.wait_for_timeout(500)

    # Click Next
    next_btn = page.locator('#NextButton')
    if await next_btn.count() == 0 or not await next_btn.is_visible():
        return False

    await next_btn.click()
    await page.wait_for_timeout(2500)

    # Check if page changed
    new_fingerprint = await get_page_fingerprint(page)
    if new_fingerprint != prev_fingerprint:
        return True

    # --- Retry with broader approach ---
    print('    Page did not advance. Second attempt...')

    # Re-do everything
    await handle_attention_check(page)
    await handle_rank_order(page)
    await page.wait_for_timeout(300)

    # Click ALL first radios by name group
    await page.evaluate('''() => {
        const namesSeen = new Set();
        const allRadios = document.querySelectorAll('input[type="radio"]');
        for (const r of allRadios) {
            if (r.offsetParent !== null && !namesSeen.has(r.name)) {
                namesSeen.add(r.name);
                const label = document.querySelector('label[for="' + r.id + '"]');
                if (label) label.click(); else r.click();
            }
        }
        // Fill all text fields
        const allText = document.querySelectorAll('input[type="text"], textarea');
        for (const t of allText) {
            if (!t.value.trim() && t.offsetParent !== null) {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeInputValueSetter.call(t, '50');
                t.dispatchEvent(new Event('input', {bubbles: true}));
                t.dispatchEvent(new Event('change', {bubbles: true}));
                t.dispatchEvent(new Event('blur', {bubbles: true}));
            }
        }
    }''')
    await page.wait_for_timeout(500)

    await next_btn.click()
    await page.wait_for_timeout(2500)

    new_fp2 = await get_page_fingerprint(page)
    return new_fp2 != prev_fingerprint


async def screenshot_survey():
    os.makedirs(OUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(viewport={'width': 1200, 'height': 900})
        page = await context.new_page()

        print(f'Opening survey: {SURVEY_URL}')
        await page.goto(SURVEY_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        page_num = 1
        stuck_count = 0

        while page_num <= MAX_PAGES:
            await page.wait_for_timeout(1000)

            # Check end of survey
            eol = await page.locator('.EndOfSurvey, #EndOfSurvey').count()
            if eol > 0:
                path = os.path.join(OUT_DIR, f'page_{page_num:02d}_end.png')
                await page.screenshot(path=path, full_page=True)
                print(f'Captured: page_{page_num:02d}_end.png (end of survey)')
                break

            # Take screenshot BEFORE answering (clean layout)
            path = os.path.join(OUT_DIR, f'page_{page_num:02d}.png')
            await page.screenshot(path=path, full_page=True)

            qids = await get_visible_question_ids(page)
            print(f'Captured: page_{page_num:02d}.png  (questions: {", ".join(qids[:8])})')

            # Fill and advance
            advanced = await fill_and_advance(page)
            if advanced:
                page_num += 1
                stuck_count = 0
            else:
                stuck_count += 1
                if stuck_count >= 3:
                    # Take a stuck screenshot showing the validation error
                    path_s = os.path.join(OUT_DIR, f'page_{page_num:02d}_stuck.png')
                    await page.screenshot(path=path_s, full_page=True)
                    # Dump visible question types for debugging
                    debug = await page.evaluate('''() => {
                        const qs = document.querySelectorAll('.QuestionOuter');
                        return Array.from(qs)
                            .filter(q => q.offsetParent !== null)
                            .map(q => ({
                                qid: q.getAttribute('questionid'),
                                cls: q.className.substring(0, 80),
                                text: q.querySelector('.QuestionText')?.textContent?.substring(0, 100) || ''
                            }));
                    }''')
                    print(f'STUCK on page {page_num}. Visible questions:')
                    for d in debug:
                        print(f'  {d["qid"]}: {d["cls"]} — {d["text"][:80]}')
                    break
                print(f'    Retry {stuck_count}/3 on page {page_num}')

        await browser.close()
        print(f'\nDone. {page_num} page(s) captured in {OUT_DIR}')


if __name__ == '__main__':
    asyncio.run(screenshot_survey())
