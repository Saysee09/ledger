package com.saysee.ledger;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.PendingIntent;
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
import android.os.CancellationSignal;
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
import androidx.activity.result.IntentSenderRequest;
import com.google.android.gms.auth.api.identity.AuthorizationRequest;
import com.google.android.gms.auth.api.identity.AuthorizationResult;
import com.google.android.gms.auth.api.identity.Identity;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.common.api.Scope;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.biometric.BiometricManager;
import androidx.credentials.Credential;
import androidx.credentials.CredentialManager;
import androidx.credentials.CredentialManagerCallback;
import androidx.credentials.CustomCredential;
import androidx.credentials.GetCredentialRequest;
import androidx.credentials.GetCredentialResponse;
import androidx.credentials.exceptions.GetCredentialCancellationException;
import androidx.credentials.exceptions.GetCredentialException;
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption;
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import java.util.concurrent.TimeUnit;
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
    private String widgetAction;
    private File pendingApk;
    private ValueCallback<Uri[]> fileCb;
    private final Handler ui = new Handler(Looper.getMainLooper());

    private final ActivityResultLauncher<Intent> filePicker = registerForActivityResult(
            new ActivityResultContracts.StartActivityForResult(), r -> {
                if (fileCb == null) return;
                fileCb.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(r.getResultCode(), r.getData()));
                fileCb = null;
            });

    /** Google Drive access: the user's OK screen comes back here */
    private final ActivityResultLauncher<IntentSenderRequest> driveAsk = registerForActivityResult(
            new ActivityResultContracts.StartIntentSenderForResult(), r -> {
                try {
                    AuthorizationResult ar = Identity.getAuthorizationClient(this).getAuthorizationResultFromIntent(r.getData());
                    driveDone(ar.getAccessToken(), ar.getAccessToken() == null ? "Sign-in cancelled" : "");
                } catch (Exception e) { driveDone(null, "Sign-in cancelled"); }
            });

    private void driveDone(String tok, String err) { js("window.onDriveToken&&onDriveToken(" + q(tok) + "," + q(err) + ")"); }

    /** asks Google for a Drive token (only files Brokeless makes). Silent when the user already said yes. */
    private void driveAuth(boolean interactive) {
        try {
            java.util.List<Scope> sc = java.util.Arrays.asList(new Scope("https://www.googleapis.com/auth/drive.file"), new Scope("email"), new Scope("profile"), new Scope("openid"));
            AuthorizationRequest req = AuthorizationRequest.builder().setRequestedScopes(sc).build();
            Identity.getAuthorizationClient(this).authorize(req)
                    .addOnSuccessListener(res -> {
                        if (res.hasResolution() && res.getPendingIntent() != null) {
                            if (!interactive) { driveDone(null, "needs-consent"); return; }
                            try { driveAsk.launch(new IntentSenderRequest.Builder(res.getPendingIntent().getIntentSender()).build()); }
                            catch (Exception e) { driveDone(null, "Could not open Google sign-in"); }
                        } else driveDone(res.getAccessToken(), res.getAccessToken() == null ? "No token from Google" : "");
                    })
                    .addOnFailureListener(e -> driveDone(null, e instanceof ApiException ? "Google sign-in error " + ((ApiException) e).getStatusCode() + ". Check the phone has Google Play services." : String.valueOf(e.getMessage())));
        } catch (Exception e) { driveDone(null, String.valueOf(e.getMessage())); }
    }

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
        dropOldScreens();
        openPending = getIntent() != null && getIntent().getBooleanExtra(EXTRA_PENDING, false);
        widgetAction = getIntent() != null ? getIntent().getStringExtra(Widgets.EXTRA) : null;
        if (getIntent() != null && ACTION_INSTALL.equals(getIntent().getAction())) { final Intent st = getIntent(); ui.postDelayed(() -> installStatus(st), 800); }
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
        /* respect the phone's bigger-text setting, but cap it so screens never spill off the side */
        if (s.getTextZoom() > 115) s.setTextZoom(115);

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

        /* look for a new app version about twice a day, even when Ledger is closed */
        try {
            PeriodicWorkRequest w = new PeriodicWorkRequest.Builder(UpdateWorker.class, 12, TimeUnit.HOURS)
                    .setConstraints(new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()).build();
            WorkManager.getInstance(this).enqueueUniquePeriodicWork("ledger-update", ExistingPeriodicWorkPolicy.KEEP, w);
        } catch (Exception ignored) { }
    }

    private volatile boolean downloading;
    static final String ACTION_INSTALL = "com.saysee.ledger.INSTALL_STATUS";

    /** Downloads the new APK (one at a time, to a temp file), checks it, then installs it with Android's PackageInstaller. */
    private void installUpdate(String url, long expect) {
        if (downloading) { js("window.toast&&toast('Already downloading…')"); return; }
        downloading = true;
        new Thread(() -> {
            try {
                File dir = new File(getCacheDir(), "updates");
                if (!dir.exists() && !dir.mkdirs()) throw new Exception("no space on phone");
                File tmp = new File(dir, "ledger.part"), f = new File(dir, "ledger.apk");
                if (tmp.exists()) tmp.delete();
                HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                c.setInstanceFollowRedirects(true);
                c.setConnectTimeout(15000);
                c.setReadTimeout(30000);
                c.setRequestProperty("User-Agent", "Brokeless-Android");
                c.setRequestProperty("Accept", "application/octet-stream");
                int code = c.getResponseCode();
                for (int hop = 0; hop < 5 && (code == 301 || code == 302 || code == 303 || code == 307 || code == 308); hop++) {
                    String loc = c.getHeaderField("Location");
                    c.disconnect();
                    c = (HttpURLConnection) new URL(new URL(url), loc).openConnection();
                    c.setConnectTimeout(15000);
                    c.setReadTimeout(30000);
                    c.setRequestProperty("User-Agent", "Brokeless-Android");
                    code = c.getResponseCode();
                }
                if (code != 200) throw new Exception("server said " + code);
                long total = c.getContentLengthLong(), got = 0;
                if (total <= 0) total = expect;
                int last = -1;
                try (InputStream in = c.getInputStream(); OutputStream o = new FileOutputStream(tmp)) {
                    byte[] b = new byte[65536];
                    int n;
                    while ((n = in.read(b)) > 0) {
                        o.write(b, 0, n);
                        got += n;
                        int pct = total > 0 ? (int) Math.min(99, got * 100 / total) : -1;
                        if (pct != last && pct >= 0) { last = pct; final int p = pct; ui.post(() -> js("window.onLedgerDl&&onLedgerDl(" + p + ")")); }
                    }
                }
                if (expect > 0 && tmp.length() != expect) throw new Exception("download incomplete (" + tmp.length() + " of " + expect + " bytes). Try again on Wi-Fi");
                /* make sure it really is a newer Ledger before asking Android to install it */
                android.content.pm.PackageInfo pi = getPackageManager().getPackageArchiveInfo(tmp.getAbsolutePath(), 0);
                if (pi == null || !getPackageName().equals(pi.packageName)) throw new Exception("the downloaded file is not a valid Brokeless app. Try again");
                if (f.exists()) f.delete();
                if (!tmp.renameTo(f)) throw new Exception("could not save the update");
                ui.post(() -> { js("window.onLedgerDl&&onLedgerDl(100)"); openInstaller(f); });
            } catch (Exception e) {
                ui.post(() -> js("window.onLedgerDl&&onLedgerDl(-1," + q(String.valueOf(e.getMessage())) + ")"));
            } finally {
                downloading = false;
            }
        }).start();
    }

    private void openInstaller(File f) {
        if (Build.VERSION.SDK_INT >= 26 && !getPackageManager().canRequestPackageInstalls()) {
            pendingApk = f;
            js("window.onLedgerDl&&onLedgerDl(-2)");
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getPackageName())));
            } catch (Exception e) {
                js("window.onLedgerDl&&onLedgerDl(-1,'Open Settings → Apps → Brokeless → Install unknown apps')");
            }
            return;
        }
        pendingApk = null;
        new Thread(() -> {
            try {
                android.content.pm.PackageInstaller pkg = getPackageManager().getPackageInstaller();
                android.content.pm.PackageInstaller.SessionParams sp = new android.content.pm.PackageInstaller.SessionParams(android.content.pm.PackageInstaller.SessionParams.MODE_FULL_INSTALL);
                sp.setAppPackageName(getPackageName());
                int id = pkg.createSession(sp);
                try (android.content.pm.PackageInstaller.Session ses = pkg.openSession(id)) {
                    try (InputStream in = new FileInputStream(f); OutputStream out = ses.openWrite("ledger.apk", 0, f.length())) {
                        byte[] b = new byte[65536];
                        int n;
                        while ((n = in.read(b)) > 0) out.write(b, 0, n);
                        ses.fsync(out);
                    }
                    Intent cb = new Intent(this, MainActivity.class).setAction(ACTION_INSTALL).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
                    int fl = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 31 ? PendingIntent.FLAG_MUTABLE : 0);
                    ses.commit(PendingIntent.getActivity(this, 77, cb, fl).getIntentSender());
                }
                ui.post(() -> js("window.onLedgerDl&&onLedgerDl(101)"));
            } catch (Exception e) {
                ui.post(() -> js("window.onLedgerDl&&onLedgerDl(-1," + q("installer: " + e.getMessage()) + ")"));
            }
        }).start();
    }

    /** answers from Android's installer: ask you to confirm, or report a problem */
    private void installStatus(Intent i) {
        int st = i.getIntExtra(android.content.pm.PackageInstaller.EXTRA_STATUS, -999);
        if (st == android.content.pm.PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirm = i.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirm != null) { confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); try { startActivity(confirm); } catch (Exception ignored) { } }
        } else if (st != android.content.pm.PackageInstaller.STATUS_SUCCESS && st != -999) {
            String m = i.getStringExtra(android.content.pm.PackageInstaller.EXTRA_STATUS_MESSAGE);
            js("window.onLedgerDl&&onLedgerDl(-1," + q(st == android.content.pm.PackageInstaller.STATUS_FAILURE_ABORTED ? "install cancelled" : "Android said: " + (m == null ? "install failed (" + st + ")" : m)) + ")");
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (intent != null && ACTION_INSTALL.equals(intent.getAction())) { installStatus(intent); return; }
        if (intent != null && intent.getBooleanExtra(EXTRA_PENDING, false))
            js("window.__ledgerOpenPending&&__ledgerOpenPending()");
        String w = intent != null ? intent.getStringExtra(Widgets.EXTRA) : null;
        if (w != null) js("window.__ledgerAction&&__ledgerAction(" + q(w) + ")");
    }

    @Override
    protected void onResume() {
        super.onResume();
        current = new WeakReference<>(this);
        js("window.__ledgerSmsPing&&__ledgerSmsPing()");
        /* came back from "Install unknown apps": carry on with the install */
        if (pendingApk != null && (Build.VERSION.SDK_INT < 26 || getPackageManager().canRequestPackageInstalls())) openInstaller(pendingApk);
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
        /* WEAK includes face unlock on phones that let apps use it (some Samsung models only allow fingerprint);
           DEVICE_CREDENTIAL = the phone's own pattern / PIN / password as a fallback */
        return BiometricManager.Authenticators.BIOMETRIC_WEAK | BiometricManager.Authenticators.DEVICE_CREDENTIAL;
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
                .setTitle(title == null || title.isEmpty() ? "Unlock Brokeless" : title)
                .setSubtitle("Fingerprint, face or your phone's screen lock")
                .setAllowedAuthenticators(authenticators())
                .build();
        bp.authenticate(info);
    }

    /** Native "Sign in with Google" (Google blocks its web sign-in inside apps). Returns an ID token to the web app. */
    private void googleSignIn(String clientId) {
        try {
            GetSignInWithGoogleOption opt = new GetSignInWithGoogleOption.Builder(clientId).build();
            GetCredentialRequest req = new GetCredentialRequest.Builder().addCredentialOption(opt).build();
            CredentialManager.create(this).getCredentialAsync(this, req, new CancellationSignal(), ContextCompat.getMainExecutor(this),
                    new CredentialManagerCallback<GetCredentialResponse, GetCredentialException>() {
                        @Override
                        public void onResult(GetCredentialResponse r) {
                            Credential c = r.getCredential();
                            if (c instanceof CustomCredential && GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL.equals(c.getType())) {
                                try {
                                    String tok = GoogleIdTokenCredential.createFrom(c.getData()).getIdToken();
                                    js("window.onLedgerGoogle&&onLedgerGoogle(" + q(tok) + ",'')");
                                } catch (Exception e) {
                                    js("window.onLedgerGoogle&&onLedgerGoogle(''," + q("Google sign-in failed") + ")");
                                }
                            } else {
                                js("window.onLedgerGoogle&&onLedgerGoogle(''," + q("Google sign-in failed") + ")");
                            }
                        }

                        @Override
                        public void onError(@NonNull GetCredentialException e) {
                            String m = e instanceof GetCredentialCancellationException ? "" : "Google sign-in: " + e.getMessage();
                            js("window.onLedgerGoogle&&onLedgerGoogle(''," + q(m) + ")");
                        }
                    });
        } catch (Exception e) {
            js("window.onLedgerGoogle&&onLedgerGoogle(''," + q("Google sign-in is not available on this phone") + ")");
        }
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

    /** A freshly installed app brings its own screens: forget screens downloaded before this install
     *  (otherwise an older copy from the website keeps showing after an update). */
    private void dropOldScreens() {
        try {
            File f = new File(getFilesDir(), "www/index.html");
            if (!f.exists()) return;
            long installed = getPackageManager().getPackageInfo(getPackageName(), 0).lastUpdateTime;
            if (f.lastModified() < installed) {
                String dl = new String(readAll(new java.io.FileInputStream(f)), StandardCharsets.UTF_8);
                String own = new String(readAll(getAssets().open("www/index.html")), StandardCharsets.UTF_8);
                if (appV(dl) < appV(own) || (appV(dl) == appV(own) && build(dl).compareTo(build(own)) <= 0)) f.delete();
            }
        } catch (Throwable ignored) { }
    }

    private static String build(String html) {
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("const APP_BUILD = '([^']*)'").matcher(html);
        return m.find() ? m.group(1) : "";
    }

    private static int appV(String html) {
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("const APP_V = (\\d+)").matcher(html);
        return m.find() ? Integer.parseInt(m.group(1)) : 0;
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
                /* never go back to older screens (e.g. a test build talking to the live site) */
                String cur = new String(currentHtml(), StandardCharsets.UTF_8);
                if (appV(all) < appV(cur)) return;
                if (appV(all) == appV(cur) && build(all).compareTo(build(cur)) < 0) return;
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
                o.put("from", addr == null ? "" : addr);
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

    /** Monthly wrap: a PNG made by the app (base64). share = Android share sheet; otherwise saved to Pictures/Ledger. */
    private String sharePng(String name, String b64, String text, boolean share) {
        try {
            byte[] b = android.util.Base64.decode(b64, android.util.Base64.DEFAULT);
            String safe = name.replaceAll("[^A-Za-z0-9._-]", "_");
            if (!share) {
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues v = new ContentValues();
                    v.put(MediaStore.Images.Media.DISPLAY_NAME, safe);
                    v.put(MediaStore.Images.Media.MIME_TYPE, "image/png");
                    v.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Brokeless");
                    Uri u = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, v);
                    if (u == null) return "";
                    try (OutputStream o = getContentResolver().openOutputStream(u)) {
                        if (o == null) return "";
                        o.write(b);
                    }
                    return "Pictures/Brokeless/" + safe;
                }
                File dir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
                if (dir == null) return "";
                File f = new File(dir, safe);
                try (OutputStream o = new FileOutputStream(f)) { o.write(b); }
                return f.getAbsolutePath();
            }
            File dir = new File(getCacheDir(), "share");
            if (!dir.exists() && !dir.mkdirs()) return "";
            File f = new File(dir, safe);
            try (OutputStream o = new FileOutputStream(f)) { o.write(b); }
            Uri u = FileProvider.getUriForFile(this, "com.saysee.ledger.files", f);
            Intent s = new Intent(Intent.ACTION_SEND);
            s.setType("image/png");
            s.putExtra(Intent.EXTRA_STREAM, u);
            if (text != null && !text.isEmpty()) s.putExtra(Intent.EXTRA_TEXT, text);
            s.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            Intent ch = Intent.createChooser(s, "Share your month");
            ch.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            ui.post(() -> {
                try { startActivity(ch); } catch (ActivityNotFoundException e) { /* no app to share with */ }
            });
            return "ok";
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
                o.put("code", UpdateChecker.myCode(MainActivity.this));
                o.put("beta", UpdateChecker.beta(MainActivity.this));
                o.put("sms", has(Manifest.permission.RECEIVE_SMS) && has(Manifest.permission.READ_SMS));
                o.put("smsLast", SmsStore.last(MainActivity.this));
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
        public String shareImage(String name, String b64, String text) {
            return MainActivity.this.sharePng(name, b64, text, true);
        }

        @JavascriptInterface
        public String saveImage(String name, String b64) {
            return MainActivity.this.sharePng(name, b64, "", false);
        }

        @JavascriptInterface
        public void googleSignIn(String clientId) {
            ui.post(() -> MainActivity.this.googleSignIn(clientId));
        }

        @JavascriptInterface
        public void checkUpdate() {
            MainActivity.this.checkUpdate();
        }

        @JavascriptInterface
        public void reload() {
            ui.post(() -> web.loadUrl(START));
        }

        /** newest version found on GitHub (JSON) or "" */
        /** the version just installed by an update, once (empty afterwards) */
        @JavascriptInterface
        public String justUpdated() {
            android.content.SharedPreferences up = getSharedPreferences(UpdateChecker.PREFS, MODE_PRIVATE);
            String v = up.getString("justUpdated", "");
            if (!v.isEmpty()) up.edit().remove("justUpdated").apply();
            return v;
        }

        /** Google Drive sign-in for "Sign in with Google" (Drive mode). "1" = may show the account / OK screen */
        @JavascriptInterface
        public void driveAuth(String interactive) { ui.post(() -> MainActivity.this.driveAuth("1".equals(interactive))); }

        /** turn "Get test builds" on or off */
        @JavascriptInterface
        public void setBeta(String on) { UpdateChecker.setBeta(MainActivity.this, "1".equals(on) || "true".equals(on)); }

        @JavascriptInterface
        public String updateInfo() { return UpdateChecker.saved(MainActivity.this); }

        /** check GitHub now; answers through window.onLedgerNewVersion(json) */
        @JavascriptInterface
        public void updateCheck() {
            new Thread(() -> {
                org.json.JSONObject u = UpdateChecker.check(MainActivity.this);
                final String j = u == null ? "" : u.toString();
                ui.post(() -> js("window.onLedgerNewVersion&&onLedgerNewVersion(" + q(j) + ")"));
            }).start();
        }

        @JavascriptInterface
        public void installUpdate(String url) { MainActivity.this.installUpdate(url, 0); }

        @JavascriptInterface
        public void installUpdate2(String url, String size) {
            long n = 0;
            try { n = Long.parseLong(size); } catch (Exception ignored) { }
            MainActivity.this.installUpdate(url, n);
        }

        /** the app sends a ready-made snapshot for the home-screen widgets */
        @JavascriptInterface
        public void setWidgets(String json) {
            Widgets.save(MainActivity.this, json == null ? "{}" : json);
        }

        /** a widget button opened the app (exp / inc / inbox / pulse / insights / home) */
        @JavascriptInterface
        public String takeAction() {
            String a = widgetAction;
            widgetAction = null;
            return a == null ? "" : a;
        }

        @JavascriptInterface
        public String pendingOpen() {
            boolean p = openPending;
            openPending = false;
            return p ? "1" : "";
        }
    }
}
