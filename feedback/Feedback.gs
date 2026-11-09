/**
 * Brokeless · Feedback inbox
 * ------------------------------------------------------------
 * A tiny web app that receives feedback from Brokeless users, keeps it in a
 * "Feedback" tab of this Sheet and emails it to you (the owner).
 * Users never see your email address: the app only knows this script's URL.
 *
 * One-time setup (5 minutes, use YOUR Gmail):
 *  1. sheets.new → name it "Brokeless Feedback".
 *  2. Extensions → Apps Script → delete everything → paste this file → Save.
 *  3. Run → setup → allow the permissions it asks for.
 *  4. Deploy → New deployment → type: Web app
 *       Execute as: Me      Who has access: Anyone
 *     → Deploy → copy the Web app URL (ends in /exec) and send it to Claude.
 *  Later changes: Deploy → Manage deployments → ✏ → Version: New version → Deploy.
 */

var VERSION = 1;
var MAX_TEXT = 4000;          // characters per message
var PER_HOUR = 6;             // messages per install per hour (stops spam)

function setup() {
  var sh = sheet_();
  MailApp.getRemainingDailyQuota();   // asks for the "send email as you" permission now
  SpreadsheetApp.getActiveSpreadsheet().toast('Feedback inbox ready. Now Deploy → New deployment → Web app.');
  return sh.getName();
}

function sheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet(), sh = ss.getSheetByName('Feedback');
  if (!sh) {
    sh = ss.insertSheet('Feedback');
    sh.appendRow(['Received', 'Type', 'Message', 'Reply to', 'App version', 'Device', 'Screen', 'Install ID', 'Status']);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, 9).setFontWeight('bold');
    sh.setColumnWidth(3, 420);
  }
  return sh;
}

function doGet() {
  return out_({ ok: true, app: 'Brokeless feedback', version: VERSION });
}

function doPost(e) {
  try {
    var b = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (b.action !== 'feedback') return out_({ ok: false, error: 'Unknown request' });
    var text = String(b.text || '').trim().slice(0, MAX_TEXT);
    if (text.length < 3) return out_({ ok: false, error: 'Message is empty' });
    var type = ({ idea: '💡 Idea', bug: '🐞 Problem', like: '❤️ Like', other: '💬 Other' })[b.type] || '💬 Other';
    var iid = String(b.iid || 'unknown').replace(/[^\w-]/g, '').slice(0, 40) || 'unknown';
    var reply = String(b.reply || '').trim().toLowerCase().slice(0, 120);
    if (reply && !/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/.test(reply)) reply = '';
    var ver = String(b.version || '').slice(0, 40), dev = String(b.device || '').slice(0, 120), scr = String(b.screen || '').slice(0, 60);

    /* simple spam guard: a few messages per install per hour */
    var cache = CacheService.getScriptCache(), k = 'n_' + iid, n = +(cache.get(k) || 0);
    if (n >= PER_HOUR) return out_({ ok: false, error: 'Too many messages. Try again in an hour.' });
    cache.put(k, String(n + 1), 3600);

    var lock = LockService.getScriptLock(); lock.waitLock(10000);
    try { sheet_().appendRow([new Date(), type, text, reply, ver, dev, scr, iid, 'New']); } finally { lock.releaseLock(); }

    var owner = Session.getEffectiveUser().getEmail();
    if (owner) {
      var body = type + '\n\n' + text + '\n\n— — —\nApp: ' + ver + '\nDevice: ' + dev + '\nScreen: ' + scr + '\nInstall: ' + iid + (reply ? '\nReply to: ' + reply : '\n(No reply address given)');
      var opt = { to: owner, subject: 'Brokeless feedback · ' + type + ' · ' + text.slice(0, 50).replace(/\s+/g, ' '), body: body, name: 'Brokeless feedback' };
      if (reply) opt.replyTo = reply;
      MailApp.sendEmail(opt);
    }
    return out_({ ok: true });
  } catch (err) {
    return out_({ ok: false, error: 'Could not send. Try again later.' });
  }
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
