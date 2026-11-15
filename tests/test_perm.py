import os; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.makedirs(ROOT + '/tests/shots', exist_ok=True)
ROOT = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))); exec(open(ROOT + '/tests/test_v91.py').read().split("with sync_playwright() as p:")[0])
ANDF = r"""
window.__perm = { sms: false, notif: false, battery: false, restricted: true };
window.LedgerAndroid = new Proxy({ info: () => JSON.stringify(Object.assign({ version: '8.0.38-test', code: 38, beta: true, bio: false, smsLast: '' }, __perm)),
  requestSms: () => { setTimeout(() => { if (!__perm.restricted) __perm.sms = true; __perm.notif = true; window.onLedgerPerm && onLedgerPerm(); }, 100); },
  openBattery: () => { setTimeout(() => { __perm.battery = true; document.dispatchEvent(new Event('visibilitychange')); }, 100); },
  takeSms: () => '[]', pendingOpen: () => '0', driveAuth: () => setTimeout(() => window.onDriveToken && onDriveToken('tok'), 30), justUpdated: () => '', takeAction: () => '' }, { get: (t, k) => k in t ? t[k] : () => '' });
"""
with sync_playwright() as p:
    br = p.chromium.launch()
    for scale in (1.0, 1.6):
        tag = ' [text %d%%]' % (scale * 100)
        ctx = br.new_context(viewport=dict(width=360, height=780), device_scale_factor=2, has_touch=True, is_mobile=True); pg = ctx.new_page()
        pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
        pg.add_init_script(FAKE + ANDF + "localStorage.getItem('ledger3') || localStorage.setItem('ledger3', JSON.stringify({theme: 'dark', prefs: {}}));")
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.goto(URL); pg.wait_for_timeout(2500)
        if scale != 1: pg.evaluate("s => document.documentElement.style.fontSize = (16*s) + 'px'", scale)
        pg.click('button[data-act=dSignIn]'); pg.wait_for_function("() => isDrive() && !!document.querySelector('.btile')", timeout=15000)
        ok(True, 'phone app: Sign in with Google → Sheet made → bank picker' + tag)
        pg.click('.btile[data-g=banks][data-k=icici]'); pg.click('#obNextBtn'); pg.wait_for_timeout(400); pg.locator('#obRows .obo').first.fill('5000'); pg.click('button[data-act=obSave]'); pg.wait_for_timeout(1200)
        ok(pg.locator('#obPermBox').count() == 1 and pg.locator('#obPermBox button').count() == 3 and pg.locator('#tour').count() == 0, 'after balances: permissions step with 3 buttons, before the tour' + tag)
        pg.screenshot(path=OUT + 'p1_perms_%d.png' % (scale * 100)); ok(overflow(pg) == [], 'permissions step fits %s' % overflow(pg) + tag)
        pg.locator('#obPermBox button[data-act=obAllow]').first.click(); pg.wait_for_timeout(1900)
        ok(pg.locator('#obPermBox button[data-act=andAppSet]').count() == 1 and pg.locator('#obPermBox b.green').count() == 1, 'Allow tapped but Android blocks SMS (sideloaded): notifications turn on, and the "Allow restricted settings" help appears' + tag)
        pg.screenshot(path=OUT + 'p2_perms_blocked_%d.png' % (scale * 100)); ok(overflow(pg) == [], 'fits with the help text %s' % overflow(pg) + tag)
        pg.evaluate("() => { __perm.restricted = false; }"); pg.locator('#obPermBox button[data-act=obAllow]').first.click(); pg.wait_for_timeout(1900)
        pg.click('#obPermBox button[data-act=obBattery]'); pg.wait_for_timeout(700)
        ok(pg.locator('#obPermBox b.green').count() == 3 and pg.inner_text('button[data-act=obPermDone]') == 'All set · continue', 'after allowing: all three show ✓ On' + tag)
        pg.click('button[data-act=obPermDone]'); pg.wait_for_timeout(900)
        ok(pg.locator('#tour').count() == 1, 'Continue → the quick tour starts' + tag); pg.click('.tr-skip'); pg.wait_for_timeout(500)
        # Google sign-in mode never offers Sheet-script-only things
        pg.evaluate("() => setTab('settings')"); pg.wait_for_timeout(300)
        ok(pg.locator('button[data-act=spOpen][data-k=reports]').count() == 0, 'Settings no longer shows "Email reports" with Google sign-in' + tag)
        pg.evaluate("() => { U.sp = 'sync'; render(); }"); pg.wait_for_timeout(300); pg.screenshot(path=OUT + 'p3_drive_card_%d.png' % (scale * 100)); ok(overflow(pg) == [], 'Google Drive page fits %s' % overflow(pg) + tag)
        c = pg.evaluate(COUNT); ok(c and c['Accounts'] == 2, 'the Sheet in Drive has the accounts (%s)' % {k: v for k, v in (c or {}).items() if v} + tag)
        ok(not errs, 'no page errors %s' % errs + tag); ctx.close()
    br.close()
print('\nFAILED: %d' % len(fails)); [print(' -', f) for f in fails]
