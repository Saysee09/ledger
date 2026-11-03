/**
 * LEDGER v9 — Google Apps Script backend
 * v9: "Recently deleted" tab — deleted entries (with their bank SMS) are kept for 30 days (or what you pick in the app), then removed.
 * v8: one Drive folder "Ledger App" (Backups + Receipts inside), date-first backup names, delete old backups from the app,
 *     payee memory, investment sell / withdraw, money owed to people you hold money for, credit-card bill day.
 * v7: Sign in with Google
 * ------------------------------------------------------------------
 * FIRST TIME
 * 1. Google Sheet → Extensions → Apps Script → delete everything → paste this file → Save.
 * 2. In the toolbar choose function "setup" → Run → allow permissions (Sheets, Drive, Gmail, Calendar).
 *    The execution log shows YOUR SECRET KEY. Copy it.
 * 3. Deploy → New deployment → ⚙ Web app → Execute as: Me · Who has access: Anyone → Deploy.
 *    Copy the Web app URL (ends with /exec).
 * 4. In the Ledger app: paste the URL + secret key.
 *
 * UPGRADING (same sheet) — ALL FOUR STEPS, otherwise the app keeps talking to the old code
 * 1. Paste this file over the old code → Save.
 * 2. Run "setup" once (allow every permission: Calendar for reminders, "connect to an external service" for Google sign-in).
 * 3. Deploy → Manage deployments → ✏ edit → Version: NEW VERSION → Deploy.
 * 4. URL and key stay the same. The app refuses to sync with an older script and tells you.
 *
 * AUTOMATIC
 * - Daily backup of the whole sheet to Drive "Ledger App / Backups", named "2026-10-29 03:11 · Backup" (how many to keep is set in the app).
 * - Restore from any backup (app → Settings → Backup & restore). A safety copy is always made first.
 * - Every hour: bills / SIPs set to auto-log are logged on their due date (even if the app is closed),
 *   reminders are added to your Google Calendar, and the email reports go out on schedule.
 * - Monthly summary email (and optional weekly), compared with the previous period by default.
 * - 2nd of every month: rows older than last year move to an archive file; balances,
 *   goals, loans and EMI counts are carried forward. Sorted bank SMS older than 90 days are cleared.
 * - Bill photos are saved to Drive "Ledger App / Receipts". Old "Ledger Backups" / "Ledger Receipts" folders are moved in automatically.
 *
 * PASTING OLD DATA into Expenses: Timestamp | Payment Method | Amount | Category | Remarks
 * (leave Photo and ID empty). Entries dated before an account's "Balance As Of" never change balances.
 * ------------------------------------------------------------------
 */

var VERSION = 9;
var BIN_DAYS = 30;                  /* default; the app can change it (Settings → Recently deleted) */
var TZ = 'Asia/Kolkata';
var FMT = 'yyyy-MM-dd HH:mm:ss';
var KEEP_BACKUPS = 15;
var ROOT = 'Ledger App';
var FOLDER = 'Backups';            /* inside Ledger App */
var RECEIPTS = 'Receipts';         /* inside Ledger App */
var OLD_FOLDERS = { Backups: 'Ledger Backups', Receipts: 'Ledger Receipts' };
var BK = ' · Backup', SAFE = ' · Safety copy';
var POS = { 'Add': 1, 'Opening': 1, 'Merge In': 1, 'Move In': 1 };
var LOAN_ACC = { Borrow: 1, Receive: 1, Lend: -1, Repay: -1 };
var LOAN_UP = { Borrow: 1, Lend: 1, Opening: 1 };

var SHEETS = {
  Expenses: { cols: [['ts', 'Timestamp'], ['account', 'Payment Method'], ['amount', 'Amount'], ['category', 'Category'], ['remarks', 'Remarks'], ['photo', 'Photo'], ['id', 'ID'], ['payee', 'Payee'], ['mine', 'For Me']] },
  Income: { cols: [['ts', 'Timestamp'], ['account', 'Account'], ['amount', 'Amount'], ['source', 'Source'], ['remarks', 'Remarks'], ['id', 'ID'], ['payee', 'Payee']] },
  Transfers: { cols: [['ts', 'Timestamp'], ['from', 'From'], ['to', 'To'], ['amount', 'Amount'], ['remarks', 'Remarks'], ['id', 'ID']] },
  Investments: { cols: [['ts', 'Timestamp'], ['from', 'Paid From'], ['amount', 'Amount'], ['type', 'Type'], ['name', 'Name'], ['to', 'Invested Into'], ['remarks', 'Remarks'], ['id', 'ID'], ['kind', 'Kind'], ['cost', 'Cost']] },
  EMILog: { title: 'EMI Log', cols: [['ts', 'Timestamp'], ['emi', 'EMI'], ['account', 'Paid From'], ['amount', 'Amount'], ['period', 'For Month'], ['remarks', 'Remarks'], ['emiId', 'EMI ID'], ['id', 'ID']] },
  GoalLog: { title: 'Goal Log', cols: [['ts', 'Timestamp'], ['goal', 'Goal'], ['action', 'Action'], ['amount', 'Amount'], ['account', 'Account'], ['remarks', 'Remarks'], ['goalId', 'Goal ID'], ['ref', 'Ref'], ['id', 'ID']] },
  LoanLog: { title: 'Loan Log', cols: [['ts', 'Timestamp'], ['person', 'Person'], ['action', 'Action'], ['amount', 'Amount'], ['account', 'Account'], ['remarks', 'Remarks'], ['loanId', 'Loan ID'], ['ref', 'Ref'], ['id', 'ID']] },
  Adjustments: { cols: [['ts', 'Timestamp'], ['account', 'Account'], ['amount', 'Amount'], ['remarks', 'Remarks'], ['id', 'ID']] },
  Accounts: { cols: [['name', 'Name'], ['type', 'Type'], ['opening', 'Opening Balance'], ['openingDate', 'Balance As Of'], ['archived', 'Archived'], ['order', 'Order'], ['id', 'ID'], ['others', 'Held For Others'], ['keptIn', 'Kept In'], ['phone', 'WhatsApp'], ['l4', 'SMS Digits'], ['billDay', 'Bill Day']] },
  Goals: { cols: [['name', 'Name'], ['kind', 'Type'], ['target', 'Target'], ['account', 'Account'], ['icon', 'Icon'], ['color', 'Color'], ['archived', 'Archived'], ['created', 'Created'], ['id', 'ID'], ['deadline', 'Reach By']] },
  EMIs: { cols: [['name', 'Name'], ['amount', 'Amount'], ['dueDay', 'Due Day'], ['account', 'Account'], ['startMonth', 'Start Month'], ['total', 'Total EMIs'], ['paidBefore', 'Paid Before'], ['active', 'Active'], ['note', 'Note'], ['id', 'ID']] },
  Loans: { cols: [['name', 'Person'], ['dir', 'Direction'], ['note', 'Note'], ['archived', 'Archived'], ['created', 'Created'], ['id', 'ID'], ['acct', 'Held Account']] },
  Reminders: { cols: [['name', 'Name'], ['kind', 'Kind'], ['amount', 'Amount'], ['account', 'Paid From'], ['category', 'Category'], ['invType', 'Invest Type'], ['invTo', 'Invested Into'], ['every', 'Every'], ['unit', 'Unit'], ['next', 'Next Due'], ['time', 'Time'], ['auto', 'Auto Log'], ['cal', 'Calendar'], ['active', 'Active'], ['snooze', 'Snoozed To'], ['lastDone', 'Last Done'], ['note', 'Note'], ['id', 'ID']] },
  Pending: { title: 'Bank SMS', cols: [['ts', 'Timestamp'], ['amount', 'Amount'], ['dir', 'Direction'], ['payee', 'Payee'], ['bank', 'Bank'], ['l4', 'Digits'], ['account', 'Account'], ['card', 'Card'], ['atm', 'ATM'], ['ref', 'Ref'], ['status', 'Status'], ['done', 'Filed As'], ['raw', 'SMS'], ['id', 'ID']] },
  Deleted: { title: 'Recently deleted', cols: [['ts', 'Deleted At'], ['what', 'What'], ['amount', 'Amount'], ['tab', 'Tab'], ['date', 'Entry Date'], ['sms', 'SMS'], ['data', 'Data'], ['id', 'ID']] }
};
var ORDER = ['Expenses', 'Income', 'Transfers', 'Investments', 'EMILog', 'GoalLog', 'LoanLog', 'Adjustments', 'Accounts', 'Goals', 'EMIs', 'Loans', 'Reminders', 'Pending', 'Deleted'];
var LOGS = ['Expenses', 'Income', 'Transfers', 'Investments', 'EMILog', 'GoalLog', 'LoanLog', 'Adjustments'];
var TS_ROWS = { Pending: 1, Deleted: 1 }; /* non-log tabs whose rows need a timestamp instead of a name */
var NUMS = { amount: 1, opening: 1, target: 1, dueDay: 1, total: 1, paidBefore: 1, order: 1, every: 1, cost: 1, billDay: 1 };
var INTS = { dueDay: 1, total: 1, paidBefore: 1, order: 1, every: 1, billDay: 1 };
var BOOLS = { archived: 1, active: 1, others: 1, auto: 1, cal: 1, card: 1, atm: 1, mine: 1 };
var TSK = { ts: 1, openingDate: 1, created: 1 };
var MONTHK = { period: 1, startMonth: 1 };
var DATEK = { next: 1, snooze: 1, lastDone: 1, deadline: 1 };
var TIMEK = { time: 1 };
var ACCOUNT_COLS = {
  Expenses: ['Payment Method'], Income: ['Account'], Transfers: ['From', 'To'], Investments: ['Paid From', 'Invested Into'],
  EMILog: ['Paid From'], GoalLog: ['Account'], LoanLog: ['Account'], Adjustments: ['Account'], Goals: ['Account'], EMIs: ['Account'], Accounts: ['Kept In'], Loans: ['Held Account'],
  Reminders: ['Paid From', 'Invested Into'], Pending: ['Account']
};
var MIGRATED_ = false, CHECKED_ = {};

/* ---------------- menu & setup ---------------- */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('Ledger')
    .addItem('Show secret key', 'showKey')
    .addItem('Backup now', 'backupNow')
    .addItem('Tidy Drive folders now', 'tidyDrive')
    .addItem("Email last month's report now", 'monthlyReport')
    .addItem("Email last week's report now", 'weeklyReport')
    .addItem('Log due bills & sync Calendar now', 'reminderTick')
    .addItem('Archive old years now', 'archiveMenu')
    .addSeparator()
    .addItem('Re-run setup', 'setup')
    .addToUi();
}

function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.setSpreadsheetTimeZone(TZ);
  try { ss.setSpreadsheetLocale('en_IN'); } catch (e) { }
  ORDER.forEach(function (k) { sheet_(ss, k); });
  settings_(ss);
  var s1 = ss.getSheetByName('Sheet1');
  if (s1 && s1.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(s1);
  var p = PropertiesService.getScriptProperties();
  if (!p.getProperty('API_KEY')) p.setProperty('API_KEY', Utilities.getUuid().replace(/-/g, '').slice(0, 20));
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (['dailyBackup', 'yearlyArchive', 'monthlyReport', 'reportTick', 'hourly'].indexOf(t.getHandlerFunction()) >= 0) ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('dailyBackup').timeBased().everyDays(1).atHour(3).inTimezone(TZ).create();
  ScriptApp.newTrigger('yearlyArchive').timeBased().onMonthDay(2).atHour(4).inTimezone(TZ).create();
  ScriptApp.newTrigger('hourly').timeBased().everyHours(1).inTimezone(TZ).create();
  tidyDrive();
  try { CalendarApp.getDefaultCalendar(); } catch (e) { Logger.log('Calendar permission not granted: ' + e); }
  try { UrlFetchApp.getRequest('https://oauth2.googleapis.com/tokeninfo'); } catch (e) { } /* asks for the "connect to an external service" permission used by Google sign-in */
  Logger.log('Ledger script v' + VERSION + ' is set up. NOW: Deploy → Manage deployments → ✏ → Version: New version → Deploy.');
  showKey();
}

function showKey() {
  var k = PropertiesService.getScriptProperties().getProperty('API_KEY');
  Logger.log('YOUR SECRET KEY: ' + k);
  try { SpreadsheetApp.getUi().alert('Ledger secret key', k + '\n\nPaste this in the app → Settings → Google Sheet → Secret key.\n\nAfter pasting new code: Deploy → Manage deployments → ✏ → Version: New version → Deploy.', SpreadsheetApp.getUi().ButtonSet.OK); } catch (e) { }
  return k;
}

/* every hour: bills first (so reports include them), then calendar, then reports */
function hourly() {
  try { reminderTick(); } catch (e) { Logger.log('reminders: ' + e); }
  reportTick();
}

/* ---------------- sheet helpers ---------------- */
function title_(k) { return SHEETS[k].title || k; }
function colsOf_(k) { return SHEETS[k].cols; }
function keyOf_(k, label) {
  var c = colsOf_(k);
  for (var i = 0; i < c.length; i++) if (c[i][1] === label) return c[i][0];
  return null;
}
function p2_(n) { return (n < 10 ? '0' : '') + n; }

function sheet_(ss, k) {
  var sh = ss.getSheetByName(title_(k));
  if (!sh) {
    sh = ss.insertSheet(title_(k));
    var head = colsOf_(k).map(function (c) { return c[1]; });
    sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground('#ECECFF');
    sh.setFrozenRows(1);
    format_(sh, k);
  } else {
    if (k === 'Expenses' && !MIGRATED_) migrateExpenses_(sh);
    if (!CHECKED_[k]) addMissingCols_(sh, k);
  }
  if (k === 'Expenses') MIGRATED_ = true;
  CHECKED_[k] = true;
  return sh;
}

/* Adds any new columns (from app upgrades) to the end of an existing sheet. */
function addMissingCols_(sh, k) {
  var lc = sh.getLastColumn(); if (lc < 1) return;
  var head = sh.getRange(1, 1, 1, lc).getValues()[0].map(function (h) { return String(h).trim(); }), add = [];
  colsOf_(k).forEach(function (c) { if (head.indexOf(c[1]) < 0) add.push(c); });
  add.forEach(function (c, i) {
    var col = lc + i + 1;
    if (col > sh.getMaxColumns()) sh.insertColumnsAfter(sh.getMaxColumns(), col - sh.getMaxColumns());
    sh.getRange(1, col).setValue(c[1]).setFontWeight('bold').setBackground('#ECECFF');
    var rows = sh.getMaxRows() - 1;
    if (rows > 0) sh.getRange(2, col, rows, 1).setNumberFormat(BOOLS[c[0]] ? 'General' : NUMS[c[0]] ? (INTS[c[0]] ? '0' : '#,##0.00') : '@');
  });
}

function format_(sh, k) {
  var lc = sh.getLastColumn(), rows = sh.getMaxRows() - 1;
  if (rows < 1 || lc < 1) return;
  var head = sh.getRange(1, 1, 1, lc).getValues()[0];
  head.forEach(function (h, i) {
    var key = keyOf_(k, String(h)), r = sh.getRange(2, i + 1, rows, 1);
    if (key && TSK[key]) r.setNumberFormat('dd mmm yyyy, h:mm am/pm');
    else if (key && INTS[key]) r.setNumberFormat('0');
    else if (key && NUMS[key]) r.setNumberFormat('#,##0.00');
    else if (key && BOOLS[key]) r.setNumberFormat('General');
    else r.setNumberFormat('@');
  });
}

/* Converts the v3 layout (one column per category) to a single Category column. */
function migrateExpenses_(sh) {
  var lc = sh.getLastColumn(); if (lc < 1) return;
  var head = sh.getRange(1, 1, 1, lc).getValues()[0].map(String);
  if (head.indexOf('Category') >= 0) return;
  var a = head.indexOf('Amount'), r = head.indexOf('Remarks');
  if (a < 0 || r < 0) return;
  var cats = []; for (var i = a + 1; i < r; i++) if (head[i].trim()) cats.push([head[i], i]);
  var H = {}; head.forEach(function (h, i) { H[h] = i; });
  var last = sh.getLastRow(), out = [];
  if (last > 1) {
    sh.getRange(2, 1, last - 1, lc).getValues().forEach(function (row) {
      if (row.every(function (v) { return v === '' || v === null; })) return;
      var amt = Number(row[H['Amount']]) || 0, cat = '', rem = String(row[H['Remarks']] == null ? '' : row[H['Remarks']]);
      for (var j = 0; j < cats.length; j++) {
        var v = row[cats[j][1]];
        if (v !== '' && v !== null) {
          cat = cats[j][0];
          if (typeof v === 'number' || (!isNaN(Number(v)) && String(v).trim() !== '')) { if (!amt) amt = Number(v); }
          else { var t = String(v).trim(); if (t && t.toLowerCase() !== cat.toLowerCase()) rem = rem ? t + ' · ' + rem : t; }
          break;
        }
      }
      out.push([row[H['Timestamp']], row[H['Payment Method']], amt, cat || 'Miscellaneous', rem, '', H['ID'] !== undefined ? row[H['ID']] : '']);
    });
  }
  sh.clear();
  var nh = colsOf_('Expenses').map(function (c) { return c[1]; });
  sh.getRange(1, 1, 1, nh.length).setValues([nh]).setFontWeight('bold').setBackground('#ECECFF');
  sh.setFrozenRows(1);
  format_(sh, 'Expenses');
  if (out.length) sh.getRange(2, 1, out.length, nh.length).setValues(out);
}

function settings_(ss) {
  var sh = ss.getSheetByName('Settings');
  if (!sh) {
    sh = ss.insertSheet('Settings');
    sh.getRange(1, 1, 1, 2).setValues([['Key', 'Value (managed by app)']]).setFontWeight('bold').setBackground('#ECECFF');
    sh.setFrozenRows(1);
  }
  return sh;
}
function readConfig_(ss) {
  var vals = settings_(ss).getDataRange().getValues(), out = {};
  for (var i = 1; i < vals.length; i++) { try { out[String(vals[i][0])] = JSON.parse(vals[i][1]); } catch (e) { } }
  return out;
}
function setConfig_(ss, key, value) {
  var sh = settings_(ss), s = JSON.stringify(value);
  if (s.length > 49000) throw new Error('Setting "' + key + '" is too large');
  var vals = sh.getDataRange().getValues();
  for (var i = 1; i < vals.length; i++) { if (String(vals[i][0]) === key) { sh.getRange(i + 1, 2).setNumberFormat('@').setValue(s); return; } }
  sh.appendRow([key, s]);
}

function normTs_(s) {
  s = String(s || '').trim();
  if (!s) return '';
  var m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
  if (m) return m[1] + '-' + m[2] + '-' + m[3] + ' ' + p2_(+(m[4] || 0)) + ':' + (m[5] || '00') + ':' + (m[6] || '00');
  m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})(?:[ ,]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
  if (m) return m[3] + '-' + p2_(+m[2]) + '-' + p2_(+m[1]) + ' ' + p2_(+(m[4] || 0)) + ':' + (m[5] || '00') + ':' + (m[6] || '00');
  return s;
}
function val_(v, key) {
  if (TSK[key]) return v instanceof Date ? Utilities.formatDate(v, TZ, FMT) : normTs_(v);
  if (MONTHK[key]) return v instanceof Date ? Utilities.formatDate(v, TZ, 'yyyy-MM') : String(v == null ? '' : v).trim();
  if (DATEK[key]) return v instanceof Date ? Utilities.formatDate(v, TZ, 'yyyy-MM-dd') : normTs_(v).slice(0, 10);
  if (TIMEK[key]) return v instanceof Date ? Utilities.formatDate(v, TZ, 'HH:mm') : String(v == null ? '' : v).trim();
  if (NUMS[key]) return (v === '' || v === null) ? 0 : (Number(v) || 0);
  if (BOOLS[key]) { var s = String(v).trim().toUpperCase(); return v === true || s === 'TRUE' || s === 'YES' || s === 'Y' || s === '1'; }
  if (v instanceof Date) return Utilities.formatDate(v, TZ, FMT);
  return v === null || v === undefined ? '' : String(v);
}
function w_(key, v) {
  if (v === undefined || v === null) return '';
  if (TSK[key] && v) { try { return Utilities.parseDate(normTs_(v), TZ, FMT); } catch (e) { return String(v); } }
  if (BOOLS[key]) return !!v;
  return v;
}

/* ---------------- read ---------------- */
function headMap_(sh, lc) {
  var head = sh.getRange(1, 1, 1, lc).getValues()[0].map(function (h) { return String(h).trim(); }), H = {};
  head.forEach(function (h, i) { if (h && !(h in H)) H[h] = i; });
  return { head: head, H: H };
}
function read_(ss, k) {
  var sh = sheet_(ss, k), last = sh.getLastRow(), lc = sh.getLastColumn();
  if (last < 2) return [];
  var hm = headMap_(sh, lc), H = hm.H;
  var vals = sh.getRange(2, 1, last - 1, lc).getValues(), cols = colsOf_(k), out = [], fix = [];
  var isLog = LOGS.indexOf(k) >= 0 || TS_ROWS[k];
  vals.forEach(function (r, ri) {
    if (r.every(function (v) { return v === '' || v === null; })) return;
    var o = {};
    cols.forEach(function (c) { var i = H[c[1]]; o[c[0]] = val_(i === undefined ? '' : r[i], c[0]); });
    if (isLog && !o.ts) return;
    if (!isLog && !o.name) return;
    if (k === 'Expenses' && !o.category) o.category = 'Miscellaneous';
    if (k === 'Reminders' && !o.unit) o.unit = 'month';
    if (!o.id) { o.id = 'X' + Utilities.getUuid().replace(/-/g, '').slice(0, 12); fix.push([ri + 2, o.id]); }
    out.push(o);
  });
  /* IDs for hand-pasted rows: only written while holding the lock, re-checked so no row gets the wrong ID */
  if (fix.length && H['ID'] !== undefined) {
    var lock = LockService.getScriptLock();
    if (lock.tryLock(10000)) {
      try {
        fix.forEach(function (f) { var c = sh.getRange(f[0], H['ID'] + 1); if (c.getValue() === '') c.setValue(f[1]); });
      } finally { lock.releaseLock(); }
    }
  }
  return out;
}

/* ---------------- write ---------------- */
function ctx_(ss, k, cache) {
  if (cache[k]) return cache[k];
  var sh = sheet_(ss, k), lc = sh.getLastColumn(), hm = headMap_(sh, lc), H = {};
  Object.keys(hm.H).forEach(function (h) { H[h] = hm.H[h] + 1; });
  var map = {}, last = sh.getLastRow();
  if (last > 1 && H['ID']) {
    var ids = sh.getRange(2, H['ID'], last - 1, 1).getValues();
    for (var i = 0; i < ids.length; i++) if (ids[i][0] !== '') map[String(ids[i][0])] = i + 2;
  }
  cache[k] = { sh: sh, H: H, head: hm.head, map: map, lc: lc };
  return cache[k];
}
function upsert_(ss, k, row, cache) {
  if (!row || !row.id) throw new Error('Row without id');
  var c = ctx_(ss, k, cache), lc = c.lc, r = c.map[String(row.id)], vals, missing = [];
  if (r) vals = c.sh.getRange(r, 1, 1, lc).getValues()[0];
  else { vals = []; for (var i = 0; i < lc; i++) vals.push(''); }
  colsOf_(k).forEach(function (cd) { var i = c.H[cd[1]]; if (i) vals[i - 1] = w_(cd[0], row[cd[0]]); else missing.push(cd[1]); });
  if (missing.length) throw new Error(title_(k) + ' tab is missing column(s): ' + missing.join(', ') + '. Run setup once.');
  if (r) c.sh.getRange(r, 1, 1, lc).setValues([vals]);
  else { var nr = c.sh.getLastRow() + 1; c.sh.getRange(nr, 1, 1, lc).setValues([vals]); c.map[String(row.id)] = nr; }
}
function delete_(ss, k, id, cache) {
  var c = ctx_(ss, k, cache), r = c.map[String(id)];
  if (r) { c.sh.deleteRow(r); delete cache[k]; }
}
function replaceIn_(ss, k, labels, from, to, cache) {
  var sh = sheet_(ss, k), last = sh.getLastRow(), lc = sh.getLastColumn();
  if (last < 2) return;
  var head = headMap_(sh, lc).head;
  labels.forEach(function (label) {
    var col = head.indexOf(label) + 1;
    if (col > 0) sh.getRange(2, col, last - 1, 1).createTextFinder(from).matchCase(true).matchEntireCell(true).replaceAllWith(to);
  });
  delete cache[k];
}
function renameAccount_(ss, from, to, cache) {
  if (!from || !to || from === to) return;
  Object.keys(ACCOUNT_COLS).forEach(function (k) { replaceIn_(ss, k, ACCOUNT_COLS[k], from, to, cache); });
  /* the "last matched with bank" date is stored by account name */
  var cfg = readConfig_(ss);
  if (cfg.matched && cfg.matched[from]) { cfg.matched[to] = cfg.matched[from]; delete cfg.matched[from]; setConfig_(ss, 'matched', cfg.matched); }
}
function renameCategory_(ss, from, to, cache) {
  if (!from || !to || from === to) return;
  replaceIn_(ss, 'Expenses', ['Category'], from, to, cache);
  replaceIn_(ss, 'Reminders', ['Category'], from, to, cache);
}

/* ---------------- photos ---------------- */
/* Ledger App (in My Drive) → Backups, Receipts. Folder IDs are remembered, so renaming or moving them in Drive is fine. */
function rootFolder_() {
  var p = PropertiesService.getScriptProperties(), id = p.getProperty('ROOT_ID');
  if (id) { try { var f = DriveApp.getFolderById(id); if (!f.isTrashed()) return f; } catch (e) { } }
  var it = DriveApp.getRootFolder().getFoldersByName(ROOT), r = it.hasNext() ? it.next() : DriveApp.createFolder(ROOT);
  p.setProperty('ROOT_ID', r.getId());
  return r;
}
function folderNamed_(name) {
  var p = PropertiesService.getScriptProperties(), key = 'DIR_' + name, id = p.getProperty(key);
  if (id) { try { var f = DriveApp.getFolderById(id); if (!f.isTrashed()) return f; } catch (e) { } }
  var root = rootFolder_(), it = root.getFoldersByName(name), dir;
  if (it.hasNext()) dir = it.next();
  else {
    var old = OLD_FOLDERS[name] ? DriveApp.getFoldersByName(OLD_FOLDERS[name]) : null;
    if (old && old.hasNext()) { dir = old.next(); dir.moveTo(root); dir.setName(name); }
    else dir = root.createFolder(name);
  }
  p.setProperty(key, dir.getId());
  return dir;
}
/* moves the old top-level folders into Ledger App and renames old backups to "yyyy-MM-dd HH:mm · Backup" */
function tidyDrive() {
  var b = folderNamed_(FOLDER); folderNamed_(RECEIPTS);
  ['Ledger Backups', 'Ledger Receipts'].forEach(function (n) {   /* a second copy of an old folder: move its files in */
    var it = DriveApp.getFoldersByName(n);
    while (it.hasNext()) {
      var f = it.next(), to = n === 'Ledger Backups' ? b : folderNamed_(RECEIPTS), fi = f.getFiles();
      while (fi.hasNext()) fi.next().moveTo(to);
      if (!f.getFiles().hasNext() && !f.getFolders().hasNext()) f.setTrashed(true);
    }
  });
  var fs = b.getFiles(), n2 = 0;
  while (fs.hasNext()) {
    var x = fs.next(), m = x.getName().match(/^Ledger (backup|safety) (\d{4}-\d{2}-\d{2} \d{2}:\d{2})$/);
    if (m) { x.setName(m[2] + (m[1] === 'backup' ? BK : SAFE)); n2++; }
  }
  return n2;
}
function upload_(body) {
  if (!body.data) throw new Error('No image');
  var name = String(body.name || ('bill_' + Utilities.formatDate(new Date(), TZ, 'yyyyMMdd_HHmmss') + '.jpg'));
  var blob = Utilities.newBlob(Utilities.base64Decode(body.data), 'image/jpeg', name);
  var file = folderNamed_(RECEIPTS).createFile(blob);
  return file.getUrl();
}

/* ---------------- web app ---------------- */
function json_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function auth_(key) {
  var k = PropertiesService.getScriptProperties().getProperty('API_KEY');
  if (!k) throw new Error('Run setup() in Apps Script first');
  if (String(key || '') !== k) throw new Error('Wrong secret key');
}

function doGet(e) {
  try {
    auth_(e && e.parameter && e.parameter.key);
    var ss = SpreadsheetApp.getActiveSpreadsheet(), data = {};
    ORDER.forEach(function (k) { data[k] = read_(ss, k); });
    return json_({ ok: true, version: VERSION, data: data, config: readConfig_(ss), serverTime: Utilities.formatDate(new Date(), TZ, FMT) });
  } catch (err) {
    return json_({ ok: false, error: String(err.message || err) });
  }
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    var body = JSON.parse(e.postData.contents);
    if (body.action === 'gsignin') return json_(gsignin_(String(body.idToken || '')));
    auth_(body.key);
    if (body.action === 'upload') return json_({ ok: true, url: upload_(body) });
    if (body.action === 'report') {
      if (body.from && body.to) return json_({ ok: true, sentTo: sendReport_(rangeFromBody_(body)) });
      return json_({ ok: true, sentTo: monthlyReport(body.month) });
    }
    if (body.action === 'backup') { lock.waitLock(30000); var f = makeBackup_(body.safety ? SAFE : BK); return json_({ ok: true, name: f.getName(), id: f.getId() }); }
    if (body.action === 'backups') { try { tidyDrive(); } catch (e) { } return json_({ ok: true, list: listBackups_(), keep: keepCount_(), folder: ROOT + ' / ' + FOLDER }); }
    if (body.action === 'delBackups') return json_(delBackups_(body.ids));
    if (body.action === 'restore') { lock.waitLock(30000); return json_(restore_(String(body.id || ''))); }
    lock.waitLock(30000);
    var ss = SpreadsheetApp.getActiveSpreadsheet(), cache = {}, n = 0, errors = [], remTouched = false;
    (body.ops || []).forEach(function (op) {
      try {
        if (op.op === 'config') setConfig_(ss, op.key, op.value);
        else if (op.op === 'renameAccount') renameAccount_(ss, op.from, op.to, cache);
        else if (op.op === 'renameCategory') renameCategory_(ss, op.from, op.to, cache);
        else if (op.op === 'addCategory') { /* nothing to do */ }
        else {
          if (!SHEETS[op.sheet]) throw new Error('Unknown sheet ' + op.sheet);
          if (op.op === 'upsert') upsert_(ss, op.sheet, op.row, cache);
          else if (op.op === 'delete') delete_(ss, op.sheet, op.id, cache);
          else throw new Error('Unknown op ' + op.op);
          if (op.sheet === 'Reminders') remTouched = true;
        }
        n++;
      } catch (x) { errors.push(String(x.message || x)); }
    });
    SpreadsheetApp.flush();
    if (remTouched) { try { syncCalendar_(ss); } catch (c) { errors.push('Calendar: ' + (c.message || c) + ' (run setup once to allow Calendar)'); } }
    return json_({ ok: true, applied: n, errors: errors });
  } catch (err) {
    return json_({ ok: false, error: String(err.message || err) });
  } finally {
    try { lock.releaseLock(); } catch (e2) { }
  }
}

/* ---------------- Sign in with Google ----------------
 * The app sends a Google ID token. Google checks it; if it belongs to the Sheet owner
 * (or an email added in the app → Settings → Google sign-in) and was made for Ledger's
 * client ID, the app gets the secret key back. Nothing else is shared. */
function gsignin_(tok) {
  if (!tok || tok.length > 4096) return { ok: false, error: 'No Google sign-in' };
  var cfg = readConfig_(SpreadsheetApp.getActiveSpreadsheet()), si = cfg.signin || {};
  var ids = (si.clientIds || []).map(String).filter(Boolean);
  if (!ids.length) return { ok: false, error: 'Google sign-in is not switched on yet. Open Ledger on a connected device once.' };
  var r = UrlFetchApp.fetch('https://oauth2.googleapis.com/tokeninfo?id_token=' + encodeURIComponent(tok), { muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) return { ok: false, error: 'Google could not confirm this sign-in. Try again.' };
  var t = JSON.parse(r.getContentText()), now = Math.floor(Date.now() / 1000);
  if (ids.indexOf(String(t.aud)) < 0) return { ok: false, error: 'This sign-in was not made for Ledger' };
  if (['accounts.google.com', 'https://accounts.google.com'].indexOf(String(t.iss)) < 0 || +t.exp < now) return { ok: false, error: 'Sign-in expired. Try again.' };
  var email = String(t.email || '').toLowerCase();
  if (String(t.email_verified) !== 'true' || !email) return { ok: false, error: 'This Google account has no verified email' };
  var owner = String(Session.getEffectiveUser().getEmail() || '').toLowerCase();
  var allowed = [owner].concat((si.emails || []).map(function (x) { return String(x).trim().toLowerCase(); })).filter(Boolean);
  if (allowed.indexOf(email) < 0) return { ok: false, error: email + ' is not allowed to open this Ledger' };
  return { ok: true, key: PropertiesService.getScriptProperties().getProperty('API_KEY'), email: email, owner: owner, version: VERSION };
}

/* ---------------- money maths (same rules as the app) ---------------- */
function effects_(D, add) {
  D.Expenses.forEach(function (e) { add(e.account, -e.amount, e.ts); });
  D.Income.forEach(function (e) { add(e.account, e.amount, e.ts); });
  D.Transfers.forEach(function (e) { add(e.from, -e.amount, e.ts); add(e.to, e.amount, e.ts); });
  D.Investments.forEach(function (e) {
    if (e.kind === 'Sell') { add(e.to, e.amount, e.ts); if (e.from) add(e.from, -(Number(e.cost) || 0), e.ts); return; }   /* sold / withdrawn: bank gets the money, the investment account drops by what was put in */
    add(e.from, -e.amount, e.ts); if (e.to) add(e.to, e.amount, e.ts);
  });
  D.EMILog.forEach(function (e) { add(e.account, -e.amount, e.ts); });
  D.Adjustments.forEach(function (e) { add(e.account, e.amount, e.ts); });
  D.LoanLog.forEach(function (e) { var s = LOAN_ACC[e.action]; if (s) add(e.account, s * e.amount, e.ts); });
}
function balances_(D, accs, until) {
  var bal = {}, start = {};
  accs.forEach(function (a) { bal[a.name] = Number(a.opening) || 0; start[a.name] = a.openingDate || ''; });
  effects_(D, function (acc, amt, ts) { if (acc in bal && ts >= start[acc] && (!until || ts < until)) bal[acc] += amt; });
  return bal;
}
function readAll_(ss) { var D = {}; LOGS.forEach(function (k) { D[k] = read_(ss, k); }); return D; }

/* ---------------- backups & restore ---------------- */
/* suffix = BK or SAFE. Names start with the date so Drive sorts and reads well: "2026-10-29 03:11 · Backup" */
function bkKind_(n) { return n.slice(-BK.length) === BK ? 'backup' : n.slice(-SAFE.length) === SAFE ? 'safety' : /^Ledger backup /.test(n) ? 'backup' : /^Ledger safety /.test(n) ? 'safety' : ''; }
function keepCount_() { var k = +((readConfig_(SpreadsheetApp.getActiveSpreadsheet()).backup || {}).keep); return k >= 3 && k <= 60 ? k : KEEP_BACKUPS; }
function makeBackup_(suffix) {
  if (suffix !== SAFE) suffix = BK;
  var ss = SpreadsheetApp.getActiveSpreadsheet(), f = folderNamed_(FOLDER);
  var file = DriveApp.getFileById(ss.getId()).makeCopy(Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd HH:mm') + suffix, f);
  var keep = function (kind, n) {
    var files = [], it = f.getFiles();
    while (it.hasNext()) { var x = it.next(); if (bkKind_(x.getName()) === kind) files.push(x); }
    files.sort(function (a, b) { return b.getDateCreated() - a.getDateCreated(); });
    files.slice(n).forEach(function (x) { x.setTrashed(true); });
  };
  keep('backup', keepCount_()); keep('safety', 5);
  return file;
}
function dailyBackup() { try { tidyDrive(); } catch (e) { } try { cleanBin_(SpreadsheetApp.getActiveSpreadsheet()); } catch (e) { Logger.log('bin: ' + e); } makeBackup_(BK); }
/* Recently deleted: rows older than the chosen number of days are removed for good */
function binDays_(ss) { var d = +((readConfig_(ss).bin || {}).days); return d >= 1 && d <= 365 ? d : BIN_DAYS; }
function cleanBin_(ss) {
  var sh = sheet_(ss, 'Deleted'), last = sh.getLastRow(), lc = sh.getLastColumn(); if (last < 2) return 0;
  var H = headMap_(sh, lc).H, cut = addDays_(today_(), -binDays_(ss)), vals = sh.getRange(2, 1, last - 1, lc).getValues(), n = 0;
  for (var i = vals.length - 1; i >= 0; i--) {
    var t = vals[i][H['Deleted At']], d = t instanceof Date ? Utilities.formatDate(t, TZ, 'yyyy-MM-dd') : normTs_(t).slice(0, 10);
    if (d && d < cut) { sh.deleteRow(i + 2); n++; }
  }
  return n;
}
function backupNow() {
  var f = makeBackup_(BK);
  try { SpreadsheetApp.getUi().alert('Backup saved in Drive "' + ROOT + ' / ' + FOLDER + '" as "' + f.getName() + '".'); } catch (e) { }
}
function listBackups_() {
  var f = folderNamed_(FOLDER), it = f.getFiles(), out = [];
  while (it.hasNext()) {
    var x = it.next(), n = x.getName(), k = bkKind_(n);
    if (k && x.getMimeType() === MimeType.GOOGLE_SHEETS) out.push({ id: x.getId(), name: n, kind: k, t: x.getDateCreated().getTime() });
  }
  out.sort(function (a, b) { return b.t - a.t; });
  return out.slice(0, 120).map(function (x) { return { id: x.id, name: x.name, kind: x.kind, t: x.t }; });
}
/* moves the chosen backups to Drive's bin (Drive empties the bin after 30 days, or empty it yourself to free space now) */
function delBackups_(ids) {
  var ok = {}; listBackups_().forEach(function (b) { ok[b.id] = 1; });
  var n = 0; (ids || []).forEach(function (id) { if (ok[id]) { DriveApp.getFileById(id).setTrashed(true); n++; } });
  return { ok: true, deleted: n, keep: keepCount_() };
}
/* replaces every Ledger tab with the backup's copy; a safety backup is taken first */
function restore_(id) {
  var ok = listBackups_().some(function (b) { return b.id === id; });
  if (!ok) throw new Error('That backup was not found in "' + ROOT + ' / ' + FOLDER + '"');
  var safety = makeBackup_(SAFE);
  var src = SpreadsheetApp.openById(id), ss = SpreadsheetApp.getActiveSpreadsheet();
  ORDER.map(title_).concat(['Settings']).forEach(function (name) {
    var from = src.getSheetByName(name), to = ss.getSheetByName(name);
    if (!from) return;
    if (!to) to = ss.insertSheet(name);
    to.clearContents();
    var r = from.getLastRow(), c = from.getLastColumn();
    if (r < 1 || c < 1) return;
    if (c > to.getMaxColumns()) to.insertColumnsAfter(to.getMaxColumns(), c - to.getMaxColumns());
    if (r > to.getMaxRows()) to.insertRowsAfter(to.getMaxRows(), r - to.getMaxRows());
    to.getRange(1, 1, r, c).setNumberFormats(from.getRange(1, 1, r, c).getNumberFormats()).setValues(from.getRange(1, 1, r, c).getValues());
  });
  CHECKED_ = {}; MIGRATED_ = false;
  ORDER.forEach(function (k) { sheet_(ss, k); });
  SpreadsheetApp.flush();
  return { ok: true, safety: safety.getName() };
}

/* ---------------- dates (all yyyy-MM-dd strings, India time) ---------------- */
function today_() { return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd'); }
function dObj_(d) { return new Date(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10), 12); }
function dStr_(o) { return o.getFullYear() + '-' + p2_(o.getMonth() + 1) + '-' + p2_(o.getDate()); }
function addDays_(d, n) { var o = dObj_(d); o.setDate(o.getDate() + n); return dStr_(o); }
function dayDiff_(a, b) { return Math.round((dObj_(b) - dObj_(a)) / 864e5); }
function dim_(y, m) { return new Date(y, m + 1, 0).getDate(); } /* m = 0-based */
function shiftD_(d, n) {
  var y = +d.slice(0, 4), m = +d.slice(5, 7) - 1, dd = +d.slice(8, 10), t = new Date(y, m + n, 1, 12);
  var dim = dim_(t.getFullYear(), t.getMonth()), wasEnd = dd === dim_(y, m);
  return t.getFullYear() + '-' + p2_(t.getMonth() + 1) + '-' + p2_(wasEnd ? dim : Math.min(dd, dim));
}
function monday_(d) { var o = dObj_(d); return addDays_(d, -((o.getDay() + 6) % 7)); }
function niceRange_(a, b) {
  var f = function (d, y) { return Utilities.formatDate(dObj_(d), TZ, y ? 'd MMM yyyy' : 'd MMM'); };
  return f(a, a.slice(0, 4) !== b.slice(0, 4)) + ' – ' + f(b, true);
}
function validD_(d) { return typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d); }
/* previous period of equal length (by months when month-based) + same period last year */
function cmpRanges_(r) {
  var t = today_(), end = r.to > t ? t : r.to, prev;
  if (r.mo) prev = { from: shiftD_(r.from, -r.mo), to: shiftD_(end, -r.mo) };
  else { var len = dayDiff_(r.from, end) + 1; prev = { from: addDays_(r.from, -len), to: addDays_(r.from, -1) }; }
  return { end: end, prev: prev, ly: r.mo === 12 ? null : { from: shiftD_(r.from, -12), to: shiftD_(end, -12) } };
}
function rangeFromBody_(b) {
  if (!validD_(b.from) || !validD_(b.to)) throw new Error('Bad report dates');
  var a = b.from, z = b.to; if (a > z) { var x = a; a = z; z = x; }
  return { from: a, to: z, mo: Math.max(0, Math.min(12, +b.mo || 0)), label: String(b.label || niceRange_(a, z)).slice(0, 80), cmp: ['prev', 'ly', 'both'].indexOf(b.cmp) >= 0 ? b.cmp : null };
}

/* ---------------- reminders: auto-log bills / SIPs, Google Calendar ---------------- */
function nextAfter_(d, every, unit) {
  var n = Math.max(1, parseInt(every, 10) || 1);
  if (unit === 'day') return addDays_(d, n);
  if (unit === 'week') return addDays_(d, 7 * n);
  if (unit === 'month') return shiftD_(d, n);
  if (unit === 'year') return shiftD_(d, 12 * n);
  return null;
}
/* Same IDs as the app ("R" + reminder id + "_" + yyyymmdd), so the app and the Sheet never log a bill twice. */
function reminderTick() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return 0;
  var made = 0;
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), t = today_(), cache = {};
    var rems = read_(ss, 'Reminders'), accs = read_(ss, 'Accounts'), have = {};
    if (!rems.length) return 0;
    var accOk = {}; accs.forEach(function (a) { if (!a.archived) accOk[a.name] = 1; });
    var exIds = {}, ivIds = {};
    read_(ss, 'Expenses').forEach(function (e) { exIds[e.id] = 1; });
    read_(ss, 'Investments').forEach(function (e) { ivIds[e.id] = 1; });
    rems.forEach(function (r) {
      if (!r.active || !r.auto || r.kind === 'task' || !r.next || r.next > t || !(r.amount > 0) || !accOk[r.account]) return;
      if (r.kind === 'sip' && r.invTo && !accOk[r.invTo]) return;
      var guard = 0;
      while (r.active && r.next && r.next <= t && guard++ < 36) {
        var id = 'R' + r.id + '_' + r.next.replace(/-/g, ''), ts = r.next + ' ' + (r.time || '09:00') + ':00';
        if (r.kind === 'sip') { if (!ivIds[id]) { upsert_(ss, 'Investments', { id: id, ts: ts, from: r.account, amount: r.amount, type: r.invType || 'Mutual Fund', name: r.name, to: r.invTo || '', remarks: 'SIP · auto-logged' }, cache); made++; } }
        else if (!exIds[id]) { upsert_(ss, 'Expenses', { id: id, ts: ts, account: r.account, amount: r.amount, category: r.category || 'Miscellaneous', remarks: r.name + ' · auto-logged', photo: '' }, cache); made++; }
        var nx = nextAfter_(r.next, r.every, r.unit);
        if (!nx) r.active = false; else r.next = nx;
        r.snooze = ''; r.lastDone = t;
      }
      upsert_(ss, 'Reminders', r, cache);
    });
    SpreadsheetApp.flush();
    try { syncCalendar_(ss); } catch (c) { Logger.log('Calendar: ' + c); }
  } finally { lock.releaseLock(); }
  return made;
}
/* one calendar event per active reminder at its next due date (popup alert at that time). */
function syncCalendar_(ss) {
  var props = PropertiesService.getScriptProperties(), map = {};
  try { map = JSON.parse(props.getProperty('REMCAL') || '{}'); } catch (e) { map = {}; }
  var cal = CalendarApp.getDefaultCalendar(), want = {}, changed = false;
  read_(ss, 'Reminders').forEach(function (r) {
    if (!r.active || !r.cal) return;
    var due = r.snooze && r.snooze > r.next ? r.snooze : r.next; if (!due) return;
    var sig = due + '|' + (r.time || '09:00') + '|' + r.name + '|' + r.amount + '|' + (r.auto ? 1 : 0);
    want[r.id] = sig;
    var cur = map[r.id];
    if (cur && cur.sig === sig) return;
    if (cur && cur.ev) { try { var old = cal.getEventById(cur.ev); if (old) old.deleteEvent(); } catch (e) { } }
    var hm = String(r.time || '09:00').split(':'), start = new Date(+due.slice(0, 4), +due.slice(5, 7) - 1, +due.slice(8, 10), +hm[0] || 9, +hm[1] || 0);
    var amt = r.amount > 0 ? ' · ' + money_(r.amount) : '';
    var title = (r.kind === 'task' ? '✅ ' : r.kind === 'sip' ? '📈 ' : '🧾 ') + r.name + amt;
    var desc = r.kind === 'task' ? 'Ledger reminder. Mark it done in the app → Plan → Reminders.' : (r.auto ? 'Ledger logs this automatically from ' + r.account + '.' : 'Open Ledger → Plan → Reminders → Pay.') + (r.note ? '\n' + r.note : '');
    var ev = cal.createEvent(title, start, new Date(start.getTime() + 15 * 60000), { description: desc });
    ev.removeAllReminders(); ev.addPopupReminder(0); if (r.kind !== 'task') ev.addPopupReminder(24 * 60);
    map[r.id] = { ev: ev.getId(), sig: sig }; changed = true;
  });
  Object.keys(map).forEach(function (id) {
    if (want[id]) return;
    try { var ev = cal.getEventById(map[id].ev); if (ev && ev.getStartTime() > new Date()) ev.deleteEvent(); } catch (e) { }
    delete map[id]; changed = true;
  });
  if (changed) props.setProperty('REMCAL', JSON.stringify(map));
}

/* ---------------- reports ---------------- */
function money_(n) {
  n = Math.round(Number(n) || 0);
  var s = String(Math.abs(n)), last3 = s.slice(-3), rest = s.slice(0, -3);
  if (rest) rest = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',';
  return (n < 0 ? '-' : '') + '₹' + rest + last3;
}
function esc_(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

/* Sends the monthly / weekly reports at the day and hour chosen in the app. */
function reportTick() {
  var ss = SpreadsheetApp.getActiveSpreadsheet(), r = readConfig_(ss).report || { on: true, day: 1, hour: 9 };
  var now = new Date(), ymNow = Utilities.formatDate(now, TZ, 'yyyy-MM'), d = +Utilities.formatDate(now, TZ, 'd'), h = +Utilities.formatDate(now, TZ, 'H');
  var props = PropertiesService.getScriptProperties();
  if (r.on !== false && props.getProperty('REPORT_SENT') !== ymNow) {
    var dim = +Utilities.formatDate(new Date(+ymNow.slice(0, 4), +ymNow.slice(5, 7), 0), TZ, 'd');
    var day = Math.min(Math.max(1, +r.day || 1), dim);
    if (d > day || (d === day && h >= (+r.hour || 0))) { props.setProperty('REPORT_SENT', ymNow); monthlyReport(); }
  }
  var wk = monday_(today_());
  if (!r.weekly) { props.deleteProperty('WEEK_ON'); return; }
  /* just switched on: start from next Monday instead of sending last week's report straight away */
  if (!props.getProperty('WEEK_ON')) { props.setProperty('WEEK_ON', '1'); props.setProperty('WEEK_SENT', wk); return; }
  if (props.getProperty('WEEK_SENT') !== wk && (today_() > wk || h >= (r.wHour == null ? 9 : +r.wHour))) { props.setProperty('WEEK_SENT', wk); weeklyReport(); }
}

/* Last full month (or a given 'yyyy-MM'). */
function monthlyReport(month) {
  var cur = Utilities.formatDate(new Date(), TZ, 'yyyy-MM'), y = +cur.slice(0, 4), mo = +cur.slice(5, 7) - 1;
  if (mo === 0) { y--; mo = 12; }
  var m = (typeof month === 'string' && /^\d{4}-\d{2}$/.test(month)) ? month : y + '-' + p2_(mo);
  y = +m.slice(0, 4); mo = +m.slice(5, 7);
  var label = Utilities.formatDate(Utilities.parseDate(m + '-01 12:00:00', TZ, FMT), TZ, 'MMMM yyyy');
  return sendReport_({ from: m + '-01', to: m + '-' + p2_(dim_(y, mo - 1)), mo: 1, label: label });
}
/* Last Monday–Sunday. */
function weeklyReport() {
  var a = addDays_(monday_(today_()), -7);
  return sendReport_({ from: a, to: addDays_(a, 6), mo: 0, label: 'Week of ' + niceRange_(a, addDays_(a, 6)) });
}

function sendReport_(R) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var D = readAll_(ss), cfg = readConfig_(ss), accs = read_(ss, 'Accounts'), loans = read_(ss, 'Loans');
  var cmp = R.cmp || ((cfg.report || {}).cmp) || 'prev';
  var others = {}; accs.forEach(function (a) { if (a.others) others[a.name] = 1; });
  var F = {
    Expenses: D.Expenses.filter(function (e) { return !others[e.account] || e.mine; }),
    Income: D.Income.filter(function (e) { return !others[e.account]; }),
    EMILog: D.EMILog.filter(function (e) { return !others[e.account]; }),
    Investments: D.Investments.filter(function (e) { return !others[e.from] && e.kind !== 'Sell'; })
  };
  var first = '9999-99-99';
  [D.Expenses, D.Income, D.Transfers, D.Investments, D.EMILog].forEach(function (L) { L.forEach(function (e) { var d = String(e.ts).slice(0, 10); if (d && d < first) first = d; }); });
  var CR = cmpRanges_(R);
  function stats(from, to) {
    var inR = function (e) { var d = String(e.ts).slice(0, 10); return d >= from && d <= to; };
    var tot = function (a) { return a.reduce(function (s, e) { return s + (Number(e.amount) || 0); }, 0); };
    var ex = F.Expenses.filter(inR), spent = tot(ex), income = tot(F.Income.filter(inR)), emi = tot(F.EMILog.filter(inR)), inv = tot(F.Investments.filter(inR));
    var end = to > today_() ? today_() : to, days = from > today_() ? 0 : dayDiff_(from, end) + 1, byCat = {}, dset = {};
    ex.forEach(function (e) { byCat[e.category] = (byCat[e.category] || 0) + e.amount; dset[String(e.ts).slice(0, 10)] = 1; });
    return { ex: ex, spent: spent, income: income, emi: emi, inv: inv, n: ex.length, days: days, avg: days ? spent / days : 0, byCat: byCat,
      rate: income > 0 ? Math.round((income - spent - emi) / income * 100) : null, noSpend: Math.max(0, days - Object.keys(dset).length) };
  }
  var S = stats(R.from, CR.end);
  /* comparison windows: no data before the first record → "no data" instead of a fake 100% */
  var winP = cmp === 'ly' ? (CR.ly || CR.prev) : CR.prev, winL = cmp === 'both' ? CR.ly : null;
  var P = winP.to >= first ? stats(winP.from, winP.to) : null, L = winL && winL.to >= first ? stats(winL.from, winL.to) : null;
  var shortP = cmp === 'ly' ? 'last year' : (R.mo === 1 ? 'last month' : R.mo === 3 ? 'last quarter' : R.mo === 12 ? 'last year' : 'the period before');
  function pct(a, b) { return b > 0 && a != null ? Math.round((a - b) / b * 100) : null; }
  function delta(a, b, good, pts, word) {
    if (a == null || b == null) return '';
    var d = pts ? Math.round(a - b) : pct(a, b); if (d == null) return '';
    var col = !d || !good ? '#6A7085' : ((d > 0) === (good > 0) ? '#12A150' : '#E5484D');
    return '<span style="color:' + col + '">' + (d > 0 ? '▲' : d < 0 ? '▼' : '') + (d ? Math.abs(d) + (pts ? ' pts' : '%') : 'same') + '</span> <span style="color:#6A7085;font-weight:400">vs ' + word + '</span>';
  }
  function dl(k, good, pts) {
    var a = P ? delta(S[k], P[k], good, pts, shortP) : '<span style="color:#6A7085;font-weight:400">no data for ' + shortP + '</span>';
    var b = winL ? (L ? delta(S[k], L[k], good, pts, 'last year') : '<span style="color:#6A7085;font-weight:400">no data last year</span>') : '';
    return (a || b) ? '<div style="font-size:11px;font-weight:700;margin-top:2px">' + a + (a && b ? '<br>' : '') + b + '</div>' : '';
  }
  function card(l, v, c, d) { return '<td style="background:#F4F5FA;border-radius:12px;padding:12px;width:33%;vertical-align:top"><div style="font-size:11px;color:#6A7085;text-transform:uppercase;letter-spacing:.05em">' + l + '</div><div style="font-size:18px;font-weight:800;color:' + (c || '#101322') + '">' + v + '</div>' + (d || '') + '</td>'; }

  var factor = R.mo ? R.mo : Math.max(1, S.days) / 30.44;
  var budgets = {}; (cfg.categories || []).forEach(function (c) { budgets[c.name] = (Number(c.budget) || 0) * factor; });
  var PB = P ? P.byCat : {};
  var cats = Object.keys(S.byCat).concat(Object.keys(PB)).filter(function (c, i, a) { return a.indexOf(c) === i; });
  cats.sort(function (a, b) { return (S.byCat[b] || 0) - (S.byCat[a] || 0); });
  var rows = cats.map(function (c) {
    var v = S.byCat[c] || 0, b = budgets[c] || 0, over = b && v > b, d = P ? delta(v, PB[c] || 0, -1, false, '').replace(/ <span[^>]*>vs <\/span>/, '') : '';
    return '<tr><td style="padding:6px 0">' + esc_(c) + '</td><td style="text-align:right;color:' + (over ? '#E5484D' : '#101322') + '"><b>' + money_(v) + '</b>' + (b ? ' <span style="color:#6A7085">/ ' + money_(b) + '</span>' : '') + '</td><td style="text-align:right;font-size:12px;width:70px">' + (d || (P && !PB[c] ? '<span style="color:#6A7085">new</span>' : '')) + '</td></tr>';
  }).join('');
  var top = S.ex.slice().sort(function (a, b) { return b.amount - a.amount; }).slice(0, 5).map(function (e) {
    return '<tr><td style="padding:4px 0">' + esc_(e.remarks || e.category) + ' <span style="color:#6A7085">· ' + String(e.ts).slice(8, 10) + '/' + String(e.ts).slice(5, 7) + '</span></td><td style="text-align:right">' + money_(e.amount) + '</td></tr>';
  }).join('');
  var tags = {}; S.ex.forEach(function (e) { (String(e.remarks || '').match(/#[\p{L}\p{N}_-]+/gu) || []).forEach(function (t) { t = t.toLowerCase(); tags[t] = (tags[t] || 0) + e.amount; }); });
  var tagRows = Object.keys(tags).sort(function (a, b) { return tags[b] - tags[a]; }).map(function (t) { return '<tr><td style="padding:4px 0">' + esc_(t) + '</td><td style="text-align:right">' + money_(tags[t]) + '</td></tr>'; }).join('');
  var out = {}; D.LoanLog.forEach(function (e) { out[e.loanId] = (out[e.loanId] || 0) + (LOAN_UP[e.action] ? 1 : -1) * e.amount; });
  var owe = 0, owed = 0; loans.forEach(function (l) { var v = Math.max(0, out[l.id] || 0); if (l.dir === 'owe') owe += v; else owed += v; });
  var bal = balances_(D, accs), accRows = accs.filter(function (a) { return !a.archived && !a.others; }).map(function (a) {
    return '<tr><td style="padding:4px 0">' + esc_(a.name) + (a.type === 'card' && bal[a.name] < 0 ? ' <span style="color:#6A7085">(bill to pay)</span>' : '') + '</td><td style="text-align:right">' + money_(bal[a.name]) + '</td></tr>';
  }).join('');
  var nw = 0; accs.forEach(function (a) { if (!a.others) nw += bal[a.name] || 0; }); nw += owed - owe;
  var partial = R.to > today_();
  var cmpNote = (P ? 'Compared with ' + niceRange_(winP.from, winP.to) : 'No records yet for ' + niceRange_(winP.from, winP.to) + ', so no comparison') + (winL ? (L ? ' and ' + niceRange_(winL.from, winL.to) : ' (no data last year)') : '') + (partial ? '. Period not finished yet, so only the same days are compared.' : '.');

  var html = '<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#101322">' +
    '<h2 style="margin:0 0 4px">Ledger · ' + esc_(R.label) + '</h2><div style="color:#6A7085;margin-bottom:4px">' + niceRange_(R.from, CR.end) + ' · ' + S.n + ' expenses logged · ' + S.noSpend + ' no-spend days</div>' +
    '<div style="color:#6A7085;font-size:12px;margin-bottom:12px">' + cmpNote + ' ▼ on spending is good (green), ▲ is more than before (red).</div>' +
    '<table style="width:100%;border-spacing:8px"><tr>' + card('Spent', money_(S.spent), '#E5484D', dl('spent', -1)) + card('Income', money_(S.income), '#12A150', dl('income', 1)) + card('Saved', S.rate == null ? '—' : S.rate + '%', '', dl('rate', 1, true)) + '</tr><tr>' +
    card('EMIs', money_(S.emi), '', dl('emi', 0)) + card('Invested', money_(S.inv), '#2F7BF5', dl('inv', 1)) + card('Avg / day', money_(S.avg), '', dl('avg', -1)) + '</tr></table>' +
    '<h3>By category</h3><table style="width:100%">' + (rows || '<tr><td>No expenses</td></tr>') + '</table>' +
    '<div style="color:#6A7085;font-size:11px">Right column: change vs ' + shortP + '. Budgets scaled to the period length.</div>' +
    '<h3>Biggest expenses</h3><table style="width:100%">' + (top || '<tr><td>—</td></tr>') + '</table>' +
    (tagRows ? '<h3>Tags</h3><table style="width:100%">' + tagRows + '</table>' : '') +
    '<h3>Loans</h3><div>You owe <b>' + money_(owe) + '</b> · Owed to you <b>' + money_(owed) + '</b></div>' +
    '<h3>Balances now</h3><table style="width:100%">' + accRows + '<tr><td style="padding:6px 0;border-top:1px solid #E9EBF2"><b>Net worth</b></td><td style="text-align:right;border-top:1px solid #E9EBF2"><b>' + money_(nw) + '</b></td></tr></table>' +
    '<p style="color:#6A7085;font-size:12px;margin-top:24px">Sent by your Ledger sheet. Held-for-others money is left out. Change the schedule, comparison or email in the app → Settings → Email reports.</p></div>';
  var to = String(((cfg.report || {}).email) || '').trim() || Session.getEffectiveUser().getEmail();
  var pc = P ? pct(S.spent, P.spent) : null;
  MailApp.sendEmail({ to: to, subject: 'Ledger · ' + R.label + ' · Spent ' + money_(S.spent) + (pc == null ? '' : ' (' + (pc === 0 ? 'same as ' : Math.abs(pc) + '% ' + (pc > 0 ? 'more than ' : 'less than ')) + shortP + ')'), htmlBody: html });
  return to;
}

/* ---------------- yearly archive ---------------- */
function yearlyArchive() {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var y = Number(Utilities.formatDate(new Date(), TZ, 'yyyy')), ss = SpreadsheetApp.getActiveSpreadsheet();
    cleanPending_(ss);
    return archiveBefore_(ss, (y - 1) + '-01-01 00:00:00');
  } finally { lock.releaseLock(); }
}
/* sorted or ignored bank SMS older than 90 days are removed (the entries they became stay) */
function cleanPending_(ss) {
  var sh = sheet_(ss, 'Pending'), last = sh.getLastRow(), lc = sh.getLastColumn(); if (last < 2) return;
  var H = headMap_(sh, lc).H, cut = addDays_(today_(), -90), vals = sh.getRange(2, 1, last - 1, lc).getValues();
  for (var i = vals.length - 1; i >= 0; i--) {
    var st = String(vals[i][H['Status']] || ''), t = vals[i][H['Timestamp']], ts = t instanceof Date ? Utilities.formatDate(t, TZ, 'yyyy-MM-dd') : normTs_(t).slice(0, 10);
    if (st && st !== 'new' && ts && ts < cut) sh.deleteRow(i + 2);
  }
}
function archiveMenu() {
  var n = yearlyArchive();
  try { SpreadsheetApp.getUi().alert(n ? n + ' old rows moved to an archive file in "' + ROOT + ' / ' + FOLDER + '".' : 'Nothing old enough to archive yet (current + previous year are kept).'); } catch (e) { }
}
function archiveBefore_(ss, cut) {
  var D = readAll_(ss), old = 0;
  LOGS.forEach(function (k) { D[k].forEach(function (e) { if (e.ts && e.ts < cut) old++; }); });
  if (!old) return 0;
  var accs = read_(ss, 'Accounts'), upto = balances_(D, accs, cut);
  accs.forEach(function (a) { if ((a.openingDate || '') < cut) { a.opening = Math.round(upto[a.name] * 100) / 100; a.openingDate = cut; } });
  var gsum = {}, ginfo = {}, lsum = {}, linfo = {}, ecount = {};
  D.GoalLog.forEach(function (e) { if (e.ts >= cut) return; var gk = e.goalId + '|' + e.account; gsum[gk] = (gsum[gk] || 0) + (POS[e.action] ? 1 : -1) * e.amount; ginfo[gk] = [e.goal, e.account, e.goalId]; });
  D.LoanLog.forEach(function (e) { if (e.ts >= cut) return; lsum[e.loanId] = (lsum[e.loanId] || 0) + (LOAN_UP[e.action] ? 1 : -1) * e.amount; linfo[e.loanId] = e.person; });
  D.EMILog.forEach(function (e) { if (e.ts < cut) ecount[e.emiId] = (ecount[e.emiId] || 0) + 1; });

  var arch = SpreadsheetApp.create(cut.slice(0, 10) + ' · Archive (older rows)');
  DriveApp.getFileById(arch.getId()).moveTo(folderNamed_(FOLDER));
  LOGS.forEach(function (k) {
    var sh = sheet_(ss, k), last = sh.getLastRow(), lc = sh.getLastColumn();
    if (last < 2) return;
    var all = sh.getRange(1, 1, last, lc).getValues(), head = all[0], ti = head.indexOf('Timestamp'), keep = [], gone = [];
    for (var i = 1; i < all.length; i++) {
      var t = all[i][ti], ts = t instanceof Date ? Utilities.formatDate(t, TZ, FMT) : normTs_(t);
      (ts && ts < cut ? gone : keep).push(all[i]);
    }
    if (!gone.length) return;
    var ash = arch.insertSheet(title_(k));
    ash.getRange(1, 1, 1, lc).setValues([head]).setFontWeight('bold');
    ash.getRange(2, 1, gone.length, lc).setValues(gone);
    sh.getRange(2, 1, last - 1, lc).clearContent();
    if (keep.length) sh.getRange(2, 1, keep.length, lc).setValues(keep);
  });
  var first = arch.getSheetByName('Sheet1');
  if (first && arch.getSheets().length > 1) arch.deleteSheet(first);

  var cache = {};
  accs.forEach(function (a) { upsert_(ss, 'Accounts', a, cache); });
  Object.keys(gsum).forEach(function (gk, i) {
    var amt = Math.round(gsum[gk] * 100) / 100; if (!amt) return;
    upsert_(ss, 'GoalLog', { id: 'GO' + ginfo[gk][2] + '_' + cut.slice(0, 4) + '_' + i, ts: cut, goal: ginfo[gk][0], action: 'Opening', amount: amt, account: ginfo[gk][1], remarks: 'Carried forward from archive', goalId: ginfo[gk][2], ref: '' }, cache);
  });
  Object.keys(lsum).forEach(function (id) {
    var amt = Math.round(lsum[id] * 100) / 100; if (!amt) return;
    upsert_(ss, 'LoanLog', { id: 'LO' + id + '_' + cut.slice(0, 4), ts: cut, person: linfo[id], action: 'Opening', amount: amt, account: '', remarks: 'Carried forward from archive', loanId: id, ref: '' }, cache);
  });
  read_(ss, 'EMIs').forEach(function (m) {
    if (!ecount[m.id]) return;
    m.paidBefore = (Number(m.paidBefore) || 0) + ecount[m.id];
    upsert_(ss, 'EMIs', m, cache);
  });
  SpreadsheetApp.flush();
  return old;
}
