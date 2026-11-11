package com.saysee.ledger;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;

/**
 * Android closes an app while it installs its update and never reopens it by itself.
 * Right after the new version is in place, this shows "Brokeless updated · tap to open".
 */
public class UpdatedReceiver extends BroadcastReceiver {
    static final String CHANNEL = "app_updated";

    @Override
    public void onReceive(Context c, Intent intent) {
        if (intent == null || !Intent.ACTION_MY_PACKAGE_REPLACED.equals(intent.getAction())) return;
        try {
            String ver = c.getPackageManager().getPackageInfo(c.getPackageName(), 0).versionName;
            c.getSharedPreferences(UpdateChecker.PREFS, Context.MODE_PRIVATE).edit().putString("latest", "").putString("justUpdated", ver).apply();
            if (Build.VERSION.SDK_INT >= 33 && c.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
            NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            if (nm.getNotificationChannel(CHANNEL) == null) {
                NotificationChannel ch = new NotificationChannel(CHANNEL, "App updated", NotificationManager.IMPORTANCE_HIGH);
                ch.setDescription("Tells you when a Brokeless update has finished installing");
                nm.createNotificationChannel(ch);
            }
            nm.cancel(2001); /* the "ready to install" notice is done */
            Intent open = new Intent(c, MainActivity.class).setAction("ledger.updated").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            PendingIntent pi = PendingIntent.getActivity(c, 51, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
            android.app.Notification n = new android.app.Notification.Builder(c, CHANNEL)
                    .setSmallIcon(R.drawable.ic_stat_rupee)
                    .setContentTitle("✅ Brokeless updated to " + ver)
                    .setContentText("Tap to open Brokeless")
                    .setAutoCancel(true)
                    .setContentIntent(pi)
                    .setTimeoutAfter(10 * 60 * 1000)
                    .build();
            nm.notify(2002, n);
        } catch (Exception ignored) { }
    }
}
