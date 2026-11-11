import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(ROOT + '/tests/shots', exist_ok=True)
import json, sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'file://' + ROOT + '/index.html'
OLD = len(sys.argv) > 1
OUT = ROOT + '/tests/shots/'
fails = []
def ok(c, msg):
    print(('PASS ' if c else 'FAIL ') + msg)
    if not c: fails.append(msg)
def state(theme='dark'):
    acc = lambda i, n, t, op, **k: dict(id='A%d' % i, name=n, type=t, opening=op, openingDate='2026-10-27 02:45:00', archived=False, order=i, others=False, keptIn='', **k)
    return dict(accounts=[acc(1, 'ICICI Bank', 'bank', 14062), acc(2, 'Kotak Bank', 'bank', 181), acc(3, 'Cash in hand', 'cash', 25), acc(4, 'ICICI Credit Card', 'card', 0, billDay=28),
                          dict(acc(5, 'Mom', 'bank', 56379), others=True, keptIn='Kotak Bank'), dict(acc(6, 'Evol', 'bank', 20000), others=True, keptIn='Kotak Bank')],
                exp=[dict(id='E1', ts='2026-11-04 10:00:00', account='ICICI Credit Card', amount=30, category='Miscellaneous', remarks='Tip', photo='', payee='', mine=False),
                     dict(id='E2', ts='2026-11-11 10:00:00', account='ICICI Credit Card', amount=729, category='Household', remarks='Beans', photo='', payee='', mine=False)],
                adj=[dict(id='J1', ts='2026-11-05 10:00:00', account='ICICI Credit Card', amount=150000, remarks='Matched to ₹1,50,000')],
                trf=[dict(id='T1', ts='2026-11-10 22:08:00', **{'from': 'ICICI Bank'}, to='ICICI Credit Card', amount=30, remarks='Card bill')],
                loans=[dict(id='L%d' % i, name=n, dir='owed', note='', archived=False, created='2026-10-01 10:00:00') for i, n in enumerate(['Abhishek Apkari', 'Evol', 'Ravi'])],
                theme=theme, prefs={})
def swipe(cdp, x, y, dy, dx=0):
    import time
    cdp.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=x, y=y)]))
    for i in range(1, 13):
        cdp.send('Input.dispatchTouchEvent', dict(type='touchMove', touchPoints=[dict(x=x + dx * i / 12, y=y + dy * i / 12)])); time.sleep(.016)
    time.sleep(.12)
    cdp.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[])); time.sleep(.25)
def tap(cdp, pg, sel):
    b = pg.locator(sel).first.bounding_box(); pg.touchscreen.tap(min(355, b['x'] + b['width'] / 2), b['y'] + b['height'] / 2); pg.wait_for_timeout(350)
with sync_playwright() as p:
    br = p.chromium.launch()
    for scale in (1.0, 1.3):
        ctx = br.new_context(viewport=dict(width=360, height=780), device_scale_factor=2, has_touch=True, is_mobile=True)
        pg = ctx.new_page(); cdp = ctx.new_cdp_session(pg)
        pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
        pg.add_init_script("window.Chart = function(){ return {destroy(){}, update(){}} }; window.Chart.register = () => {}; window.Chart.defaults = {font:{}, plugins:{legend:{labels:{}}, tooltip:{}}, color:''}; localStorage.setItem('ledger3', %s);" % json.dumps(json.dumps(state())))
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(1800)
        pg.evaluate("s => document.documentElement.style.fontSize = (16*s) + 'px'", scale)
        pg.evaluate("() => { U.mseg = 'acc'; setTab('money'); }"); pg.wait_for_timeout(400)
        tag = ' [text %d%%]' % (scale * 100)
        # ---- 1. tab strip keeps its place
        seg = '#view .seg.page'
        vis = "k => { const g = document.querySelector('#view .seg.page'), b = g.querySelector('[data-k=' + k + ']'), r = b.getBoundingClientRect(), q = g.getBoundingClientRect(); return [b.classList.contains('on'), r.left >= q.left - 1 && r.right <= q.right + 1, Math.round(g.scrollLeft)]; }"
        bx = pg.locator(seg).bounding_box()
        swipe(cdp, bx['x'] + bx['width'] - 40, bx['y'] + bx['height'] / 2, 0, -260); pg.wait_for_timeout(300)
        print('   strip after finger swipe: %dpx' % pg.evaluate("() => document.querySelector('#view .seg.page').scrollLeft"))
        pg.evaluate("() => { const g = document.querySelector('#view .seg.page'); g.scrollLeft = g.scrollWidth; }")
        tap(cdp, pg, seg + ' [data-k=loans]')
        r = pg.evaluate(vis, 'loans'); ok(r[0] and r[1], 'tap Loans: Loans is selected and still in view (strip at %dpx, not reset to 0)%s' % (r[2], tag))
        tap(cdp, pg, seg + ' [data-k=emi]')
        r2_ = pg.evaluate(vis, 'emi'); ok(r2_[0] and r2_[1] and abs(r2_[2] - r[2]) < 3, 'tap EMIs: strip stays where it was (%d -> %dpx)%s' % (r[2], r2_[2], tag))
        tap(cdp, pg, seg + ' [data-k=loans]'); tap(cdp, pg, seg + ' [data-k=emi]')
        r3 = pg.evaluate(vis, 'emi'); ok(r3[0] and r3[1] and r3[2] > 0, 'Loans -> EMIs again: no jump back to the start (%dpx)%s' % (r3[2], tag))
        if scale == 1.0: pg.screenshot(path=OUT + 'g1_tabs.png')
        pg.evaluate("() => { U.mseg = 'acc'; render(); }"); pg.wait_for_timeout(300)
        r = pg.evaluate(vis, 'acc'); ok(r[0] and r[1], 'back to Accounts: Accounts tab is in view%s' % tag)
        # ---- 2. page behind a sheet never scrolls
        can = pg.evaluate("() => document.documentElement.scrollHeight - innerHeight")
        pg.evaluate("() => ACT.acctOpen({dataset: {n: 'ICICI Credit Card'}})"); pg.wait_for_timeout(600)
        sb = pg.evaluate("() => { const b = document.querySelector('#shBody'); return [b.scrollHeight, b.clientHeight]; }")
        sh = pg.locator('#sheet').bounding_box()
        for dy in (-300, 300, -300):
            swipe(cdp, 180, sh['y'] + sh['height'] / 2, dy); pg.wait_for_timeout(250)
        y = pg.evaluate("() => scrollY")
        ok(y == 0, 'swiping up/down on the card sheet: page behind stays still (moved %dpx; page could scroll %dpx; sheet body %s)%s' % (y, can, sb, tag))
        swipe(cdp, 180, 40, -300); pg.wait_for_timeout(250)   # finger on the dimmed area above the sheet
        ok(pg.evaluate("() => scrollY") == 0, 'swiping on the dimmed area: page stays still%s' % tag)
        if OLD: continue
        # long sheet still scrolls with a finger
        pg.evaluate("() => ACT.acctEdit({dataset: {n: 'ICICI Bank'}})"); pg.wait_for_timeout(500)
        sh = pg.locator('#sheet').bounding_box(); swipe(cdp, 180, sh['y'] + sh['height'] / 2, -300); pg.wait_for_timeout(300)
        ok(pg.evaluate("() => document.querySelector('#shBody').scrollTop") > 100 and pg.evaluate("() => scrollY") == 0, 'a long sheet still scrolls inside itself%s' % tag)
        # chips row inside a sheet still scrolls sideways
        pg.evaluate("() => compose('exp')"); pg.wait_for_timeout(500)
        ch = pg.evaluate("() => { const c = [...document.querySelectorAll('#sheet *')].find(e => e.scrollWidth > e.clientWidth + 20 && /auto|scroll/.test(getComputedStyle(e).overflowX)); if (!c) return null; const r = c.getBoundingClientRect(); c.setAttribute('data-t', '1'); return [r.x + r.width - 30, r.y + r.height / 2]; }")
        if ch:
            swipe(cdp, ch[0], ch[1], 0, -150); pg.wait_for_timeout(300)
            ok(pg.evaluate("() => document.querySelector('[data-t]').scrollLeft") > 20, 'sideways rows inside a sheet still scroll%s' % tag)
        # swipe down from the top bar still closes
        tb = pg.locator('#shTop').bounding_box(); pg.touchscreen.tap(5, 5)
        cdp.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=120, y=tb['y'] + 10)]))
        for i in range(1, 9): cdp.send('Input.dispatchTouchEvent', dict(type='touchMove', touchPoints=[dict(x=120, y=tb['y'] + 10 + i * 25)]))
        cdp.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[])); pg.wait_for_timeout(500)
        ok(not pg.evaluate("() => sheetOpen()"), 'swipe down from the sheet top still closes it%s' % tag)
        swipe(cdp, 180, 400, -300); pg.wait_for_timeout(300)
        ok(pg.evaluate("() => scrollY") > 50 or can < 50, 'after closing, the page scrolls normally again%s' % tag)
        pg.evaluate("() => scrollTo(0,0)")
        # ---- 3. card that shows its limit as a balance
        ok(pg.evaluate("() => cardLooksLimit(acc('ICICI Credit Card'))") and pg.evaluate("() => C.bal['ICICI Credit Card']") == 149271, 'card showing ₹1,49,271 is flagged%s' % tag)
        pg.evaluate("() => ACT.acctOpen({dataset: {n: 'ICICI Credit Card'}})"); pg.wait_for_timeout(500)
        if scale == 1.0: pg.screenshot(path=OUT + 'g2_card_flag.png')
        pg.click('#sheet button[data-act=acctEdit] >> nth=0'); pg.wait_for_timeout(500)
        v = [pg.input_value('#aLimit').replace(',', ''), pg.input_value('#aOwe').replace(',', '')]
        ok(v == ['150000', '729'], 'Fix screen pre-fills limit 1,50,000 and owed 729 (%s)%s' % (v, tag))
        if scale == 1.0: pg.screenshot(path=OUT + 'g3_card_fix.png')
        pg.evaluate("() => document.querySelector('button[data-act=aSave]').scrollIntoView()"); pg.click('button[data-act=aSave]'); pg.wait_for_timeout(500)
        r = pg.evaluate("() => { const a = acc('ICICI Credit Card'), u = cardUse(a); return [C.bal[a.name], cardLooksLimit(a), u && u.lim, u && Math.round(u.pct * 100) / 100, u && u.safe]; }")
        ok(r[0] == -729 and not r[1] and r[2] == 150000 and r[4] == 44271, 'after Save: owes 729, limit 1.5L, %s%% used, 44,271 left before 30%% (%s)%s' % (r[3], r, tag))
        pg.evaluate("() => ACT.acctOpen({dataset: {n: 'ICICI Credit Card'}})"); pg.wait_for_timeout(500)
        if scale == 1.0: pg.screenshot(path=OUT + 'g4_card_fixed.png')
        # Match on a card = what you owe
        pg.evaluate("() => ACT.recon({dataset: {n: 'ICICI Credit Card'}})"); pg.wait_for_timeout(500); pg.fill('#rAmt', '1000'); pg.click('button[data-act=rSave]'); pg.wait_for_timeout(400)
        ok(pg.evaluate("() => C.bal['ICICI Credit Card']") == -1000, 'Match on a card: typing 1000 means "I owe 1000"%s' % tag)
        ok(not errs, 'no page errors %s%s' % (errs, tag))
        ctx.close()
    br.close()
print('\nFAILED: %d' % len(fails)); [print(' -', f) for f in fails]
