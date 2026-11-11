import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(ROOT + '/tests/shots', exist_ok=True)
import json, sys
from playwright.sync_api import sync_playwright

URL = 'file://' + ROOT + '/index.html'
OUT = ROOT + '/tests/shots/'
now = '2026-11-10 22:08:00'

def state(theme=''):
    acc = lambda i, n, t, op, **k: dict(id='A%d' % i, name=n, type=t, opening=op, openingDate='2026-11-01 00:00:00', archived=False, order=i, others=False, keptIn='', **k)
    return dict(accounts=[acc(1, 'ICICI Bank', 'bank', 52000, l4='123'), acc(2, 'Kotak Bank', 'bank', 18000), acc(3, 'Cash in hand', 'cash', 900), acc(4, 'ICICI Credit Card', 'card', 0, billDay=28, l4='4005')],
                exp=[dict(id='E1', ts='2026-11-05 10:00:00', account='ICICI Credit Card', amount=12500, category='Shopping', remarks='Shoes', photo='', payee='', mine=False)],
                pend=[dict(id='Pold1', ts='2026-11-09 22:08:00', amount=45, dir='debit', payee='Dispute Call 18002662 Or Sms Block 123', bank='ICICI', l4='123', account='ICICI Bank', card=False, atm=False, ref='', status='new', done='', raw='Rs 45.00 debited from ICICI Bank Acc XX123 on 09-Nov-26. To dispute call 18002662 or SMS BLOCK 123 to 9215676766')],
                theme=theme, prefs={})

SMS = {
 'debit':  'Rs 30.00 debited from ICICI Bank Acc XX123 on 10-Nov-26. To dispute call 18002662 or SMS BLOCK 123 to 9215676766',
 'credit': 'Payment of Rs 30.00 has been received on your ICICI Bank Credit Card XX4005 through Bharat Bill Payment System on 10-NOV-26.',
 'spend':  'INR 30.00 spent using ICICI Bank Card XX4005 on 10-Nov-26 on SWIGGY. Avl Limit: INR 1,49,970.00. If not you, call 1800 2662/SMS BLOCK 4005 to 9215676766.',
 'upi':    'ICICI Bank Acct XX123 debited for Rs 250.00 on 10-Nov-26; RAMESH KUMAR credited. UPI:631412345678. Call 18002662 for dispute. SMS BLOCK 123 to 9215676766.',
 'upi2':   'Sent Rs.664.71 from Kotak Bank AC X1211 to MC DONALDS on 10-11-26.UPI Ref 631498765432. Not you, https://kotak.com/KBANKT/Fraud',
}
fails = []
def ok(c, msg):
    print(('PASS ' if c else 'FAIL ') + msg)
    if not c: fails.append(msg)

def open_app(br, theme='', scale=1.0, st=None):
    ctx = br.new_context(viewport=dict(width=360, height=780), device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
    pg.add_init_script("window.Chart = function(){ return {destroy(){}, update(){}} }; window.Chart.register = () => {}; window.Chart.defaults = {font:{}, plugins:{legend:{labels:{}}, tooltip:{}}, color:''}; localStorage.setItem('ledger3', %s);" % json.dumps(json.dumps(st or state(theme))))
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1800)
    if scale != 1.0: pg.evaluate("s => document.documentElement.style.fontSize = (16*s) + 'px'", scale); pg.wait_for_timeout(200)
    return ctx, pg, errs

def overflow(pg):
    return pg.evaluate("() => { const w = innerWidth; return [...document.querySelectorAll('.sheet *, #view *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > w + 1 && !e.closest('.chips:not(.wrap), .strip, .seg, .tabs, [style*=overflow]'); }).slice(0, 5).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right)); }")

with sync_playwright() as p:
    br = p.chromium.launch()
    # ---------- parser ----------
    ctx, pg, errs = open_app(br)
    P = {k: pg.evaluate("r => parseSms(r, '2026-11-10 22:08:00')", v) for k, v in SMS.items()}
    ok(P['debit'] and P['debit']['dir'] == 'debit' and P['debit']['payee'] == '', 'bank debit SMS: helpline text is not the payee (%r)' % (P['debit'] or {}).get('payee'))
    ok(P['credit'] and P['credit']['dir'] == 'credit' and P['credit']['card'], 'card "payment received" SMS read as money into the card')
    ok(P['spend'] and P['spend']['payee'] == 'Swiggy' and P['spend']['card'], 'card spend still reads Swiggy (%r)' % (P['spend'] or {}).get('payee'))
    ok(P['upi'] and P['upi']['payee'] == 'Ramesh Kumar', 'UPI payee unchanged (%r)' % (P['upi'] or {}).get('payee'))
    ok(P['upi2'] and P['upi2']['payee'] == 'Mc Donalds', 'Kotak payee unchanged (%r)' % (P['upi2'] or {}).get('payee'))

    # ---------- usage ----------
    u = pg.evaluate("() => cardUse(acc('ICICI Credit Card'))")
    ok(u is None, 'no limit yet -> no usage shown')
    pg.evaluate("() => { commit([cfgOp('cards', {limits: {'ICICI Credit Card': 150000}})]); render(); }")
    u = pg.evaluate("() => cardUse(acc('ICICI Credit Card'))")
    ok(u and u['g'] == 30 and abs(u['pct'] - 8.333) < .01 and u['safe'] == 32500 and not u['over'], 'usage: 12,500 of 1.5L = 8%%, 32,500 left before 30%% (%s)' % u)

    # ---------- the two SMS arrive ----------
    pg.evaluate("([a,b]) => { window.LedgerSms(a, '2026-11-10 22:08:00', 'ICICIB'); window.LedgerSms(b, '2026-11-10 22:09:00', 'ICICIB'); pendFix(); cardPayTidy(); render(); }", [SMS['debit'], SMS['credit']])
    cp = pg.evaluate("() => cardPays().map(x => ({card: x.card, from: x.from, amount: x.amount, d: !!x.d}))")
    ok(len(cp) == 1 and cp[0] == dict(card='ICICI Credit Card', **{'from': 'ICICI Bank'}, amount=30, d=True), 'bank + card SMS joined into one card payment (%s)' % cp)
    ok(pg.evaluate("() => pendSort().length") == 1, 'both SMS leave "to sort" (only the unrelated ₹45 stays)')
    ok(pg.evaluate("() => S.pend.find(p => p.id === 'Pold1').payee") == '', 'old waiting SMS: "Dispute Call…" name cleaned')
    pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(500)
    pg.screenshot(path=OUT + '1_bell_light.png')
    ok(overflow(pg) == [], 'bell fits 360px %s' % overflow(pg))
    # tap the text -> editable sheet
    pg.click('.alert.cpay .mid'); pg.wait_for_timeout(400)
    ok(pg.input_value('#cpAmt').replace(',', '') in ('30', '30.00') and pg.input_value('#cpDate') == '2026-11-10', 'tap the line -> Pay sheet pre-filled (₹%s, %s)' % (pg.input_value('#cpAmt'), pg.input_value('#cpDate')))
    pg.screenshot(path=OUT + '2_pay_from_sms.png')
    pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(300)
    b0 = pg.evaluate("() => [C.bal['ICICI Bank'], C.bal['ICICI Credit Card'], S.exp.length]")
    pg.click('.alert.cpay button[data-act=cpYes]'); pg.wait_for_timeout(500)
    b1 = pg.evaluate("() => [C.bal['ICICI Bank'], C.bal['ICICI Credit Card'], S.exp.length, S.trf.length, S.pend.filter(p => p.status === 'done').length, cardPays().length]")
    ok(b1[0] == b0[0] - 30 and b1[1] == b0[1] + 30 and b1[2] == b0[2] and b1[3] == 1 and b1[4] == 2 and b1[5] == 0, 'one tap "Yes, paid": bank −30, card owed −30, no new expense, 1 transfer, both SMS filed (%s -> %s)' % (b0, b1))
    ok(not errs, 'no page errors %s' % errs)

    # ---------- pay by hand first, SMS come later ----------
    ctx2, pg, errs = open_app(br)
    pg.evaluate("() => { commit([cfgOp('cards', {limits: {'ICICI Credit Card': 150000}})]); ACT.acctOpen({dataset: {n: 'ICICI Credit Card'}}); }"); pg.wait_for_timeout(400)
    pg.screenshot(path=OUT + '3_card_sheet.png')
    ok(pg.locator('.sheet button[data-act=payCard]').count() == 1, 'card screen has a "Pay card" button (any day)')
    ok(overflow(pg) == [], 'card screen fits %s' % overflow(pg))
    pg.click('.sheet button[data-act=payCard]'); pg.wait_for_timeout(400)
    ok(pg.input_value('#cpAmt').replace(',', '') in ('12500', '12500.00'), 'pay sheet opens with what you owe (%s)' % pg.input_value('#cpAmt'))
    pg.fill('#cpAmt', '30'); pg.screenshot(path=OUT + '4_pay_sheet.png'); pg.click('button[data-act=cpSave]'); pg.wait_for_timeout(400)
    pg.evaluate("([a,b]) => { window.LedgerSms(a, nowTs(), 'ICICIB'); window.LedgerSms(b, nowTs(), 'ICICIB'); pendFix(); cardPayTidy(); render(); }", [SMS['debit'].replace('10-Nov-26', '11-Nov-26'), SMS['credit'].replace('10-NOV-26', '11-NOV-26')])
    r = pg.evaluate("() => [S.trf.length, cardPays().length, S.pend.filter(p => p.status === 'done').length, pendNew().length]")
    ok(r == [1, 0, 2, 1], 'paid by hand first -> both SMS filed quietly, no second transfer, nothing to confirm (%s)' % r)
    ok(not errs, 'no page errors %s' % errs)

    # ---------- over the 30% line, dark, big text ----------
    st = state('dark'); st['exp'].append(dict(id='E2', ts='2026-11-06 10:00:00', account='ICICI Credit Card', amount=40000, category='Shopping', remarks='Phone', photo='', payee='', mine=False))
    st['cfg'] = None
    ctx3, pg, errs = open_app(br, 'dark', 1.6, st)
    pg.evaluate("() => { commit([cfgOp('cards', {limits: {'ICICI Credit Card': 150000}})]); render(); }")
    u = pg.evaluate("() => cardUse(acc('ICICI Credit Card'))")
    ok(u['over'] and u['safe'] == -7500, 'over the line: 52,500 of 1.5L = 35%%, 7,500 over (%s)' % u)
    ok(pg.evaluate("() => nAlerts(cardUseAlerts())") == 1, 'heads-up in the bell when over the line')
    pg.evaluate("([a,b]) => { window.LedgerSms(a, '2026-11-10 22:08:00', 'X'); window.LedgerSms(b, '2026-11-10 22:09:00', 'X'); inboxSheet(); }", [SMS['debit'], SMS['credit']]); pg.wait_for_timeout(500)
    pg.screenshot(path=OUT + '5_bell_dark_160.png', full_page=False)
    ok(overflow(pg) == [], 'bell fits at 160%% text %s' % overflow(pg))
    pg.evaluate("() => ACT.acctOpen({dataset: {n: 'ICICI Credit Card'}})"); pg.wait_for_timeout(400)
    pg.screenshot(path=OUT + '6_card_dark_160.png')
    ok(overflow(pg) == [], 'card screen fits at 160%% text %s' % overflow(pg))
    # change the safe line to 50%
    pg.evaluate("() => ACT.acctEdit({dataset: {n: 'ICICI Credit Card'}})"); pg.wait_for_timeout(400)
    ok(pg.input_value('#aGuide') == '30' and pg.input_value('#aLimit').replace(',', '') == '150000', 'card form shows limit and the 30% line')
    pg.fill('#aGuide', '50'); pg.screenshot(path=OUT + '7_card_form.png'); pg.click('button[data-act=aSave]'); pg.wait_for_timeout(400)
    u = pg.evaluate("() => cardUse(acc('ICICI Credit Card'))")
    ok(u['g'] == 50 and not u['over'] and u['lim'] == 150000, 'safe line changed to 50%% and saved (%s)' % {k: u[k] for k in ('g', 'over', 'safe')})
    pg.evaluate("() => { shut(); U.mseg = 'acc'; setTab('money'); }"); pg.wait_for_timeout(500)
    pg.screenshot(path=OUT + '8_accounts_dark_160.png')
    ok(not errs, 'no page errors %s' % errs)
    # glass theme quick look
    ctx4, pg, errs = open_app(br, 'glass', 1.15)
    pg.evaluate("([a,b]) => { commit([cfgOp('cards', {limits: {'ICICI Credit Card': 150000}})]); window.LedgerSms(a, '2026-11-10 22:08:00', 'X'); window.LedgerSms(b, '2026-11-10 22:09:00', 'X'); inboxSheet(); }", [SMS['debit'], SMS['credit']]); pg.wait_for_timeout(500)
    pg.screenshot(path=OUT + '9_bell_glass.png'); ok(overflow(pg) == [] and not errs, 'glass theme fits, no errors %s %s' % (overflow(pg), errs))
    br.close()
print('\nFAILED: %d' % len(fails)); [print(' -', f) for f in fails]
