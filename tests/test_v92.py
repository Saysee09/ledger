import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(ROOT + '/tests/shots', exist_ok=True)
# v9.2: self-transfer from two SMS, "Money paid" sheet extras (split, for me, tags, first-time suggestions, bill match), goal instalments
import json, time, datetime
from playwright.sync_api import sync_playwright

URL = 'file://' + ROOT + '/index.html'
OUT = ROOT + '/tests/shots/v92_'
T = datetime.date.today().isoformat(); YM = T[:7]
DD = datetime.date.today().strftime('%d-%b-%y')
fails = []
def ok(c, msg):
    print(('PASS ' if c else 'FAIL ') + msg)
    if not c: fails.append(msg)

def state(theme=''):
    acc = lambda i, n, t, op, **k: dict(dict(id='A%d' % i, name=n, type=t, opening=op, openingDate='2026-10-01 00:00:00', archived=False, order=i, others=False, keptIn=''), **k)
    return dict(accounts=[acc(1, 'ICICI Bank', 'bank', 52000, l4='616'), acc(2, 'Kotak Bank', 'bank', 18000, l4='1211'), acc(3, 'Cash in hand', 'cash', 900),
                          acc(4, 'Mom', 'bank', 20000, others=True, keptIn='Kotak Bank'), acc(5, 'ICICI Credit Card', 'card', 0, billDay=28, l4='4005')],
                exp=[dict(id='E1', ts='2026-10-14 10:00:00', account='ICICI Bank', amount=899, category='Household', remarks='Phone recharge', photo='', payee='', mine=False),
                     dict(id='E2', ts='2026-10-20 10:00:00', account='ICICI Bank', amount=250, category='Food', remarks='Breakfast #office', photo='', payee='', mine=False),
                     dict(id='E3', ts='2026-10-22 10:00:00', account='ICICI Bank', amount=180, category='Food', remarks='Lunch', photo='', payee='', mine=False)],
                rem=[dict(id='R1', name='Electricity bill', kind='bill', amount=530, account='ICICI Bank', category='Household', every=1, unit='month', next=T, time='09:00', auto=False, cal=False, active=True, snooze='', lastDone='', note='')],
                goals=[dict(id='G1', name='TV payback', kind='payback', target=55000, account='Kotak Bank', icon='📺', color='#A855F7', archived=False, created='2026-09-01 10:00:00', deadline='')],
                goal=[dict(id='GL1', ts='2026-09-01 10:00:00', goal='TV payback', action='Opening', amount=15000, account='Kotak Bank', remarks='', goalId='G1', ref=''),
                      dict(id='GL2', ts=T + ' 09:00:00', goal='TV payback', action='Add', amount=2000, account='Kotak Bank', remarks='', goalId='G1', ref='')],
                loans=[dict(id='L1', name='Rahul', dir='owed', note='', archived=False, created='2026-10-01 10:00:00')],
                theme=theme, prefs={})

SMS = {
 'out':  'ICICI Bank Acct XX616 debited for Rs 5000.00 on %s; SAYALI credited. UPI:631412345678. Call 18002662 for dispute. SMS BLOCK 616 to 9215676766.' % DD,
 'in':   'Received Rs.5000.00 in your Kotak Bank AC X1211 from sayali@okicici on %s.UPI Ref:631412345678.' % DD,
 'adani':'ICICI Bank Acct XX616 debited for Rs 530.00 on %s; ADANI ELECTRICI credited. UPI:631400000001. Call 18002662 for dispute. SMS BLOCK 616 to 9215676766.' % DD,
 'swig': 'ICICI Bank Acct XX616 debited for Rs 600.00 on %s; SWIGGY credited. UPI:631400000002. Call 18002662 for dispute. SMS BLOCK 616 to 9215676766.' % DD,
 'tok':  'Rs 2000.00 debited from ICICI Bank Acc XX616 on %s and credited to A/c XX1211 IMPS Ref 631400000003. To dispute call 18002662' % DD,
}

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

def sms(pg, k, t):
    return pg.evaluate("([r, t]) => window.LedgerSms(r, t, 'BANK')", [SMS[k], T + ' ' + t])

def swipe(cdp, x, y, dy):
    cdp.send('Input.dispatchTouchEvent', dict(type='touchStart', touchPoints=[dict(x=x, y=y)]))
    for i in range(1, 13):
        cdp.send('Input.dispatchTouchEvent', dict(type='touchMove', touchPoints=[dict(x=x, y=y + dy * i / 12)])); time.sleep(.016)
    time.sleep(.12); cdp.send('Input.dispatchTouchEvent', dict(type='touchEnd', touchPoints=[])); time.sleep(.3)

with sync_playwright() as p:
    br = p.chromium.launch()
    # ================= self-transfer: both SMS -> one line =================
    ctx, pg, errs = open_app(br)
    P = pg.evaluate("([a,b]) => [parseSms(a, '%s 10:00:00'), parseSms(b, '%s 10:00:00')]" % (T, T), [SMS['out'], SMS['in']])
    ok(P[0] and P[0]['dir'] == 'debit' and P[1] and P[1]['dir'] == 'credit', 'SMS read: ICICI out, Kotak in (%s / %s)' % ((P[0] or {}).get('l4'), (P[1] or {}).get('l4')))
    sms(pg, 'out', '10:44:00'); sms(pg, 'in', '10:44:30')
    acs = pg.evaluate("() => pendNew().map(p => p.account)")
    ok(sorted(acs) == ['ICICI Bank', 'Kotak Bank'], 'SMS matched to ICICI and Kotak (%s)' % acs)
    sp = pg.evaluate("() => selfPairs().map(x => [x.from, x.to, x.amount])")
    ok(sp == [['ICICI Bank', 'Kotak Bank', 5000]], 'joined into one self-transfer (%s)' % sp)
    ok(pg.evaluate("() => pendSort().length") == 0, 'both SMS leave "to sort"')
    pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(500)
    ok(pg.locator('.alert.cpay').count() == 1 and 'Moved' in pg.inner_text('.alert.cpay'), 'bell shows "Moved ₹5,000 to Kotak Bank?"')
    ok(overflow(pg) == [], 'bell fits 360px %s' % overflow(pg))
    pg.screenshot(path=OUT + '1_self_bell.png')
    b0 = pg.evaluate("() => [C.bal['ICICI Bank'], C.bal['Kotak Bank'], S.exp.length, S.inc.length]")
    pg.click('.alert.cpay button[data-act=stYes]'); pg.wait_for_timeout(500)
    b1 = pg.evaluate("() => [C.bal['ICICI Bank'], C.bal['Kotak Bank'], S.exp.length, S.inc.length, S.trf.length, S.pend.filter(p => p.status === 'done').length, selfPairs().length]")
    ok(b1[0] == b0[0] - 5000 and b1[1] == b0[1] + 5000 and b1[2] == b0[2] and b1[3] == b0[3] and b1[4] == 1 and b1[5] == 2 and b1[6] == 0, 'one tap: ICICI −5,000, Kotak +5,000, no expense/income, 1 transfer, both SMS filed (%s -> %s)' % (b0, b1))
    # next time, the same payee is suggested as a transfer
    ok(pg.evaluate("() => (payeeFind('Sayali') || {}).act") == 'trf', 'payee remembered as a transfer')
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ---- Not this ----
    ctx, pg, errs = open_app(br)
    sms(pg, 'out', '10:44:00'); sms(pg, 'in', '10:45:00')
    pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(300)
    pg.click('.alert.cpay button[data-act=stNo]'); pg.wait_for_timeout(300)
    ok(pg.evaluate("() => [selfPairs().length, pendSort().length]") == [0, 2], '"Not this" -> both back in "to sort"')
    ctx.close()

    # ---- filed one side as a transfer by hand in the sheet, the other side comes later ----
    ctx, pg, errs = open_app(br)
    sms(pg, 'out', '10:44:00')
    pid = pg.evaluate("() => pendNew()[0].id")
    pg.evaluate("id => ACT.pendPick({dataset: {id}})", pid); pg.wait_for_timeout(300)
    pg.click('#sheet [data-act=pdSet][data-f=act][data-v=trf]'); pg.wait_for_timeout(200)
    pg.click('#sheet [data-act=pdSet][data-f=to][data-v="Kotak Bank"]'); pg.wait_for_timeout(200)
    pg.click('#sheet [data-act=pdSave]'); pg.wait_for_timeout(400)
    sms(pg, 'in', '10:46:00'); pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(300)
    r = pg.evaluate("() => [S.trf.length, pendNew().length, C.bal['Kotak Bank']]")
    ok(r[0] == 1 and r[1] == 0 and r[2] == 23000, 'second SMS filed quietly against the transfer, nothing counted twice (%s)' % r)
    ctx.close()

    # ---- logged by hand first, both SMS later ----
    ctx, pg, errs = open_app(br)
    pg.evaluate("() => commit([up('Transfers', {id: 'TX', ts: nowTs(), from: 'ICICI Bank', to: 'Kotak Bank', amount: 5000, remarks: 'Moved'})])")
    sms(pg, 'out', pg.evaluate("() => nowTs().slice(11)")); sms(pg, 'in', pg.evaluate("() => nowTs().slice(11)"))
    pg.evaluate("() => inboxSheet()"); pg.wait_for_timeout(300)
    r = pg.evaluate("() => [S.trf.length, pendNew().length, selfPairs().length]")
    ok(r == [1, 0, 0], 'hand-logged transfer: both SMS filed quietly, no second transfer (%s)' % r)
    ctx.close()

    # ---- one SMS naming your other account ----
    ctx, pg, errs = open_app(br)
    sms(pg, 'tok', '11:00:00')
    pid = pg.evaluate("() => pendNew()[0].id")
    pg.evaluate("id => ACT.pendPick({dataset: {id}})", pid); pg.wait_for_timeout(300)
    r = pg.evaluate("() => [U.pd.act, U.pd.to, U.pd.account]")
    ok(r == ['trf', 'Kotak Bank', 'ICICI Bank'], 'SMS that names A/c XX1211 -> filled in as transfer to Kotak (%s)' % r)
    ctx.close()

    # ================= Money paid sheet =================
    for theme, scale in (('', 1.0), ('dark', 1.6), ('light', 1.15), ('glass', 1.3)):
        ctx, pg, errs = open_app(br, theme, scale)
        cdp = ctx.new_cdp_session(pg)
        sms(pg, 'adani', '10:44:00')
        pid = pg.evaluate("() => pendNew()[0].id")
        pg.evaluate("id => ACT.pendPick({dataset: {id}})", pid); pg.wait_for_timeout(400)
        tx = pg.inner_text('#sheet')
        ok('First time with' in tx and 'Electricity bill' in tx, '[%s %.2f] first-time payee shows suggestions incl. your bill' % (theme or 'auto', scale))
        r = pg.evaluate("() => [U.pd.cat, U.pd.note, U.pd.rem, U.pd.fi]")
        ok(r[0] == 'Household' and r[1] == 'Electricity bill' and r[2] == 'R1' and r[3] == 0, '[%s] exact bill amount -> filled in (%s)' % (theme or 'auto', r))
        ok(pg.locator('#sheet [data-act=pdSplitT]').count() == 1, '[%s] Split bill button on the SMS sheet' % (theme or 'auto'))
        ok(pg.locator('#sheet [data-act=pdNote]').count() >= 1, '[%s] note suggestions shown (%d)' % (theme or 'auto', pg.locator('#sheet [data-act=pdNote]').count()))
        ok(pg.locator('#sheet [data-act=pdTag]').count() >= 1, '[%s] #tag chips shown' % (theme or 'auto'))
        ok(overflow(pg) == [], '[%s %.2f] sheet fits 360px %s' % (theme or 'auto', scale, overflow(pg)))
        pg.screenshot(path=OUT + '2_sheet_%s.png' % (theme or 'auto'))
        # finger scroll inside the sheet reaches Save
        sb = pg.locator('#shBody').bounding_box()
        for _ in range(6): swipe(cdp, 180, sb['y'] + sb['height'] - 60, -380)
        y = pg.evaluate("() => $('#shBody').scrollTop")
        ok(y > 50 and pg.locator('#sheet [data-act=pdSave]').is_visible(), '[%s] finger scroll moves the sheet (scrollTop %d)' % (theme or 'auto', y))
        pg.screenshot(path=OUT + '3_sheet_bottom_%s.png' % (theme or 'auto'))
        if scale == 1.0:
            pg.click('#sheet [data-act=pdSave]'); pg.wait_for_timeout(400)
            r = pg.evaluate("() => [S.exp.find(e => e.amount === 530).category, S.exp.find(e => e.amount === 530).remarks, S.rem[0].next > today()]")
            ok(r == ['Household', 'Electricity bill', True], 'saved as Household · Electricity bill, the bill moves to next month (%s)' % r)
        ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ---- split from SMS ----
    ctx, pg, errs = open_app(br)
    sms(pg, 'swig', '13:00:00')
    pid = pg.evaluate("() => pendNew()[0].id")
    pg.evaluate("id => ACT.pendPick({dataset: {id}})", pid); pg.wait_for_timeout(300)
    if pg.evaluate("() => U.pd.cat") != 'Food': pg.click('#sheet [data-act=pdSet][data-f=cat][data-v=Food]'); pg.wait_for_timeout(200)
    ok('Lunch' in pg.inner_text('#sheet') and 'Breakfast #office' in pg.inner_text('#sheet'), 'Food picked -> your usual Food notes suggested')
    pg.fill('#pdRemk', 'Dinner')
    pg.click('#sheet [data-act=pdSplitT]'); pg.wait_for_timeout(200)
    pg.click('#sheet [data-act=pdSplitP][data-v=Rahul]'); pg.wait_for_timeout(200)
    pg.fill('#pdSpName', 'Ankit'); pg.click('#sheet [data-act=pdSplitAdd]'); pg.wait_for_timeout(200)
    ok(pg.input_value('#pdRemk') == 'Dinner', 'note kept while splitting')
    ok('each friend owes you' in pg.inner_text('#sheet'), 'split summary shown')
    ok(overflow(pg) == [], 'split box fits %s' % overflow(pg))
    pg.screenshot(path=OUT + '4_split.png')
    b0 = pg.evaluate("() => C.bal['ICICI Bank']")
    pg.click('#sheet [data-act=pdSave]'); pg.wait_for_timeout(400)
    r = pg.evaluate("() => { const e = S.exp.find(x => x.payee && /swiggy/i.test(x.payee)); return [e.amount, e.remarks, S.loan.filter(l => l.ref === e.id && l.action === 'Lend').map(l => l.person + ':' + l.amount).sort(), C.bal['ICICI Bank']]; }")
    ok(r[0] == 200 and r[1] == 'Dinner · split ÷3' and r[2] == ['Ankit:200', 'Rahul:200'] and r[3] == b0 - 600, 'split ÷3: your expense 200, Rahul and Ankit owe 200 each, ICICI −600 (%s)' % r)
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ---- paid from Mom's money, for me ----
    ctx, pg, errs = open_app(br)
    sms(pg, 'swig', '13:00:00')
    pid = pg.evaluate("() => pendNew()[0].id")
    pg.evaluate("id => ACT.pendPick({dataset: {id}})", pid); pg.wait_for_timeout(300)
    pg.click('#sheet [data-act=pdSet][data-f=account][data-v=Mom]'); pg.wait_for_timeout(200)
    if pg.evaluate("() => U.pd.cat") != 'Food': pg.click('#sheet [data-act=pdSet][data-f=cat][data-v=Food]'); pg.wait_for_timeout(200)
    ok(pg.locator('#sheet [data-act=pdMine]').count() == 2, '"Who was it for?" shown for Mom\'s money')
    pg.click('#sheet [data-act=pdMine][data-v="1"]'); pg.wait_for_timeout(200)
    pg.click('#sheet [data-act=pdSave]'); pg.wait_for_timeout(400)
    r = pg.evaluate("() => { const e = S.exp.find(x => x.account === 'Mom'); return [e.mine, heldOwed('Mom')]; }")
    ok(r == [True, 600], 'for me: counted as mine, you owe Mom ₹600 (%s)' % r)
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= goals =================
    for theme, scale in (('', 1.0), ('dark', 1.6), ('glass', 1.3)):
        ctx, pg, errs = open_app(br, theme, scale)
        pg.evaluate("() => { commit([cfgOp('goalplan', {G1: 5000})]); U.pseg = 'goals'; setTab('goals'); }"); pg.wait_for_timeout(500)
        I = pg.evaluate("() => goalInstInfo(goalById('G1'))")
        exp_end = pg.evaluate("() => shiftM(ym(), 7)")
        ok(I['total'] == 11 and I['paid'] == 3 and I['mLeft'] == 8 and I['mIn'] == 2000 and not I['mDone'] and I['end'] == exp_end, '[%s] 17,000 of 55,000 at 5,000/month: 3 of 11 done, 8 months left, ends %s (%s)' % (theme or 'auto', exp_end, I))
        tx = pg.inner_text('#view')
        ok('Target' in tx and '55,000' in tx and '31%' in tx and '8 months left' in tx, '[%s] card shows target, 31%%, 8 months left' % (theme or 'auto'))
        w = pg.evaluate("() => $('.gbar i').style.width")
        ok(w.startswith('30.9'), '[%s] progress bar at 30.9%% (%s)' % (theme or 'auto', w))
        ok(overflow(pg) == [], '[%s %.2f] goals fit 360px %s' % (theme or 'auto', scale, overflow(pg)))
        pg.locator('.gcard').first.scroll_into_view_if_needed(); pg.screenshot(path=OUT + '5_goal_%s.png' % (theme or 'auto'))
        ctx.close()
    ctx, pg, errs = open_app(br)
    pg.evaluate("() => { commit([cfgOp('goalplan', {G1: 5000})]); U.pseg = 'goals'; setTab('goals'); }"); pg.wait_for_timeout(400)
    pg.click('.gcard [data-act=gAdd]'); pg.wait_for_timeout(400)
    ok(pg.input_value('#gaAmt').replace(',', '') == '3000', 'Add money pre-filled with the rest of this month (3,000) (%s)' % pg.input_value('#gaAmt'))
    pg.once('dialog', lambda d: d.accept()); pg.click('#sheet [data-act=gaSave]'); pg.wait_for_timeout(400)
    I = pg.evaluate("() => goalInstInfo(goalById('G1'))")
    ok(I['mDone'] and I['paid'] == 4 and I['mLeft'] == 7, 'after adding: month done, 4 of 11, 7 left (%s)' % I)
    ok('instalment done' in pg.inner_text('#view'), 'card says this month is done')
    # edit form: instalment field + live hint
    pg.evaluate("() => goalSheet(goalById('G1'))"); pg.wait_for_timeout(400)
    ok(pg.input_value('#gsInst') == '5000', 'edit form shows the instalment')
    pg.fill('#gsInst', '10000'); pg.wait_for_timeout(150)
    h = pg.inner_text('#gsInstHint')
    ok('4 instalments' in h, 'live hint: 35,000 left at 10,000 -> 4 instalments (%s)' % h)
    ok(overflow(pg) == [], 'goal form fits %s' % overflow(pg))
    pg.screenshot(path=OUT + '6_goal_form.png')
    pg.click('#sheet [data-act=gsSave]'); pg.wait_for_timeout(400)
    ok(pg.evaluate("() => S.cfg.goalplan.G1") == 10000, 'instalment saved (Settings → goalplan)')
    pg.evaluate("() => goalSheet(goalById('G1'))"); pg.wait_for_timeout(300); pg.fill('#gsInst', ''); pg.click('#sheet [data-act=gsSave]'); pg.wait_for_timeout(300)
    ok(pg.evaluate("() => 'G1' in S.cfg.goalplan") is False and pg.locator('.ginst').count() == 0, 'clearing it removes the instalment line')
    # new goal with instalment
    pg.evaluate("() => goalSheet(null)"); pg.wait_for_timeout(300)
    pg.fill('#gsName', 'Emergency Fund'); pg.fill('#gsTarget', '120000'); pg.fill('#gsInst', '8000')
    ok('15 instalments' in pg.inner_text('#gsInstHint'), 'new goal hint: 1.2L at 8,000 -> 15 instalments')
    pg.click('#sheet [data-act=gsSave]'); pg.wait_for_timeout(300)
    ok(pg.evaluate("() => S.cfg.goalplan[S.goals.find(g => g.name === 'Emergency Fund').id]") == 8000, 'new goal instalment saved')
    ok(not errs, 'no page errors %s' % errs); ctx.close()
    br.close()

print('FAILED: %d' % len(fails))
for f in fails: print(' - ' + f)
