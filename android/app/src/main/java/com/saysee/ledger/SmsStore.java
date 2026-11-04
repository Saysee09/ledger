package com.saysee.ledger;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Keeps bank SMS on the phone until the app files them into the "to sort" list. */
public final class SmsStore {
    private static final String PREFS = "ledger_sms";
    private static final String KEY = "queue";
    private static final int MAX = 300;
    static final String CHANNEL = "bank_sms";

    private static final Pattern AMOUNT = Pattern.compile("(?:rs\\.?|inr|₹)\\s*([\\d,]+(?:\\.\\d{1,2})?)", Pattern.CASE_INSENSITIVE);
    private static final Pattern MONEY_WORD = Pattern.compile("\\b(debited|credited|spent|sent|withdrawn|received|paid|deducted|refund(?:ed|s)?|deposited|purchase|txn|cash ?back|reversal|reversed)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern SKIP = Pattern.compile("\\b(otp|one[- ]time password|verification code|passcode|cvv)\\b|pre-?approved|apply now|\\boffer\\b", Pattern.CASE_INSENSITIVE);
    /* personal numbers (+91XXXXXXXXXX / 10 digits) are skipped; banks send from IDs like AX-KOTAKB */
    private static final Pattern PERSON = Pattern.compile("^\\+?\\d{10,13}$");

    private SmsStore() { }

    /** Quick on-phone check. The app runs the full reader (and ignores anything not a completed payment). */
    static boolean looksFinancial(String sender, String body) {
        if (body == null || body.length() < 20) return false;
        if (sender != null && PERSON.matcher(sender.replace(" ", "")).matches()) return false;
        if (SKIP.matcher(body).find()) return false;
        return AMOUNT.matcher(body).find() && MONEY_WORD.matcher(body).find();
    }

    /** last SMS this phone handed to Ledger, for the status line in Settings → Phone app */
    static void noteLast(Context c, String sender, boolean kept) {
        try {
            JSONObject o = new JSONObject();
            o.put("at", now()); o.put("from", sender == null ? "" : sender); o.put("kept", kept);
            c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("last", o.toString()).apply();
        } catch (Exception ignored) { }
    }

    static String last(Context c) { return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("last", ""); }

    static String now() { return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date()); }
    static String fmt(long ms) { return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date(ms)); }

    static synchronized void add(Context c, String body, String ts) { add(c, body, ts, ""); }

    /** sender = the SMS sender ID (e.g. VM-IRCTCI), so the app can tell who a refund is from */
    static synchronized void add(Context c, String body, String ts, String sender) {
        SharedPreferences p = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        try {
            JSONArray a = new JSONArray(p.getString(KEY, "[]"));
            for (int i = 0; i < a.length(); i++) if (body.equals(a.getJSONObject(i).optString("raw"))) return;
            JSONObject o = new JSONObject();
            o.put("raw", body);
            o.put("ts", ts);
            o.put("from", sender == null ? "" : sender);
            a.put(o);
            while (a.length() > MAX) a.remove(0);
            p.edit().putString(KEY, a.toString()).apply();
        } catch (Exception ignored) { }
    }

    static synchronized String take(Context c) {
        SharedPreferences p = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String s = p.getString(KEY, "[]");
        p.edit().putString(KEY, "[]").apply();
        return s;
    }

    static void notify(Context c, String body) {
        if (Build.VERSION.SDK_INT >= 33 && c.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        if (nm.getNotificationChannel(CHANNEL) == null) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "Bank messages", NotificationManager.IMPORTANCE_DEFAULT);
            ch.setDescription("A note when a bank payment SMS is saved to sort");
            nm.createNotificationChannel(ch);
        }
        String amt = "";
        Matcher m = AMOUNT.matcher(body);
        if (m.find()) amt = "₹" + m.group(1) + " ";
        boolean in = Pattern.compile("\\b(credited|received|deposited|refund|cash ?back)", Pattern.CASE_INSENSITIVE).matcher(body).find()
                && !Pattern.compile("\\b(debited|spent|sent)\\b", Pattern.CASE_INSENSITIVE).matcher(body).find();
        /* "refund of Rs 400 initiated, will reflect in 5-7 days": money not here yet, so it goes to the Refunds list, not "to sort" */
        boolean promise = Pattern.compile("\\b(refund|cash ?back|reversal)", Pattern.CASE_INSENSITIVE).matcher(body).find()
                && Pattern.compile("\\b(initiated|processed|will be|will reflect|within \\d|working days|business days|expected)", Pattern.CASE_INSENSITIVE).matcher(body).find()
                && !Pattern.compile("avl\\.? ?bal|available bal", Pattern.CASE_INSENSITIVE).matcher(body).find();
        Intent open = new Intent(c, MainActivity.class).putExtra(MainActivity.EXTRA_PENDING, true)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pi = PendingIntent.getActivity(c, 1, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        android.app.Notification n = new android.app.Notification.Builder(c, CHANNEL)
                .setSmallIcon(R.drawable.ic_stat_rupee)
                .setContentTitle(promise ? amt + "refund on the way" : amt + (in ? "received" : "paid") + " · tap to sort")
                .setContentText(promise ? "Ledger will watch for it and tell you if it's late" : "Ledger saved this bank message for you")
                .setAutoCancel(true)
                .setContentIntent(pi)
                .build();
        nm.notify(1001, n);
    }
}
