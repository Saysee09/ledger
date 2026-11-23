import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(ROOT + '/tests/shots', exist_ok=True)
# v9.3: card purchase -> EMI (by hand or from the bank's EMI SMS), EMI from a bank SMS, auto-logged card EMIs,
# #tags in small letters, note ideas without case duplicates, career analysis + hike calculator, smaller widgets
import json, time, datetime, xml.dom.minidom, glob
from playwright.sync_api import sync_playwright

URL = 'file://' + ROOT + '/index.html'
OUT = ROOT + '/tests/shots/v93_'
TD = datetime.date.today(); T = TD.isoformat(); YM = T[:7]
DD = TD.strftime('%d-%b-%y')
def ago(n): return (TD - datetime.timedelta(days=n)).isoformat()
def mshift(m, n):
    y, mo = int(m[:4]), int(m[5:7]) - 1 + n
    return '%04d-%02d' % (y + mo // 12, mo % 12 + 1)
fails = []
def ok(c, msg):
    print(('PASS ' if c else 'FAIL ') + msg)
    if not c: fails.append(msg)

def state(theme=''):
    acc = lambda i, n, t, op, **k: dict(dict(id='A%d' % i, name=n, type=t, opening=op, openingDate='2026-09-01 00:00:00', archived=False, order=i, others=False, keptIn=''), **k)
    ex = lambda i, d, a, amt, c, r: dict(id=i, ts=d + ' 10:00:00', account=a, amount=amt, category=c, remarks=r, photo='', payee='', mine=False)
    return dict(accounts=[acc(1, 'ICICI Bank', 'bank', 52000, l4='616'), acc(2, 'Kotak Bank', 'bank', 18000, l4='1211'), acc(5, 'ICICI Credit Card', 'card', 0, billDay=28, l4='8009')],
                exp=[ex('E9', ago(2), 'ICICI Credit Card', 17268.22, 'Household', 'Mobile #mom'), ex('E8', ago(1), 'ICICI Credit Card', 1408, 'Shopping', 'Clothes'),
                     ex('U1', ago(40), 'ICICI Bank', 220, 'Transportation', 'Uber'), ex('U2', ago(30), 'ICICI Bank', 180, 'Transportation', 'Uber'), ex('U3', ago(20), 'ICICI Bank', 150, 'Transportation', 'uber'),
                     ex('U4', ago(10), 'ICICI Bank', 300, 'Transportation', 'Fuel #CaR'), ex('U5', ago(9), 'ICICI Bank', 500, 'Transportation', 'Service #Car')],
                inc=[dict(id='I%d' % k, ts='%s-30 10:00:00' % mshift(YM, -k), account='ICICI Bank', amount=45210, source='Salary', remarks='', payee='') for k in (1, 2, 3)],
                cfg=dict(cards=dict(limits={'ICICI Credit Card': 150000}, guide=30), career=dict(jobs=[dict(id='J1', company='First Co', role='Designer', **{'from': '2022-12'}, to='2026-09', ctc=360000), dict(id='J2', company='New Co', role='Senior designer', **{'from': '2026-10'}, to='', ctc=600000)]),
                         profile=dict(born='1998-12', earning='2022-12', city='Mumbai', role='Designer')),
                theme=theme, prefs={})

CONV = {
 'icici': 'Dear Customer, your transaction of INR 17,268.22 at AMAZON PAY INDIA on ICICI Bank Credit Card XX8009 has been successfully converted into 6 EMIs of INR 3,047.38 each at 15.99% p.a. Processing fee of INR 199 will be levied.',
 'booked': 'EMI booked successfully on your ICICI Bank Credit Card XX8009. Loan amount: Rs 17268.22, Tenure: 6 months, EMI: Rs 3047.38.',
 'hdfc': 'Dear Customer, your request for EMI conversion of Rs.17268.22 on HDFC Bank Credit Card ending 4005 has been processed. EMI Rs.3047/- p.m. for 6 months.',
 'offer': 'Convert your purchase of INR 17,268.22 on ICICI Bank Credit Card XX8009 to EMI. SMS EMI 8009 to 5676766. T&C apply',
 'due': 'Your EMI of Rs 3047.38 for ICICI Bank Credit Card XX8009 is due on 28-Nov-26.',
}
BANK_EMI = 'ICICI Bank Acct XX616 debited for Rs 4500.00 on %s; BAJAJ FINANCE LTD credited. EMI for loan 4410. UPI:631400000009. Call 18002662 for dispute.' % DD

def open_app(br, theme='', scale=1.0, st=None):
    ctx = br.new_context(viewport=dict(width=360, height=780), device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
    pg.add_init_script("window.Chart = function(){ return {destroy(){}, update(){}} }; window.Chart.register = () => {}; window.Chart.defaults = {font:{}, plugins:{legend:{labels:{}}, tooltip:{}}, color:''}; localStorage.setItem('ledger3', %s);" % json.dumps(json.dumps(st or state(theme))))
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1500)
    if scale != 1.0: pg.evaluate("s => document.documentElement.style.fontSize = (16*s) + 'px'", scale); pg.wait_for_timeout(200)
    return ctx, pg, errs

def overflow(pg):
    return pg.evaluate("() => { const w = innerWidth; return [...document.querySelectorAll('.sheet *, #view *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > w + 1 && !e.closest('.chips:not(.wrap), .strip, .seg, .tabs, [style*=overflow]'); }).slice(0, 5).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right)); }")

def swipe(cdp, x, y, dy):
    cdp.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=x, y=y)]))
    for i in range(1, 13):
        cdp.send('Input.dispatchTouchEvent', dict(type='touchMove', touchPoints=[dict(x=x, y=y + dy * i / 12)])); time.sleep(.016)
    time.sleep(.12); cdp.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[])); time.sleep(.3)

def scroll_to_end(pg, cdp):
    sb = pg.locator('#shBody').bounding_box()
    for _ in range(8): swipe(cdp, 180, sb['y'] + sb['height'] - 60, -380)
    return pg.evaluate("() => $('#shBody').scrollTop")

with sync_playwright() as p:
    br = p.chromium.launch()
    TH = (('', 1.0), ('dark', 1.6), ('light', 1.15), ('glass', 1.3))

    # ================= EMI SMS reader =================
    ctx, pg, errs = open_app(br)
    R = {k: pg.evaluate("r => parseEmiConv(r, '%s 10:00:00')" % T, v) for k, v in CONV.items()}
    ok(R['icici'] and R['icici']['principal'] == 17268.22 and R['icici']['emi'] == 3047.38 and R['icici']['months'] == 6 and R['icici']['l4'] == '8009' and R['icici']['fee'] == 199, 'ICICI "converted into 6 EMIs of INR 3,047.38" read (%s)' % R['icici'])
    ok(R['booked'] and R['booked']['principal'] == 17268.22 and R['booked']['emi'] == 3047.38 and R['booked']['months'] == 6, '"EMI booked … Tenure 6 months, EMI Rs 3047.38" read')
    ok(R['hdfc'] and R['hdfc']['emi'] == 3047 and R['hdfc']['l4'] == '4005', 'HDFC "EMI Rs.3047/- p.m. … card ending 4005" read')
    ok(R['offer'] is None and R['due'] is None, 'EMI offers and "EMI is due" reminders are not taken as a conversion')
    ok(pg.evaluate("r => parseSms(r, nowTs())", CONV['offer']) is None, 'the offer is not a payment either')
    tip = 'INR 1,408.00 spent using ICICI Bank Card XX8009 on %s on AMAZON. Avl Limit: INR 1,28,000.00. Convert to EMI: SMS EMI 8009 to 5676766.' % DD
    ok(pg.evaluate("r => (parseSms(r, nowTs()) || {}).amount", tip) == 1408 and pg.evaluate("r => parseEmiConv(r, nowTs())", tip) is None, 'a real card spend SMS with an EMI tip at the end is still read as the spend')
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= turn a card purchase into EMI, by hand, 4 themes =================
    for theme, scale in TH:
        ctx, pg, errs = open_app(br, theme, scale)
        cdp = ctx.new_cdp_session(pg)
        tag = '[%s %.2f]' % (theme or 'auto', scale)
        owed0 = pg.evaluate("() => cardDue(acc('ICICI Credit Card'))")
        pg.evaluate("() => entrySheet('Expenses', 'E9')"); pg.wait_for_timeout(400)
        ok(pg.locator('#sheet [data-act=emiConv]').count() == 1, tag + ' card purchase shows "📆 Turn into EMI"')
        pg.evaluate("() => entrySheet('Expenses', 'U1')"); pg.wait_for_timeout(200)
        ok(pg.locator('#sheet [data-act=emiConv]').count() == 0, tag + ' small bank spend has no EMI button')
        pg.evaluate("() => entrySheet('Expenses', 'E9')"); pg.wait_for_timeout(300)
        pg.click('#sheet [data-act=emiConv]'); pg.wait_for_timeout(400)
        ok(pg.locator('#ecForm').count() == 1 and pg.locator('#ecForm [data-act=ecMo][data-v="6"].on').count() == 1, tag + ' EMI sheet opens, 6 months picked')
        pg.fill('#ecEmi', '3,047.38'); pg.wait_for_timeout(200)
        h = pg.inner_text('#ecHint')
        ok('6 × ₹3,047 = ₹18,284' in h and '₹1,016 extra' in h, tag + ' hint: 6 × ₹3,047 = ₹18,284 · ₹1,016 extra (%s)' % h.replace('\n', ' '))
        ok(overflow(pg) == [], tag + ' EMI sheet fits 360px %s' % overflow(pg))
        pg.screenshot(path=OUT + '1_emi_sheet_%s.png' % (theme or 'auto'))
        y = scroll_to_end(pg, cdp)
        ok(pg.locator('#sheet [data-act=ecSave]').is_visible(), tag + ' finger scroll reaches "Turn into EMI" (scrollTop %d)' % y)
        if scale == 1.0 or theme == 'dark':
            pg.click('#sheet [data-act=ecSave]'); pg.wait_for_timeout(500)
            r = pg.evaluate("""() => { const m = S.emis[0], x = emiX(m), j = S.adj.find(a => a.id === x.adj); return { n: S.emis.length, acc: m.account, amt: m.amount, tot: m.total, day: m.dueDay, start: m.startMonth, auto: x.auto, exp: x.exp, pr: x.principal, adj: j && j.amount, adjAcc: j && j.account, owed: cardDue(acc('ICICI Credit Card')), use: cardUse(acc('ICICI Credit Card')), spentE9: S.exp.some(e => e.id === 'E9') }; }""")
            want_start = YM if TD.day <= 28 else mshift(YM, 1)
            ok(r['n'] == 1 and r['acc'] == 'ICICI Credit Card' and r['amt'] == 3047.38 and r['tot'] == 6 and r['day'] == 28 and r['start'] == want_start and r['auto'] and r['exp'] == 'E9' and r['pr'] == 17268.22, tag + ' EMI saved: card, 6 × 3,047.38, bill day 28, first %s, logs itself (%s)' % (want_start, {k: r[k] for k in ('acc', 'amt', 'tot', 'day', 'start', 'auto')}))
            logged = pg.evaluate("() => S.emi.length")
            ok(r['adj'] == 17268.22 and r['adjAcc'] == 'ICICI Credit Card' and r['spentE9'], tag + ' card gets the purchase back (+17,268.22), the purchase stays in spending')
            ok(abs(r['owed'] - (owed0 - 17268.22 + 3047.38 * logged)) < .01, tag + ' card owes %s (was %s, %d EMI logged)' % (r['owed'], owed0, logged))
            ok(abs(r['use']['emi'] - 17268.22 * (6 - logged) / 6) < .05 and abs(r['use']['due'] - (r['owed'] + r['use']['emi'])) < .05, tag + ' limit used still counts the EMI principal left (%s)' % r['use']['emi'])
            pg.evaluate("() => entrySheet('Expenses', 'E9')"); pg.wait_for_timeout(300)
            tx = pg.inner_text('#sheet')
            ok('On EMI' in tx and '6 × ₹3,047' in tx and pg.locator('#sheet [data-act=emiEdit]').count() == 1 and pg.locator('#sheet [data-act=emiConv]').count() == 0, tag + ' purchase shows "📆 On EMI · 6 × ₹3,047.38" + See the EMI')
            ok(abs(pg.evaluate("() => emiCost({ emiId: S.emis[0].id, amount: 3047.38 })") - 169.34) < .01, tag + ' each EMI counts only ₹169.34 extra as cost (no double counting)')
            pg.evaluate("() => { U.mseg = 'emis'; setTab('money'); }"); pg.wait_for_timeout(400)
            pg.evaluate("() => { const b = [...document.querySelectorAll('[data-act]')].find(x => /^EMIs/.test(x.textContent.trim())); if (b) b.click(); }"); pg.wait_for_timeout(400)
            tx = pg.inner_text('#view')
            ok('logs itself' in tx and 'bought for' in tx and pg.locator('#view [data-act=emiPay]').count() == 0, tag + ' EMI card: "⚡ logs itself", "bought for ₹17,268.22", no Pay button')
            ok(overflow(pg) == [], tag + ' EMIs page fits %s' % overflow(pg))
            pg.screenshot(path=OUT + '2_emis_%s.png' % (theme or 'auto'), full_page=True)
            pg.evaluate("() => ACT.accOpen ? ACT.accOpen({dataset: {n: 'ICICI Credit Card'}}) : 0"); pg.wait_for_timeout(300)
        ok(not errs, tag + ' no page errors %s' % errs); ctx.close()

    # ---- auto-log: an EMI started 2 months ago logs past months once ----
    ctx, pg, errs = open_app(br)
    st = mshift(YM, -2)
    pg.evaluate("st => { commit([up('EMIs', {id: 'M1', name: 'Phone', amount: 3000, dueDay: 5, account: 'ICICI Credit Card', startMonth: st, total: 6, paidBefore: 0, active: true, note: ''}), emixOp('M1', {auto: true, from: st})]); }", st)
    n1 = pg.evaluate("() => runEmiAuto()"); n2 = pg.evaluate("() => runEmiAuto()")
    want = 2 + (1 if TD.day >= 5 else 0)
    per = pg.evaluate("() => S.emi.map(e => e.period).sort()")
    ok(n1 == want and n2 == 0 and per[0] == st, 'auto-log: %d past EMIs logged once, nothing twice (%s, %s)' % (want, n1, per))
    ok(pg.evaluate("() => emiDue().length") == 0, 'auto EMIs never nag "to pay" in the bell')
    # delete the converted EMI puts the purchase back on the card
    pg.evaluate("() => { entrySheet('Expenses', 'E9'); ACT.emiConv({dataset: {id: 'E9'}}); $('#ecEmi').value = '3047.38'; ACT.ecSave(); }"); pg.wait_for_timeout(300)
    mid = pg.evaluate("() => emiOfExp('E9').id"); o0 = pg.evaluate("() => cardDue(acc('ICICI Credit Card'))")
    pg.on('dialog', lambda d: d.accept())
    pg.evaluate("id => { ACT.emiEdit({dataset: {id}}); }", mid); pg.wait_for_timeout(300)
    pg.click('#sheet [data-act=emDel]'); pg.wait_for_timeout(400)
    r = pg.evaluate("() => [!!emiOfExp('E9'), S.adj.length, cardDue(acc('ICICI Credit Card'))]")
    ok(r[0] is False and r[1] == 0 and abs(r[2] - (o0 + 17268.22)) < .01, 'deleting the EMI puts the purchase back on the card: owed %s -> %s' % (o0, r[2]))
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= the bank's EMI SMS -> bell -> link =================
    for theme, scale in (('', 1.0), ('dark', 1.6), ('glass', 1.3)):
        ctx, pg, errs = open_app(br, theme, scale)
        tag = '[%s %.2f]' % (theme or 'auto', scale)
        v = pg.evaluate("r => window.LedgerSms(r, nowTs(), 'ICICIB')", CONV['icici'])
        v2 = pg.evaluate("r => window.LedgerSms(r, nowTs(), 'ICICIB')", CONV['booked'])
        v3 = pg.evaluate("r => window.LedgerSms(r, nowTs(), 'ICICIB')", CONV['offer'])
        ok(v is True and v2 is False and v3 is False, tag + ' conversion SMS kept once; the 2nd SMS of the same EMI and the offer are dropped (%s %s %s)' % (v, v2, v3))
        ok(pg.evaluate("() => pendNew().length") == 0, tag + ' it does not land in "to sort" as a payment')
        pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(400)
        al = pg.locator('#sheet .alert', has_text='turned into EMI')
        ok(al.count() == 1 and 'Mobile' in al.inner_text() and '3,047' in al.inner_text(), tag + ' bell: "₹17,268.22 turned into EMI · ICICI Credit Card · 6 months · Mobile #mom"')
        ok(overflow(pg) == [], tag + ' bell fits %s' % overflow(pg))
        pg.screenshot(path=OUT + '3_bell_%s.png' % (theme or 'auto'))
        al.locator('button[data-act=emiSmsOpen]').click(); pg.wait_for_timeout(400)
        r = pg.evaluate("() => [U.ec.exp, $('#ecEmi').value, U.ec.months]")
        ok(r == ['E9', '3047.38', 6], tag + ' Link opens the EMI sheet with the purchase, 6 months and ₹3,047.38 filled in (%s)' % r)
        ok(overflow(pg) == [], tag + ' link sheet fits %s' % overflow(pg))
        pg.screenshot(path=OUT + '4_link_%s.png' % (theme or 'auto'))
        pg.evaluate("() => ACT.ecSave()"); pg.wait_for_timeout(400)
        r = pg.evaluate("() => [S.emis.length, emiSmsList()[0].done === S.emis[0].id, emiSmsAlerts() === '', !!emiOfExp('E9')]")
        ok(r == [1, True, True, True], tag + ' linked: EMI made, SMS filed, bell line gone (%s)' % r)
        ok(not errs, tag + ' no page errors %s' % errs); ctx.close()

    # SMS with no matching purchase; and ✕
    ctx, pg, errs = open_app(br)
    pg.evaluate("r => window.LedgerSms(r, nowTs(), 'HDFCBK')", CONV['hdfc'])
    pg.evaluate("() => ACT.emiSmsOpen({dataset: {id: emiSmsList()[0].id}})"); pg.wait_for_timeout(300)
    ok(pg.evaluate("() => U.ec.exp") == 'E9', 'card not in Brokeless (HDFC): the same-amount card purchase is still offered')
    pg.click('#sheet [data-act=ecExp][data-id=""]'); pg.wait_for_timeout(200)
    ok(pg.evaluate("() => U.ec.exp") == '' and 'Not logged in Brokeless' in pg.inner_text('#sheet'), 'no matching purchase: "Not logged in Brokeless" picked')
    pg.evaluate("() => ACT.ecSave()"); pg.wait_for_timeout(300)
    r = pg.evaluate("() => [S.emis.length, S.adj.length, emiCost({emiId: S.emis[0].id, amount: 3047})]")
    ok(r == [1, 0, 3047], 'then only the EMIs are logged, each in full, no card credit (%s)' % r)
    ctx.close()
    ctx, pg, errs = open_app(br)
    pg.evaluate("r => window.LedgerSms(r, nowTs(), 'ICICIB')", CONV['icici'])
    pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(300)
    pg.click('#sheet .alert button[data-act=emiSmsDrop]'); pg.wait_for_timeout(300)
    ok(pg.evaluate("() => emiSmsAlerts()") == '' and pg.evaluate("() => emiSmsList()[0].dropped") is True, '✕ hides the EMI line')
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= a bank EMI SMS goes to your EMI =================
    for theme, scale in (('', 1.0), ('dark', 1.6)):
        ctx, pg, errs = open_app(br, theme, scale)
        cdp = ctx.new_cdp_session(pg)
        tag = '[%s %.2f]' % (theme or 'auto', scale)
        pg.evaluate("() => commit([up('EMIs', {id: 'MB', name: 'Bike loan', amount: 4500, dueDay: 5, account: 'ICICI Bank', startMonth: shiftM(ym(), -3), total: 24, paidBefore: 3, active: true, note: ''})])")
        pg.evaluate("r => window.LedgerSms(r, nowTs(), 'ICICIB')", BANK_EMI)
        pid = pg.evaluate("() => pendNew()[0].id")
        pg.evaluate("id => ACT.pendPick({dataset: {id}})", pid); pg.wait_for_timeout(400)
        r = pg.evaluate("() => [U.pd.act, U.pd.emi, U.pd.account]")
        ok(r == ['emi', 'MB', 'ICICI Bank'], tag + ' SMS saying "EMI" with the same amount -> 📆 EMI · Bike loan filled in (%s)' % r)
        ok(pg.locator('#sheet #pdPer').count() == 1 and pg.input_value('#pdPer') == YM, tag + ' for month = this month')
        ok(overflow(pg) == [], tag + ' sheet fits %s' % overflow(pg))
        pg.screenshot(path=OUT + '5_sms_emi_%s.png' % (theme or 'auto'))
        scroll_to_end(pg, cdp)
        b0 = pg.evaluate("() => C.bal['ICICI Bank']")
        pg.click('#sheet [data-act=pdSave]'); pg.wait_for_timeout(400)
        r = pg.evaluate("() => [S.emi.length, S.emi[0].emiId, S.emi[0].period, C.bal['ICICI Bank'], S.exp.filter(e => e.amount === 4500).length, emiState(S.emis[0]).st]")
        ok(r[0] == 1 and r[1] == 'MB' and r[2] == YM and r[3] == b0 - 4500 and r[4] == 0 and r[5] == 'paid', tag + ' logged as the Bike loan EMI for this month, not an expense (%s)' % r)
        ok(pg.evaluate("() => (payeeFind('Bajaj Finance Ltd') || {}).act") == 'emi', tag + ' payee remembered as EMI')
        ok(not errs, tag + ' no page errors %s' % errs); ctx.close()
    # an EMI SMS when that EMI already logged itself -> filed quietly
    ctx, pg, errs = open_app(br)
    pg.evaluate("() => { commit([up('EMIs', {id: 'MB', name: 'Bike loan', amount: 4500, dueDay: 1, account: 'ICICI Bank', startMonth: ym(), total: 24, paidBefore: 0, active: true, note: ''}), emixOp('MB', {auto: true, from: ym()})]); runEmiAuto(); }")
    pg.evaluate("r => window.LedgerSms(r, nowTs(), 'ICICIB')", BANK_EMI)
    pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(300)
    r = pg.evaluate("() => [S.emi.length, pendNew().length, S.pend[0].done === S.emi[0].id]")
    ok(r == [1, 0, True], 'EMI already logged by itself: its SMS is filed quietly, nothing counted twice (%s)' % r)
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= tags + note ideas =================
    ctx, pg, errs = open_app(br)
    r = pg.evaluate("() => S.exp.filter(e => /#/.test(e.remarks)).map(e => e.remarks).sort()")
    ok(r == ['Fuel #car', 'Mobile #mom', 'Service #car'], 'older #CaR / #Car saved again as #car at start (%s)' % r)
    ok(pg.evaluate("() => S.outbox.filter(o => o.sheet === 'Expenses').length") == 2, 'only the 2 rows that needed it are sent to the Sheet')
    pg.evaluate("() => commit([up('Expenses', {id: 'X1', ts: nowTs(), account: 'ICICI Bank', amount: 99, category: 'Food', remarks: 'Snacks #Goa #GOA-Trip', photo: '', payee: ''})])")
    ok(pg.evaluate("() => S.exp.find(e => e.id === 'X1').remarks") == 'Snacks #goa #goa-trip', 'new note "Snacks #Goa #GOA-Trip" saved as "Snacks #goa #goa-trip"')
    ok(pg.evaluate("() => allTags().filter(t => t === '#car').length") == 1, 'one #car tag in the tag chips')
    pg.evaluate("() => compose('exp')"); pg.wait_for_timeout(400)
    pg.evaluate("() => { U.c.cat = 'Transportation'; updCompose(); }"); pg.wait_for_timeout(200)
    chips = pg.evaluate("() => [...document.querySelectorAll('#remSug [data-act=sug]')].map(b => b.textContent)")
    ok(chips.count('Uber') == 1 and 'uber' not in chips, 'note ideas: "Uber" once, no separate "uber" (%s)' % chips)
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= career: analysis + hike calculator =================
    ctx, pg, errs = open_app(br)
    t = pg.evaluate("() => [taxNew(0), taxNew(1200000), taxNew(1210000), taxNew(1275000), payOf(1500000, 'cap').tax, payOf(600000, 'cap').inHand]")
    ok(t[:5] == [0, 0, 10400, 74100, 94130], 'tax (new regime): ₹12L taxable = 0, ₹12.1L = 10,400 (marginal relief), ₹12.75L = 74,100, CTC ₹15L = 94,130 (%s)' % t)
    ok(t[5] == 46192, 'CTC ₹6L → ≈ ₹46,192/month in hand (PF ₹1,800, PT) (%s)' % t[5])
    ctx.close()
    for theme, scale in TH:
        ctx, pg, errs = open_app(br, theme, scale)
        cdp = ctx.new_cdp_session(pg)
        tag = '[%s %.2f]' % (theme or 'auto', scale)
        pg.evaluate("() => { U.pt = 'career'; pulseSheet(); }"); pg.wait_for_timeout(500)
        tx = pg.inner_text('#sheet')
        ok('analysis' in tx.lower() and 'In-hand (estimate)' in tx and '45,210' in tx and 'next review' in tx, tag + ' Career → Analysis: CTC, in-hand, salary reaching the bank, next review target')
        ok(overflow(pg) == [], tag + ' career tab fits %s' % overflow(pg))
        y = scroll_to_end(pg, cdp)
        ok(pg.locator('#sheet [data-act=hikeOpen]').is_visible(), tag + ' "🧮 Hike calculator" is at the end of Career (scrollTop %d)' % y)
        pg.screenshot(path=OUT + '6_career_%s.png' % (theme or 'auto'))
        pg.click('#sheet [data-act=hikeOpen]'); pg.wait_for_timeout(400)
        ok(pg.input_value('#hkBase').replace(',', '') == '600000', tag + ' calculator starts from your CTC ₹6,00,000')
        pg.click('#sheet [data-act=hkPct][data-v="20"]'); pg.wait_for_timeout(200)
        tx = pg.inner_text('#hkOut')
        ok('7,20,000' in tx and '60,000' in tx and 'Reaches your bank' in tx, tag + ' 20%% → ₹7,20,000 a year, ₹60,000 a month, what reaches your bank')
        ok(overflow(pg) == [], tag + ' calculator fits 360px %s' % overflow(pg))
        pg.screenshot(path=OUT + '7_hike_%s.png' % (theme or 'auto'))
        pg.fill('#hkPctIn', '12.5'); pg.wait_for_timeout(200)
        ok('6,75,000' in pg.inner_text('#hkOut') and pg.locator('#sheet [data-act=hkPct].on').count() == 0, tag + ' typed 12.5% → ₹6,75,000')
        pg.click('#sheet [data-act=hkMode][data-v=offer]'); pg.wait_for_timeout(300)
        pg.fill('#hkOffer', '9,00,000'); pg.wait_for_timeout(200)
        ok('+50%' in pg.inner_text('#hkOut'), tag + ' offer ₹9,00,000 → +50%')
        pg.click('#sheet [data-act=hkPer][data-v=m]'); pg.wait_for_timeout(300)
        ok(pg.input_value('#hkBase').replace(',', '') == '50000' and pg.input_value('#hkOffer').replace(',', '') == '75000', tag + ' monthly view: ₹50,000 now, offer ₹75,000 a month')
        pg.fill('#hkBase', '40000'); pg.wait_for_timeout(200)
        ok('+87.5%' in pg.inner_text('#hkOut') and 'Reaches your bank' not in pg.inner_text('#hkOut'), tag + ' any amount: ₹40,000/month vs ₹75,000 offer = +87.5% (no "your bank" row for a typed amount)')
        y = scroll_to_end(pg, cdp)
        ok(pg.locator('#sheet [data-act=jbBack]').is_visible(), tag + ' finger scroll reaches "Back to Money Pulse"')
        ok(not errs, tag + ' no page errors %s' % errs); ctx.close()
    # save a hike
    ctx, pg, errs = open_app(br)
    pg.on('dialog', lambda d: d.accept())
    pg.evaluate("() => { U.pt = 'career'; pulseSheet(); ACT.hikeOpen(); }"); pg.wait_for_timeout(300)
    pg.click('#sheet [data-act=hkPct][data-v="15"]'); pg.wait_for_timeout(200)
    pg.click('#sheet [data-act=hkSave]'); pg.wait_for_timeout(400)
    J = pg.evaluate("() => S.cfg.career.jobs.map(j => [j.company, j.from, j.to, j.ctc])")
    ok(J[-1] == ['New Co', YM, '', 690000] and J[1][2] == mshift(YM, -1), '"I got this" adds New Co ₹6,90,000 from this month, the old row ends last month (%s)' % J)
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= widgets =================
    W = ROOT + '/android/app/src/main/res/'
    for f in glob.glob(W + 'layout/widget_*.xml') + glob.glob(W + 'xml/widget_*_info.xml'): xml.dom.minidom.parse(f)
    ok(True, 'widget XML files parse')
    cells = {os.path.basename(f): xml.dom.minidom.parse(f).documentElement.getAttribute('android:targetCellHeight') for f in glob.glob(W + 'xml/widget_*_info.xml')}
    ok(all(v == '1' for v in cells.values()), 'every widget is one row high by default (%s)' % cells)
    br.close()

print('FAILED: %d' % len(fails))
for f in fails: print(' -', f)
