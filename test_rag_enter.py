"""Live browser check for question keyboard controls and safe Markdown."""
import json

from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True,
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    page = browser.new_page()
    requests = []

    def answer(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=200, content_type='application/json', body=json.dumps({
            'answer': ('### Nano-biosensors\n\n**Graphene-Based Sensors:**\n'
                       '* **Reduced graphene oxide:** Label-free detection [2].\n'
                       '* Safe *emphasis* and `code`.\n\n<script>window.bad=true</script>'),
            'sources': [], 'ranking': 'test'}))

    page.route('**/api/rag/ask', answer)
    page.goto('http://127.0.0.1:1337/rag', wait_until='domcontentloaded')
    question = page.locator('#question')
    question.fill('Ask with Enter')
    question.press('Enter')
    page.locator('#answer').wait_for(state='visible')
    assert requests == [{'question': 'Ask with Enter'}], requests
    assert page.locator('#answer h3').inner_text() == 'Nano-biosensors'
    assert page.locator('#answer ul li').count() == 2
    assert page.locator('#answer strong').count() == 2
    assert page.locator('#answer em').inner_text() == 'emphasis'
    assert page.locator('#answer code').inner_text() == 'code'
    assert page.locator('#answer script').count() == 0
    assert '<script>window.bad=true</script>' in page.locator('#answer').inner_text()

    question.fill('First line')
    question.press('Shift+Enter')
    question.type('Second line')
    assert question.input_value() == 'First line\nSecond line'
    assert len(requests) == 1
    print('Enter/Shift+Enter and safe Markdown rendering passed.')
    browser.close()
