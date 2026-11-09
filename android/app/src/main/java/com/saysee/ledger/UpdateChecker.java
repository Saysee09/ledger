package com.saysee.ledger;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** Looks at the GitHub Releases of the Ledger repo for a newer APK (test builds also see test releases). */
final class UpdateChecker {
    private static final String API = "https://api.github.com/repos/Saysee09/ledger/releases?per_page=15";
    static final String PREFS = "ledger_update";
    static final String CHANNEL = "app_updates";

    private UpdateChecker() { }

    static PackageInfo me(Context c) {
        try { return c.getPackageManager().getPackageInfo(c.getPackageName(), 0); } catch (PackageManager.NameNotFoundException e) { return null; }
    }

    @SuppressWarnings("deprecation")
    static int myCode(Context c) {
        PackageInfo p = me(c);
        if (p == null) return 0;
        return Build.VERSION.SDK_INT >= 28 ? (int) p.getLongVersionCode() : p.versionCode;
    }

    static String myName(Context c) { PackageInfo p = me(c); return p == null ? "" : p.versionName; }

    static boolean isTest(Context c) { return myName(c).contains("test"); }

    /** "Get test builds": on by default for anyone who has ever run a test build (older live builds were labelled test too) */
    static boolean beta(Context c) {
        SharedPreferences p = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (!p.contains("beta")) p.edit().putBoolean("beta", isTest(c)).apply();
        return p.getBoolean("beta", false) || isTest(c);
    }

    static void setBeta(Context c, boolean on) {
        c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean("beta", on).putString("latest", "").apply();
    }

    private static String get(String url) throws Exception {
        HttpURLConnection h = (HttpURLConnection) new URL(url).openConnection();
        h.setConnectTimeout(10000);
        h.setReadTimeout(20000);
        h.setRequestProperty("Accept", "application/vnd.github+json");
        h.setRequestProperty("User-Agent", "Brokeless-Android");
        if (h.getResponseCode() != 200) throw new Exception("HTTP " + h.getResponseCode());
        InputStream in = h.getInputStream();
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] b = new byte[16384];
        int n;
        while ((n = in.read(b)) > 0) out.write(b, 0, n);
        in.close();
        return new String(out.toByteArray(), StandardCharsets.UTF_8);
    }

    /** Newest release newer than the installed app, or null. Saved so the app can show it offline. */
    static JSONObject check(Context c) {
        try {
            JSONArray a = new JSONArray(get(API));
            int mine = myCode(c);
            boolean test = beta(c);
            JSONObject best = null;
            int bestN = mine;
            for (int i = 0; i < a.length(); i++) {
                JSONObject r = a.getJSONObject(i);
                if (r.optBoolean("draft")) continue;
                boolean pre = r.optBoolean("prerelease");
                if (pre && !test) continue;
                String tag = r.optString("tag_name");
                int dash = tag.lastIndexOf('-');
                int n;
                try { n = Integer.parseInt(tag.substring(dash + 1)); } catch (Exception e) { continue; }
                if (n <= bestN) continue;
                String url = "";
                long size = 0;
                JSONArray as = r.optJSONArray("assets");
                if (as != null) for (int j = 0; j < as.length(); j++) {
                    JSONObject x = as.getJSONObject(j);
                    if (x.optString("name").endsWith(".apk")) { url = x.optString("browser_download_url"); size = x.optLong("size"); break; }
                }
                if (url.isEmpty()) continue;
                best = new JSONObject();
                best.put("tag", tag);
                best.put("n", n);
                best.put("name", r.optString("name"));
                best.put("date", r.optString("published_at"));
                best.put("notes", r.optString("body"));
                best.put("url", url);
                best.put("size", size);
                best.put("test", pre);
                best.put("page", r.optString("html_url"));
                bestN = n;
            }
            SharedPreferences p = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            p.edit().putString("latest", best == null ? "" : best.toString()).putLong("checked", System.currentTimeMillis()).apply();
            return best;
        } catch (Exception e) {
            return null;
        }
    }

    /** What the last check found, if it is still newer than what is installed. */
    static String saved(Context c) {
        try {
            String s = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("latest", "");
            if (s.isEmpty()) return "";
            JSONObject o = new JSONObject(s);
            return o.optInt("n") > myCode(c) ? s : "";
        } catch (Exception e) { return ""; }
    }

    /** one phone notification per new version */
    static void notifyOnce(Context c, JSONObject u) {
        if (u == null) return;
        SharedPreferences p = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String tag = u.optString("tag");
        if (tag.equals(p.getString("notified", ""))) return;
        if (Build.VERSION.SDK_INT >= 33 && c.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        if (nm.getNotificationChannel(CHANNEL) == null) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "App updates", NotificationManager.IMPORTANCE_DEFAULT);
            ch.setDescription("When a new version of Brokeless is ready to install");
            nm.createNotificationChannel(ch);
        }
        Intent open = new Intent(c, MainActivity.class).setAction("ledger.widget.update").putExtra(Widgets.EXTRA, "update")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pi = PendingIntent.getActivity(c, 50, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        String first = "";
        for (String line : u.optString("notes").split("\n")) { String t = line.replaceAll("^[#*\\-\\s]+", "").trim(); if (!t.isEmpty() && !t.toLowerCase().startsWith("ledger") && !t.toLowerCase().startsWith("brokeless")) { first = t; break; } }
        android.app.Notification n = new android.app.Notification.Builder(c, CHANNEL)
                .setSmallIcon(R.drawable.ic_stat_rupee)
                .setContentTitle("Brokeless " + u.optString("tag").replaceAll("\\D+", ".").replaceAll("^\\.", "8.0.") + " is ready · tap to install")
                .setContentText(first.isEmpty() ? "See what's new" : first)
                .setAutoCancel(true)
                .setContentIntent(pi)
                .build();
        nm.notify(2001, n);
        p.edit().putString("notified", tag).apply();
    }
}
