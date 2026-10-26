package com.saysee.ledger;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.ActivityNotFoundException;
import android.content.ContentValues;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.provider.MediaStore;
import android.provider.Settings;
import android.provider.Telephony;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;

import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import androidx.webkit.WebViewAssetLoader;
import androidx.webkit.WebViewClientCompat;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.ref.WeakReference;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

public class MainActivity extends AppCompatActivity {
    static final String EXTRA_PENDING = "openPending";
    private static final String HOST = "appassets.androidplatform.net";
    private static final String START = "https://" + HOST + "/index.html";
    /* where new versions of the app screens come from (your GitHub Pages site) */
    private static final String UPDATE_URL = "https://saysee09.github.io/ledger/index.html";

    private static WeakReference<MainActivity> current = new WeakReference<>(null);

    private WebView web;
    private boolean openPending;
    private ValueCallback<Uri[]> fileCb;
    private final Handler ui = new Handler(Looper.getMainLooper());

    private final ActivityResultLauncher<Intent> filePicker = registerForActivityResult(
            new ActivityResultContracts.StartActivityForResult(), r -> {
                if (fileCb == null) return;
                fileCb.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(r.getResultCode(), r.getData()));
                fileCb = null;
            });

    private final ActivityResultLauncher<String[]> permAsk = registerForActivityResult(
            new ActivityResultContracts.RequestMultiplePermissions(), r -> js("window.onLedgerPerm&&onLedgerPerm()"));

    /** Called by SmsReceiver. Returns true when the app is open and took the message itself. */
    static boolean ping() {
        MainActivity a = current.get();
        if (a == null || a.web == null || a.isFinishing() || !a.hasWindowFocus()) return false;
        a.ui.post(() -> a.js("window.__ledgerSmsPing&&__ledgerSmsPing()"));
        return true;
    }

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        openPending = getIntent() != null && getIntent().getBooleanExtra(EXTRA_PENDING, false);
        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setSupportMultipleWindows(false);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setMediaPlaybackRequiresUserGesture(true);

        WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
                .setDomain(HOST)
                .addPathHandler("/", path -> {
                    if (!path.isEmpty() && !path.equals("index.html")) return null;
                    try {
                        File f = new File(getFilesDir(), "www/index.html");
                        InputStream in = f.exists() && f.length() > 100000 ? new FileInputStream(f) : getAssets().open("www/index.html");
                        return new WebResourceResponse("text/html", "utf-8", in);
                    } catch (Exception e) {
                        return null;
                    }
                })
                .build();

        web.setWebViewClient(new WebViewClientCompat() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest req) {
                return loader.shouldInterceptRequest(req.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(@NonNull WebView v, @NonNull WebResourceRequest req) {
                Uri u = req.getUrl();
                if (HOST.equals(u.getHost())) return false;
                openOutside(u);
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileCb != null) fileCb.onReceiveValue(null);
                fileCb = cb;
                try {
                    filePicker.launch(p.createIntent());
                } catch (ActivityNotFoundException e) {
                    fileCb = null;
                    return false;
                }
                return true;
            }
        });
        web.addJavascriptInterface(new Bridge(), "LedgerAndroid");

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (web.canGoBack()) web.goBack();
                else finish();
            }
        });

        web.loadUrl(START);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (intent != null && intent.getBooleanExtra(EXTRA_PENDING, false))
            js("window.__ledgerOpenPending&&__ledgerOpenPending()");
    }

    @Override
    protected void onResume() {
        super.onResume();
        current = new WeakReference<>(this);
        js("window.__ledgerSmsPing&&__ledgerSmsPing()");
    }

    @Override
    protected void onPause() {
        super.onPause();
        current = new WeakReference<>(null);
    }

    private void js(String code) {
        if (web != null) web.evaluateJavascript(code, null);
    }

    private static String q(String s) {
        return JSONObject.quote(s == null ? "" : s);
    }

    private void openOutside(Uri u) {
        try {
            Intent i = new Intent(Intent.ACTION_VIEW, u);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
        } catch (ActivityNotFoundException e) {
            js("window.toast&&toast('No app can open this link')");
        }
    }

    private boolean has(String perm) {
        return ContextCompat.checkSelfPermission(this, perm) == PackageManager.PERMISSION_GRANTED;
    }

    private int authenticators() {
        return Build.VERSION.SDK_INT >= 30
                ? BiometricManager.Authenticators.BIOMETRIC_STRONG | BiometricManager.Authenticators.DEVICE_CREDENTIAL
                : BiometricManager.Authenticators.BIOMETRIC_WEAK | BiometricManager.Authenticators.DEVICE_CREDENTIAL;
    }

    private void unlock(String title) {
        BiometricPrompt bp = new BiometricPrompt(this, ContextCompat.getMainExecutor(this), new BiometricPrompt.AuthenticationCallback() {
            @Override
            public void onAuthenticationSucceeded(@NonNull BiometricPrompt.AuthenticationResult r) {
                js("window.onLedgerUnlock&&onLedgerUnlock(true,'')");
            }

            @Override
            public void onAuthenticationError(int code, @NonNull CharSequence msg) {
                boolean quiet = code == BiometricPrompt.ERROR_USER_CANCELED || code == BiometricPrompt.ERROR_NEGATIVE_BUTTON || code == BiometricPrompt.ERROR_CANCELED;
                js("window.onLedgerUnlock&&onLedgerUnlock(false," + q(quiet ? "" : msg.toString()) + ")");
            }
        });
        BiometricPrompt.PromptInfo info = new BiometricPrompt.PromptInfo.Builder()
                .setTitle(title == null || title.isEmpty() ? "Unlock Ledger" : title)
                .setSubtitle("Fingerprint, or your phone's screen lock")
                .setAllowedAuthenticators(authenticators())
                .build();
        bp.authenticate(info);
    }

    private String sha(byte[] b) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(b);
            StringBuilder sb = new StringBuilder();
            for (byte x : d) sb.append(String.format("%02x", x));
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    private byte[] currentHtml() {
        try {
            File f = new File(getFilesDir(), "www/index.html");
            InputStream in = f.exists() && f.length() > 100000 ? new FileInputStream(f) : getAssets().open("www/index.html");
            return readAll(in);
        } catch (Exception e) {
            return new byte[0];
        }
    }

    private static byte[] readAll(InputStream in) throws java.io.IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[16384];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        in.close();
        return out.toByteArray();
    }

    /** Downloads the newest app screens from GitHub Pages; they are used from the next start. */
    private void checkUpdate() {
        new Thread(() -> {
            try {
                HttpURLConnection c = (HttpURLConnection) new URL(UPDATE_URL + "?t=" + System.currentTimeMillis()).openConnection();
                c.setConnectTimeout(10000);
                c.setReadTimeout(20000);
                c.setUseCaches(false);
                if (c.getResponseCode() != 200) return;
                byte[] b = readAll(c.getInputStream());
                String head = new String(b, 0, Math.min(b.length, 4000), StandardCharsets.UTF_8);
                String all = new String(b, StandardCharsets.UTF_8);
                if (b.length < 100000 || !head.contains("<title>") || !all.contains("LedgerSms")) return;
                if (sha(b).equals(sha(currentHtml()))) {
                    ui.post(() -> js("window.toast&&window.__ledgerManualUpd&&toast('You have the latest version')"));
                    return;
                }
                File dir = new File(getFilesDir(), "www");
                if (!dir.exists() && !dir.mkdirs()) return;
                File tmp = new File(dir, "index.tmp");
                try (OutputStream o = new FileOutputStream(tmp)) {
                    o.write(b);
                }
                if (tmp.renameTo(new File(dir, "index.html"))) ui.post(() -> js("window.onLedgerUpdate&&onLedgerUpdate()"));
            } catch (Exception ignored) {
            }
        }).start();
    }

    private String readInbox(int days) {
        JSONArray out = new JSONArray();
        if (!has(Manifest.permission.READ_SMS)) return "[]";
        long since = System.currentTimeMillis() - days * 86400000L;
        try (Cursor c = getContentResolver().query(Telephony.Sms.Inbox.CONTENT_URI,
                new String[]{Telephony.Sms.ADDRESS, Telephony.Sms.BODY, Telephony.Sms.DATE},
                Telephony.Sms.DATE + " > ?", new String[]{String.valueOf(since)}, Telephony.Sms.DATE + " ASC")) {
            if (c == null) return "[]";
            while (c.moveToNext()) {
                String addr = c.getString(0), body = c.getString(1);
                long date = c.getLong(2);
                if (!SmsStore.looksFinancial(addr, body)) continue;
                JSONObject o = new JSONObject();
                o.put("raw", body);
                o.put("ts", SmsStore.fmt(date));
                out.put(o);
            }
        } catch (Exception ignored) {
        }
        return out.toString();
    }

    private String saveFile(String name, String data, String mime) {
        try {
            byte[] b = data.getBytes(StandardCharsets.UTF_8);
            if (Build.VERSION.SDK_INT >= 29) {
                ContentValues v = new ContentValues();
                v.put(MediaStore.Downloads.DISPLAY_NAME, name);
                v.put(MediaStore.Downloads.MIME_TYPE, mime);
                v.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                Uri u = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
                if (u == null) return "";
                try (OutputStream o = getContentResolver().openOutputStream(u)) {
                    if (o == null) return "";
                    o.write(b);
                }
                return "Downloads/" + name;
            }
            File dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            if (dir == null) return "";
            File f = new File(dir, name);
            try (OutputStream o = new FileOutputStream(f)) {
                o.write(b);
            }
            return f.getAbsolutePath();
        } catch (Exception e) {
            return "";
        }
    }

    /** Everything the web app can ask the phone for. */
    private class Bridge {
        @JavascriptInterface
        public String info() {
            try {
                JSONObject o = new JSONObject();
                o.put("version", getPackageManager().getPackageInfo(getPackageName(), 0).versionName);
                o.put("sms", has(Manifest.permission.RECEIVE_SMS) && has(Manifest.permission.READ_SMS));
                o.put("notif", Build.VERSION.SDK_INT < 33 || has(Manifest.permission.POST_NOTIFICATIONS));
                PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
                o.put("battery", pm != null && pm.isIgnoringBatteryOptimizations(getPackageName()));
                o.put("bio", BiometricManager.from(MainActivity.this).canAuthenticate(authenticators()) == BiometricManager.BIOMETRIC_SUCCESS);
                return o.toString();
            } catch (Exception e) {
                return "{}";
            }
        }

        @JavascriptInterface
        public void requestSms() {
            ui.post(() -> {
                if (Build.VERSION.SDK_INT >= 33)
                    permAsk.launch(new String[]{Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS, Manifest.permission.POST_NOTIFICATIONS});
                else
                    permAsk.launch(new String[]{Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS});
            });
        }

        @JavascriptInterface
        public String takeSms() {
            return SmsStore.take(MainActivity.this);
        }

        @JavascriptInterface
        public String readInbox(int days) {
            return MainActivity.this.readInbox(Math.max(1, Math.min(days, 90)));
        }

        @JavascriptInterface
        public void unlock(String title) {
            ui.post(() -> MainActivity.this.unlock(title));
        }

        @JavascriptInterface
        @SuppressLint("BatteryLife")
        public void openBattery() {
            ui.post(() -> {
                try {
                    startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + getPackageName())));
                } catch (Exception e) {
                    startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName())));
                }
            });
        }

        @JavascriptInterface
        public String saveFile(String name, String data, String mime) {
            return MainActivity.this.saveFile(name, data, mime);
        }

        @JavascriptInterface
        public void checkUpdate() {
            MainActivity.this.checkUpdate();
        }

        @JavascriptInterface
        public void reload() {
            ui.post(() -> web.loadUrl(START));
        }

        @JavascriptInterface
        public String pendingOpen() {
            boolean p = openPending;
            openPending = false;
            return p ? "1" : "";
        }
    }
}
