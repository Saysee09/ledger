import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(ROOT + '/tests/shots', exist_ok=True)
import urllib.parse
ROOT = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))); exec(open(ROOT + '/tests/test_v91.py').read().split("with sync_playwright() as p:")[0])
with sync_playwright() as p:
    br = p.chromium.launch()
    for scale in (1.0, 1.6):
        tag = ' [text %d%%]' % (scale * 100)
        st = owner_state(False); st['drive'] = dict(id='S1', email='sunny@gmail.com', name='Sunny', since='2026-11-01 10:00:00')
        st['exp'] += [dict(id='O%d' % i, ts='2026-10-%02d 10:00:00' % (1 + i), account='ICICI Bank', amount=a, category=c, remarks=r, photo='', payee='', mine=False) for i, (a, c, r) in enumerate([(9250, 'Household', 'Rent'), (1200, 'Food & Dining', 'Dinner'), (300, 'Food & Dining', 'Chai'), (2500, 'Shopping', 'Shoes'), (450, 'Transport', 'Cab'), (80, 'Food & Dining', 'Snacks')])]
        st['inc'][0]['ts'] = '2026-10-05 10:00:00'; st['exp'] += [dict(id='SEP1', ts='2026-09-10 10:00:00', account='ICICI Bank', amount=10000, category='Household', remarks='Rent', photo='', payee='', mine=False)]
        ctx, pg, errs, dl = open_app(br, st, scale)
        pg.evaluate("() => { G.files.S1 = { id: 'S1', name: 'Brokeless', appProperties: { brokeless: '1' }, t: 1, tabs: {} }; }")
        D = pg.evaluate("() => { const D = repData('2026-10'); return { spent: D.spent, inc: D.inc, saved: D.saved, rate: D.rate, ch: D.ch, n: D.n, avg: D.avg, cats: D.cats.slice(0, 2), top: D.top.map(e => e.amount), cards: D.cards }; }")
        ok(D['spent'] == 13780 and D['inc'] == 50000 and D['saved'] == 36220 and D['rate'] == 72 and D['ch'] == 38 and D['n'] == 6 and D['avg'] == round(13780 / 31, 2) and D['cats'][0] == ['Household', 9250] and D['top'] == [9250, 2500, 1200, 450, 300] and D['cards'] == [['ICICI Credit Card', 699]], 'October numbers add up: spent 13,780 (38%% more than Sept), income 50,000, left 36,220 = 72%%, avg/day, top category, biggest 5, card dues (%s)' % D + tag)
        ok(pg.evaluate("() => nAlerts(repAlert())") == 1, 'bell shows "Your October report is ready"' + tag)
        pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(400); pg.screenshot(path=OUT + 'r1_bell_%d.png' % (scale * 100)); ok(overflow(pg) == [], 'bell fits %s' % overflow(pg) + tag)
        pg.click('button[data-act=repOpen]'); pg.wait_for_timeout(500)
        ok(pg.evaluate("() => U.tab === 'settings' && U.sp === 'mreport' && !sheetOpen() && nAlerts(repAlert()) === 0"), 'Open → the report page, and the bell line is cleared' + tag)
        pg.screenshot(path=OUT + 'r2_report_%d.png' % (scale * 100), full_page=True); ok(overflow(pg) == [], 'report fits %s' % overflow(pg) + tag)
        href = pg.get_attribute('a[href^="mailto:"]', 'href'); to, q = href[7:].split('?'); qs = urllib.parse.parse_qs(q)
        body = qs['body'][0]
        ok(urllib.parse.unquote(to) == 'sunny@gmail.com' and qs['subject'][0] == 'Brokeless · October 2026 report' and 'Spent: ₹13,780' in body and '38% more than September 2026' in body and 'Household: ₹9,250 (67%)' in body and 'ICICI Credit Card: ₹699' in body and len(href) < 3500, 'Send to my email: addressed to the signed-in Gmail, subject and full report text filled in (%d chars)' % len(href) + tag)
        if scale == 1.0: print('--- email body ---\n' + body + '\n------------------')
        pg.click('button[data-act=repShift][data-n="1"]'); pg.wait_for_timeout(300)
        ok('November 2026 · so far' in pg.inner_text('#view'), '› moves to this month (so far)' + tag)
        ok(pg.locator('button[data-act=repShift][data-n="1"]').is_disabled(), 'cannot go past this month' + tag)
        for i in range(3): pg.click('button[data-act=repShift][data-n="-1"]'); pg.wait_for_timeout(150)
        ok('Nothing logged in August 2026' in pg.inner_text('#view'), 'a month with nothing says so' + tag)
        pg.evaluate("() => setTab('settings')"); pg.wait_for_timeout(300)
        ok(pg.locator('button[data-act=spOpen][data-k=mreport]').count() == 1 and pg.locator('button[data-act=spOpen][data-k=reports]').count() == 0, 'Settings lists "Monthly report" for Google sign-in users' + tag)
        pg.click('button[data-act=spOpen][data-k=mreport]'); pg.wait_for_timeout(300); pg.uncheck('input[data-in=repOn]'); pg.wait_for_timeout(200)
        ok(pg.evaluate("() => S.prefs.mrep === false && repAlert() === ''"), 'reminder can be switched off' + tag)
        pg.evaluate("() => widgetAct('report')"); pg.wait_for_timeout(600)
        ok(pg.evaluate("() => U.sp === 'mreport'"), 'tapping the phone notification opens the report' + tag)
        ok(not errs, 'no page errors %s' % errs + tag); ctx.close()
    br.close()
print('\nFAILED: %d' % len(fails)); [print(' -', f) for f in fails]
