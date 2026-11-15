import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(ROOT + '/tests/shots', exist_ok=True)
import json, sys
from playwright.sync_api import sync_playwright
URL = 'file://' + ROOT + '/index.html'
OUT = ROOT + '/tests/shots/'
SCRIPT = 'https://script.google.com/macros/s/FAKE/exec'
fails = []
def ok(c, msg):
    print(('PASS ' if c else 'FAIL ') + msg)
    if not c: fails.append(msg)

FAKE = r"""
window.Chart = function(){ return {destroy(){}, update(){}} }; window.Chart.register = () => {}; window.Chart.defaults = {font:{}, plugins:{legend:{labels:{}}, tooltip:{}}, color:''};
window.G = { files: {}, n: 0, log: [], failWrite: false, scriptOps: [], script: null };
window.google = { accounts: { id: {}, oauth2: { initTokenClient: cfg => ({ callback: null, requestAccessToken() { setTimeout(() => this.callback({ access_token: 'tok' }), 20); } }), revoke() {} } } };
(() => {
  const J = (o, st) => new Response(JSON.stringify(o), { status: st || 200, headers: { 'Content-Type': 'application/json' } });
  const trim = rows => { const r = rows.map(x => x.slice()); while (r.length && r[r.length - 1].every(c => c === '' || c == null)) r.pop(); return r; };
  const real = window.fetch;
  window.fetch = async (url, opt) => {
    url = String(url); opt = opt || {}; const m = (opt.method || 'GET').toUpperCase(), body = opt.body ? JSON.parse(opt.body) : null; G.log.push(m + ' ' + url.slice(0, 90));
    if (url.startsWith('""" + SCRIPT + r"""')) { if (m === 'GET') return J(G.script); if (body.ops) G.scriptOps.push(...body.ops); return J({ ok: true }); }
    if (url.includes('oauth2/v3/userinfo')) return J({ email: 'sunny@gmail.com', name: 'Sunny', given_name: 'Sunny' });
    let mm;
    if (url.startsWith('https://www.googleapis.com/drive/v3/files')) {
      const u = new URL(url), path = u.pathname.replace('/drive/v3/files', '');
      if (path === '' && m === 'GET') { const q = u.searchParams.get('q') || ''; const k = (q.match(/key='(\w+)' and value='(\w+)'/) || []); const folder = /folder/.test(q), sheet = /spreadsheet/.test(q);
        const L = Object.values(G.files).filter(f => !f.trashed && (f.appProperties || {})[k[1]] === k[2] && (!folder || f.folder) && (!sheet || !f.folder)).sort((a, b) => b.t - a.t);
        return J({ files: L.map(f => ({ id: f.id, name: f.name, createdTime: f.t, modifiedTime: f.t, appProperties: f.appProperties })) }); }
      if (path === '' && m === 'POST') { const id = 'F' + (++G.n); G.files[id] = { id, name: body.name, folder: true, appProperties: body.appProperties || {}, t: ++G.n }; return J({ id }); }
      if ((mm = path.match(/^\/(\w+)\/copy$/))) { const src = G.files[mm[1]]; if (!src) return J({ error: { message: 'File not found' } }, 404); const id = 'F' + (++G.n); G.files[id] = { id, name: body.name, parents: body.parents, appProperties: Object.assign({}, src.appProperties, body.appProperties), tabs: JSON.parse(JSON.stringify(src.tabs)), t: ++G.n }; return J({ id }); }
      if ((mm = path.match(/^\/(\w+)$/)) && m === 'PATCH') { const f = G.files[mm[1]]; if (!f) return J({ error: { message: 'File not found' } }, 404); if (body.name) f.name = body.name; if (body.trashed) f.trashed = true; if (body.appProperties) Object.assign(f.appProperties, body.appProperties); if (body.description) f.description = body.description; return J({ id: f.id }); }
    }
    if (url.startsWith('https://sheets.googleapis.com/v4/spreadsheets')) {
      const u = new URL(url), path = u.pathname.replace('/v4/spreadsheets', '');
      if (path === '' && m === 'POST') { if (body.properties.locale === 'en_IN') return J({ error: { message: 'Invalid properties: Unsupported locale: en_IN' } }, 400); if (G.noTz && body.properties.timeZone) return J({ error: { message: 'Invalid properties: Unsupported time zone' } }, 400); const id = 'S' + (++G.n); const tabs = {}; body.sheets.forEach(x => tabs[x.properties.title] = []); G.files[id] = { id, name: body.properties.title, appProperties: {}, tabs, t: ++G.n }; return J({ spreadsheetId: id }); }
      if ((mm = path.match(/^\/(\w+)$/)) && m === 'GET') return J({ sheets: Object.keys(G.files[mm[1]].tabs).map(t => ({ properties: { title: t } })) });
      if ((mm = path.match(/^\/(\w+):batchUpdate$/))) { body.requests.forEach(r => G.files[mm[1]].tabs[r.addSheet.properties.title] = []); return J({}); }
      if ((mm = path.match(/^\/(\w+)\/values:batchUpdate$/))) { if (G.failWrite) return J({ error: { message: 'Quota exceeded (test)' } }, 429); const f = G.files[mm[1]]; f.t = ++G.n; body.data.forEach(d => { const tab = d.range.split('!')[0]; f.tabs[tab] = f.tabs[tab] || []; d.values.forEach((row, i) => f.tabs[tab][i] = row.slice()); }); return J({}); }
      if ((mm = path.match(/^\/(\w+)\/values:batchGet$/))) { const f = G.files[mm[1]]; if (!f) return J({ error: { message: 'Not found' } }, 404); return J({ valueRanges: u.searchParams.getAll('ranges').map(r => { const [tab, rg] = r.split('!'); let rows = trim(f.tabs[tab] || []); if (/^A2:A$/.test(rg)) rows = rows.slice(1).map(x => [x[0]]).filter(x => x[0] !== '' && x[0] != null); return rows.length ? { range: r, values: rows } : { range: r }; }) }); }
    }
    if (/^https?:/.test(url)) return J({ error: { message: 'blocked in test: ' + url } }, 500);
    return real(url, opt);
  };
})();
"""

def owner_state(linked=True):
    acc = lambda i, n, t, op, **k: dict(id='A%d' % i, name=n, type=t, opening=op, openingDate='2026-10-27 02:45:00', archived=False, order=i, others=False, keptIn='', **k)
    st = dict(accounts=[acc(1, 'ICICI Bank', 'bank', 14062), acc(2, 'Kotak Bank', 'bank', 181), acc(3, 'Cash in hand', 'cash', 25), acc(4, 'ICICI Credit Card', 'card', -729, billDay=28),
                        dict(acc(5, 'Mom', 'bank', 56379), others=True, keptIn='Kotak Bank')],
              exp=[dict(id='E%d' % i, ts='2026-11-%02d 10:00:00' % (1 + i % 10), account='ICICI Bank', amount=100 + i, category='Food & Dining', remarks='Lunch %d' % i, photo='', payee='', mine=False) for i in range(120)],
              inc=[dict(id='I1', ts='2026-10-31 10:00:00', account='ICICI Bank', amount=50000, source='Salary', remarks='Oct', payee='')],
              trf=[dict(id='T1', ts='2026-11-10 22:08:00', **{'from': 'ICICI Bank'}, to='ICICI Credit Card', amount=30, remarks='Card bill')],
              goals=[dict(id='G1', name='Emergency fund', kind='save', target=100000, account='Kotak Bank', icon='🛟', color='#12A150', archived=False, created='2026-10-20 10:00:00', deadline='')],
              rem=[dict(id='R1', name='Rent', kind='bill', amount=9250, account='ICICI Bank', category='Household', invType='', invTo='', every=1, unit='month', next='2026-12-01', time='09:00', auto=False, cal=True, active=True, snooze='', lastDone='', note='', then=0, thenFrom='')],
              theme='dark', prefs={'tour': '2026-11-01'}, srvV=10)
    if linked: st.update(url=SCRIPT, key='SECRET')
    return st
def script_reply(st):
    COLL = {'Expenses': 'exp', 'Income': 'inc', 'Transfers': 'trf', 'Investments': 'inv', 'EMILog': 'emi', 'GoalLog': 'goal', 'LoanLog': 'loan', 'Adjustments': 'adj', 'Accounts': 'accounts', 'Goals': 'goals', 'EMIs': 'emis', 'Loans': 'loans', 'Reminders': 'rem', 'Pending': 'pend', 'Deleted': 'bin'}
    return dict(ok=True, version=10, data={k: st.get(v, []) for k, v in COLL.items()}, config={'report': {'on': True, 'day': 1, 'hour': 9}, 'cards': {'limits': {'ICICI Credit Card': 150000}, 'guide': 30}})

def open_app(br, st, scale=1.0, accept=True):
    ctx = br.new_context(viewport=dict(width=360, height=780), device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
    pg.add_init_script(FAKE + "\nG.script = %s; if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('ledger3', %s); }" % (json.dumps(script_reply(st)), json.dumps(json.dumps(st))))
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    dl = []; pg.on('dialog', lambda d: (dl.append(d.message), d.accept() if accept else d.dismiss()))
    pg.goto(URL); pg.wait_for_timeout(2200)
    if scale != 1.0: pg.evaluate("s => document.documentElement.style.fontSize = (16*s) + 'px'", scale)
    return ctx, pg, errs, dl
def overflow(pg):
    return pg.evaluate("() => { const w = innerWidth; return [...document.querySelectorAll('.sheet.open *, #view *, #tour *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > w + 1 && !e.closest('.chips:not(.wrap), .strip, .seg, .tabs, .wr-track, [style*=overflow]'); }).slice(0, 5).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right)); }")
COUNT = "() => { const f = Object.values(G.files).find(f => !f.trashed && !f.folder && f.appProperties.brokeless === '1'); if (!f) return null; const o = {}; Object.keys(f.tabs).forEach(t => o[t] = f.tabs[t].filter((r, i) => i && r.some(c => c !== '' && c != null)).length); return o; }"

with sync_playwright() as p:
    br = p.chromium.launch()
    # ================= 1. owner: secret key -> Google sign-in =================
    ctx, pg, errs, dl = open_app(br, owner_state())
    ok(pg.evaluate("() => linked() && !isDrive() && S.accounts.length === 5 && S.exp.length === 120"), 'owner starts on the secret key with data loaded')
    pg.evaluate("() => { setTab('settings'); U.sp = 'sync'; render(); }"); pg.wait_for_timeout(300)
    ok(pg.locator('button[data-act=dSwitchAsk]').count() == 1, 'Settings → Google Sheet & sync shows "Switch to Google sign-in"')
    pg.screenshot(path=OUT + 's1_sync_page.png')
    pg.click('button[data-act=dSwitchAsk]'); pg.wait_for_timeout(500); pg.screenshot(path=OUT + 's2_switch_ask.png'); ok(overflow(pg) == [], 'switch sheet fits %s' % overflow(pg))
    pg.evaluate("() => document.querySelector('button[data-act=dSwitch]').scrollIntoView()"); pg.click('button[data-act=dSwitch]')
    pg.wait_for_function("() => !U.dSw", timeout=20000); pg.wait_for_timeout(600)
    pg.screenshot(path=OUT + 's3_switch_done.png')
    r = pg.evaluate("() => ({ drive: isDrive(), url: S.url, key: S.key, email: S.drive && S.drive.email, out: S.outbox.length, acc: S.accounts.length, exp: S.exp.length, dBk: S.prefs.dBk === today(), lim: cardLimit(acc('ICICI Credit Card')) })")
    ok(r['drive'] and r['url'] == '' and r['key'] == '' and r['email'] == 'sunny@gmail.com' and r['out'] == 0 and r['acc'] == 5 and r['exp'] == 120, 'after the switch: Google sign-in mode, key gone, all data still on the phone (%s)' % r)
    c = pg.evaluate(COUNT)
    ok(c and c['Expenses'] == 120 and c['Accounts'] == 5 and c['Income'] == 1 and c['Transfers'] == 1 and c['Goals'] == 1 and c['Reminders'] == 1 and c['Settings'] >= 5, 'Drive Sheet has every row (%s)' % {k: v for k, v in (c or {}).items() if v})
    ok(r['lim'] == 150000, 'settings came along too (card limit 1,50,000)')
    so = pg.evaluate("() => G.scriptOps.filter(o => o.op === 'config' && o.key === 'report').map(o => o.value.on)")
    ok(so == [False], 'old Sheet told to stop its email report (%s)' % so)
    b = pg.evaluate("() => Object.values(G.files).filter(f => f.appProperties.brokelessBackup === '1').map(f => [f.name.slice(-6), f.appProperties.brokeless, !!f.parents])")
    ok(len(b) == 1 and b[0][1] == '0' and b[0][2] and r['dBk'], 'first backup copy saved in the "Brokeless backups" folder, and it can never be mistaken for the main Sheet (%s)' % b)
    ok(dl == [], 'no surprise pop-ups during the switch %s' % dl)
    pg.evaluate("() => shut()")
    # a new entry syncs to Drive
    pg.evaluate("() => commit([up('Expenses', { id: 'ENEW', ts: nowTs(), account: 'ICICI Bank', amount: 55, category: 'Food & Dining', remarks: 'Chai', photo: '', payee: '', mine: false })])")
    pg.wait_for_function("() => !S.outbox.length", timeout=10000); pg.wait_for_timeout(300)
    ok(pg.evaluate(COUNT)['Expenses'] == 121, 'a new expense reaches the Drive Sheet')
    # second device: sign in finds the same Sheet
    files = pg.evaluate("() => JSON.stringify(G.files)")
    ctx2 = br.new_context(viewport=dict(width=360, height=780), has_touch=True, is_mobile=True); p2 = ctx2.new_page()
    p2.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
    p2.add_init_script(FAKE + "\nG.files = %s; G.n = 9000;" % files); p2.goto(URL); p2.wait_for_timeout(2500)
    p2.evaluate("() => driveSignIn()"); p2.wait_for_function("() => isDrive() && S.exp.length > 0", timeout=15000)
    r2 = p2.evaluate("() => [S.exp.length, S.accounts.length, Object.values(G.files).filter(f => f.appProperties.brokeless === '1' && !f.folder).length]")
    ok(r2 == [121, 5, 1], 'a second phone that taps "Sign in with Google" gets the same data, no second Sheet made (%s)' % r2); ctx2.close()
    # backups page + restore
    pg.evaluate("() => { setTab('settings'); U.sp = 'backup'; render(); }"); pg.wait_for_timeout(800)
    ok(pg.locator('#bkBox .item').count() == 1, 'Backups page lists the Drive backup')
    pg.screenshot(path=OUT + 's4_backups.png'); ok(overflow(pg) == [], 'backups page fits %s' % overflow(pg))
    pg.click('#bkBox button[data-act=bkPick]'); pg.wait_for_function("() => !S.outbox.length && !S.exp.some(e => e.id === 'ENEW')", timeout=15000); pg.wait_for_timeout(600)
    c = pg.evaluate(COUNT); b = pg.evaluate("() => Object.values(G.files).filter(f => f.appProperties.brokelessBackup === '1' && !f.trashed).map(f => f.appProperties.kind)")
    ok(c['Expenses'] == 120 and pg.evaluate("() => S.exp.length") == 120 and sorted(b) == ['daily', 'safety'], 'Restore: the backup comes back (chai gone, 120 expenses on phone and in Drive) and a safety copy was made first (%s)' % b)
    # daily automatic backup + pruning
    pg.evaluate("() => { S.prefs.dBk = '2026-11-01'; commit([cfgOp('backup', Object.assign({}, S.cfg.backup, { keep: 7 }))]); for (let i = 0; i < 9; i++) { const id = 'OLD' + i; G.files[id] = { id, name: '2026-10-' + (10 + i) + ' 09:00 · Backup', appProperties: { brokeless: '0', brokelessBackup: '1', kind: 'daily' }, tabs: {}, t: i }; } }")
    pg.wait_for_function("() => !S.outbox.length", timeout=10000); pg.wait_for_function("() => S.prefs.dBk === today()", timeout=15000); pg.wait_for_timeout(800)
    b = pg.evaluate("() => Object.values(G.files).filter(f => f.appProperties.brokelessBackup === '1' && f.appProperties.kind === 'daily' && !f.trashed).length")
    ok(b == 7, 'next day: a backup is made by itself after the first sync, and only the last 7 daily copies are kept (%s)' % b)
    ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= 2. an earlier Brokeless Sheet already in the account =================
    ctx, pg, errs, dl = open_app(br, owner_state())
    pg.evaluate("() => { G.files.OLDS = { id: 'OLDS', name: 'Brokeless', appProperties: { brokeless: '1' }, t: 1, tabs: { Accounts: [['Name'], ['Test bank']], Expenses: [['Timestamp'], ['x'], ['y']], Settings: [['Key', 'Value']] } }; }")
    pg.evaluate("() => driveSwitch()"); pg.wait_for_function("() => !U.dSw", timeout=20000); pg.wait_for_timeout(400)
    r = pg.evaluate("() => [isDrive(), G.files.OLDS.name.startsWith('Brokeless (old'), G.files.OLDS.appProperties.brokeless, S.drive.id !== 'OLDS', S.exp.length]")
    ok(r == [True, True, '0', True, 120] and len(dl) == 1 and 'already has a Brokeless Sheet with 3 row' in dl[0], 'an earlier test Sheet in the same Google account is set aside (asked first), never mixed in (%s)' % r)
    ctx.close()
    # ================= 3. something fails half-way =================
    ctx, pg, errs, dl = open_app(br, owner_state())
    pg.evaluate("() => { G.failWrite = true; driveSwitch(); }"); pg.wait_for_function("() => !U.dSw", timeout=20000); pg.wait_for_timeout(400)
    r = pg.evaluate("() => [isDrive(), S.url, S.key, S.exp.length, S.accounts.length, S.outbox.length, Object.values(G.files).filter(f => f.appProperties.brokeless === '1').length]")
    ok(r == [False, SCRIPT, 'SECRET', 120, 5, 0, 0], 'if Google fails half-way: back on the secret key, nothing lost, half-made Sheet set aside (%s)' % r)
    pg.evaluate("() => { G.failWrite = false; driveSwitch(); }"); pg.wait_for_function("() => !U.dSw", timeout=20000)
    ok(pg.evaluate("() => isDrive()") and pg.evaluate(COUNT)['Expenses'] == 120, 'trying again afterwards works'); ok(not errs, 'no page errors %s' % errs); ctx.close()

    # ================= 4. new user: banks picker, balances, tour =================
    for scale, theme in ((1.0, ''), (1.6, 'dark')):
        tag = ' [text %d%%%s]' % (scale * 100, ' dark' if theme else '')
        ctx, pg, errs, dl = open_app(br, dict(theme=theme, prefs={}), scale)
        pg.wait_for_timeout(600)
        ok(pg.evaluate("() => sheetOpen()") and pg.locator('button[data-act=dSignIn]').count() >= 1, 'new user sees Welcome with Sign in with Google' + tag)
        pg.click('button[data-act=wSkip]'); pg.wait_for_timeout(500)
        ok(pg.locator('.btile').count() > 40, 'bank picker opens (%d tiles)' % pg.locator('.btile').count() + tag)
        for g, k in (('banks', 'sbi'), ('banks', 'hdfc'), ('banks', 'canara'), ('cards', 'hdfc'), ('wal', 'paytm')):
            pg.click('.btile[data-g=%s][data-k=%s]' % (g, k))
        pg.wait_for_timeout(200); pg.screenshot(path=OUT + 'o1_banks_%d.png' % (scale * 100)); ok(overflow(pg) == [], 'bank picker fits %s' % overflow(pg) + tag)
        ok(pg.inner_text('#obNextBtn') == 'Next · 5 picked', 'button counts what is picked (%s)' % pg.inner_text('#obNextBtn') + tag)
        tiny = pg.evaluate("() => Math.min(...[...document.querySelectorAll('.btile .bbadge')].map(b => b.scrollWidth <= b.clientWidth + 1 ? 1 : 0))")
        ok(tiny == 1, 'every bank badge fits its initials' + tag)
        pg.click('#obNextBtn'); pg.wait_for_timeout(500)
        names = pg.evaluate("() => [...document.querySelectorAll('#obRows .obr2')].map(r => r.dataset.t + ':' + r.querySelector('.obn').value)")
        ok(names == ['bank:SBI', 'bank:HDFC Bank', 'bank:Canara Bank', 'cash:Cash in hand', 'wallet:Paytm', 'card:HDFC Credit Card'], 'balances step lists what was picked (%s)' % names + tag)
        vals = ['12,000', '34,500.50', '900', '250', '', '4200']
        for i, v in enumerate(vals):
            if v: pg.locator('#obRows .obr2 .obo').nth(i).fill(v)
        pg.locator('#obRows .obr2 .obl').fill('200000')
        pg.screenshot(path=OUT + 'o2_balances_%d.png' % (scale * 100)); ok(overflow(pg) == [], 'balances step fits %s' % overflow(pg) + tag)
        pg.click('button[data-act=obBack]'); pg.wait_for_timeout(300); ok(pg.locator('.btile.on').count() == 5, 'Back keeps the picks' + tag); pg.click('#obNextBtn'); pg.wait_for_timeout(300)
        for i, v in enumerate(vals):
            if v: pg.locator('#obRows .obr2 .obo').nth(i).fill(v)
        pg.locator('#obRows .obr2 .obl').fill('200000')
        pg.click('button[data-act=obSave]'); pg.wait_for_timeout(1300)
        r = pg.evaluate("() => S.accounts.map(a => a.name + '|' + a.type + '|' + C.bal[a.name]).concat([cardLimit(acc('HDFC Credit Card')), !!document.querySelector('#tour')])")
        ok(r == ['SBI|bank|12000', 'HDFC Bank|bank|34500.5', 'Canara Bank|bank|900', 'Cash in hand|cash|250', 'Paytm|wallet|0', 'HDFC Credit Card|card|-4200', 200000, True], 'accounts created with balances, card owes 4,200 with limit 2L, tour opens (%s)' % r + tag)
        pg.screenshot(path=OUT + 't1_tour_%d.png' % (scale * 100)); ok(overflow(pg) == [], 'tour card fits %s' % overflow(pg) + tag)
        fit = pg.evaluate("() => [...document.querySelectorAll('#tour .wr-s')].map(s => s.scrollHeight <= s.clientHeight + 1 || getComputedStyle(s).overflowY === 'auto')")
        ok(all(fit), 'each tour card fits or scrolls' + tag)
        for i in range(4): pg.click('#trNext'); pg.wait_for_timeout(450)
        ok(pg.inner_text('#trNext') == 'Start using Brokeless' and pg.evaluate("() => U.ti") == 4, 'Next walks through all 5 cards' + tag)
        if scale == 1.0: pg.screenshot(path=OUT + 't2_tour_last.png')
        pg.click('#trNext'); pg.wait_for_timeout(500)
        ok(pg.locator('#tour').count() == 0 and pg.evaluate("() => !!S.prefs.tour && !document.documentElement.classList.contains('wr-on')"), 'last button closes the tour and it will not show again' + tag)
        pg.evaluate("() => tourShow()"); pg.wait_for_timeout(300); pg.click('.tr-skip'); pg.wait_for_timeout(500)
        ok(pg.locator('#tour').count() == 0, 'Skip closes the tour from the first card' + tag)
        pg.evaluate("() => tourShow()"); pg.wait_for_timeout(300); pg.go_back(); pg.wait_for_timeout(500)
        ok(pg.locator('#tour').count() == 0 and pg.evaluate("() => S.accounts.length") == 6, 'phone Back button closes the tour (app stays open)' + tag)
        # SMS go to the picked banks
        m = pg.evaluate("() => ['Rs.500.00 debited from your Canara Bank A/c XX4321 on 11-Nov-26 to RAMESH. Avl Bal Rs.400', 'Dear Customer, Rs.250 debited from A/c XX9876 on 11Nov26 to SWIGGY -SBI', 'Rs 999 spent on HDFC Bank Card x1234 at AMAZON on 2026-11-11'].map(t => { const x = parseSms(t, nowTs()); return x ? x.bank + ' -> ' + accForSms(x) : null; })")
        ok(m == ['Canara Bank -> Canara Bank', 'SBI -> SBI', 'HDFC -> HDFC Credit Card'], 'bank SMS land on the accounts you picked (%s)' % m + tag)
        # How it works
        pg.evaluate("() => { setTab('settings'); }"); pg.wait_for_timeout(300)
        ok(pg.locator('button[data-act=spOpen][data-k=help]').count() == 1, 'Settings has "How it works"' + tag)
        pg.click('button[data-act=spOpen][data-k=help]'); pg.wait_for_timeout(400)
        n = pg.locator('details.hlp').count(); pg.locator('details.hlp summary').nth(3).click(); pg.wait_for_timeout(200)
        pg.screenshot(path=OUT + 'h1_help_%d.png' % (scale * 100)); ok(n == 11 and overflow(pg) == [], 'How it works: %d guides, fits %s' % (n, overflow(pg)) + tag)
        pg.locator('details.hlp[open] button[data-act=helpGo]').click(); pg.wait_for_timeout(400)
        ok(pg.evaluate("() => U.tab === 'money' && U.mseg === 'acc'"), 'a guide\'s button jumps to the right screen' + tag)
        pg.evaluate("() => { setTab('settings'); U.sp = 'help'; render(); }"); pg.click('button[data-act=tourOpen]'); pg.wait_for_timeout(400)
        ok(pg.locator('#tour').count() == 1, '"Play the tour" replays it' + tag)
        ok(not errs, 'no page errors %s' % errs + tag); ctx.close()
    br.close()
print('\nFAILED: %d' % len(fails)); [print(' -', f) for f in fails]
