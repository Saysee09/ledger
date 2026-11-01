package com.saysee.ledger;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.view.View;
import android.widget.RemoteViews;

import org.json.JSONArray;
import org.json.JSONObject;

/** Home-screen widgets. The app sends a small snapshot (already formatted) each time it opens; widgets only display it. */
final class Widgets {
    private static final String PREFS = "ledger_widget";
    static final String EXTRA = "widget";

    private Widgets() { }

    static synchronized void save(Context c, String json) {
        c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("data", json).apply();
        updateAll(c);
    }

    private static JSONObject data(Context c) {
        try { return new JSONObject(c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("data", "{}")); }
        catch (Exception e) { return new JSONObject(); }
    }

    /** a bank SMS arrived while the app was closed: count it on the "Needs you" widget straight away */
    static synchronized void bumpSort(Context c) {
        try {
            JSONObject o = data(c);
            o.put("sort", o.optInt("sort") + 1);
            o.put("needs", o.optInt("needs") + 1);
            c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("data", o.toString()).apply();
            updateAll(c);
        } catch (Exception ignored) { }
    }

    static void updateAll(Context c) {
        AppWidgetManager m = AppWidgetManager.getInstance(c);
        JSONObject d = data(c);
        Class<?>[] kinds = { FreeWidget.class, MonthWidget.class, NeedsWidget.class, PulseWidget.class };
        for (Class<?> k : kinds) {
            int[] ids = m.getAppWidgetIds(new ComponentName(c, k));
            for (int id : ids) {
                try { m.updateAppWidget(id, build(c, k, d)); } catch (Exception ignored) { }
            }
        }
    }

    private static PendingIntent open(Context c, String action, int req) {
        Intent i = new Intent(c, MainActivity.class).setAction("ledger.widget." + action).putExtra(EXTRA, action)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        return PendingIntent.getActivity(c, req, i, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private static String s(JSONObject d, String k, String def) { String v = d.optString(k, ""); return v.isEmpty() ? def : v; }

    private static RemoteViews build(Context c, Class<?> k, JSONObject d) {
        String pkg = c.getPackageName();
        boolean empty = d.length() == 0;
        String at = empty ? "Open Ledger once to fill this in" : "Updated " + s(d, "at", "");
        if (k == FreeWidget.class) {
            RemoteViews v = new RemoteViews(pkg, R.layout.widget_free);
            v.setTextViewText(R.id.w_value, s(d, "free", "₹ —"));
            v.setTextViewText(R.id.w_sub, empty ? at : s(d, "safe", ""));
            v.setOnClickPendingIntent(R.id.w_root, open(c, "home", 10));
            v.setOnClickPendingIntent(R.id.w_add_exp, open(c, "exp", 11));
            v.setOnClickPendingIntent(R.id.w_add_inc, open(c, "inc", 12));
            return v;
        }
        if (k == MonthWidget.class) {
            RemoteViews v = new RemoteViews(pkg, R.layout.widget_month);
            v.setTextViewText(R.id.w_title, "Spent · " + s(d, "month", ""));
            v.setTextViewText(R.id.w_value, s(d, "spent", "₹ —"));
            v.setTextViewText(R.id.w_sub, empty ? at : s(d, "budgetLine", ""));
            int pct = Math.max(0, Math.min(100, d.optInt("pct", 0)));
            v.setProgressBar(R.id.w_bar, 100, pct, false);
            v.setViewVisibility(R.id.w_bar, d.optBoolean("hasBudget") ? View.VISIBLE : View.GONE);
            v.setTextColor(R.id.w_value, d.optBoolean("over") ? Color.parseColor("#FF8A8D") : Color.WHITE);
            v.setOnClickPendingIntent(R.id.w_root, open(c, "insights", 20));
            return v;
        }
        if (k == NeedsWidget.class) {
            RemoteViews v = new RemoteViews(pkg, R.layout.widget_needs);
            int n = d.optInt("needs", 0);
            v.setTextViewText(R.id.w_value, n == 0 ? "All clear ✓" : n + (n == 1 ? " thing" : " things"));
            JSONArray L = d.optJSONArray("lines");
            StringBuilder b = new StringBuilder();
            if (d.optInt("sort", 0) > 0 && (L == null || L.length() == 0 || !L.optString(0).startsWith("📩"))) b.append("📩 ").append(d.optInt("sort")).append(" bank SMS to sort\n");
            if (L != null) for (int i = 0; i < L.length() && i < 3; i++) b.append(L.optString(i)).append('\n');
            v.setTextViewText(R.id.w_sub, empty ? at : (b.length() > 0 ? b.toString().trim() : "Nothing to pay or sort"));
            v.setOnClickPendingIntent(R.id.w_root, open(c, "inbox", 30));
            return v;
        }
        RemoteViews v = new RemoteViews(pkg, R.layout.widget_pulse);
        v.setTextViewText(R.id.w_value, s(d, "pulse", "—"));
        v.setTextViewText(R.id.w_sub, empty ? "Open Ledger" : s(d, "pulseLabel", ""));
        v.setTextViewText(R.id.w_delta, s(d, "pulseDelta", ""));
        try { v.setTextColor(R.id.w_value, Color.parseColor(s(d, "pulseCol", "#FFFFFF"))); } catch (Exception ignored) { }
        v.setOnClickPendingIntent(R.id.w_root, open(c, "pulse", 40));
        return v;
    }
}
