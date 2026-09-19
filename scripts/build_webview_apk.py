import os, re, base64, functools, paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
secrets = os.path.join(os.path.dirname(ROOT), ".secrets")

def read_env(path):
    d = {}
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if "=" in s and not s.startswith("#"):
            k, v = s.split("=", 1); d[k.strip()] = v.strip()
    return d

ssh = read_env(os.path.join(secrets, "local.env"))
apk_env = read_env(os.path.join(secrets, "apk-build.local.env"))
ssh_cfg = {k[4:]: v for k, v in ssh.items() if k.startswith("SSH_")}

HOME_HOST = "yexingchen.cn"
START_URL = f"https://{HOME_HOST}/workbench"

MAIN_JAVA = r'''
package cn.yexingchen.app;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Message;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.GeolocationPermissions;
import android.webkit.MimeTypeMap;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final String START_URL = "https://yexingchen.cn/workbench";
    private static final String HOME_HOST = "yexingchen.cn";

    private WebView webView;
    private ProgressBar progressBar;
    private ValueCallback<Uri[]> filePathCallback;
    private static final int REQUEST_FILE_CHOOSER = 10001;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#F6F4EE"));

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgress(1);
        progressBar.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));
        root.addView(progressBar);

        webView = new WebView(this);
        webView.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        configureWebView();
        root.addView(webView);

        setContentView(root);

        String start = START_URL;
        Uri data = getIntent() != null ? getIntent().getData() : null;
        if (data != null && HOME_HOST.equals(data.getHost())) {
            String path = data.getPath();
            start = (path == null || path.isEmpty()) ? START_URL : data.toString();
        }
        webView.loadUrl(start);
    }

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setSupportMultipleWindows(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        s.setUserAgentString(s.getUserAgentString() + " XuanHuangApp/2.1.0");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            @SuppressWarnings("deprecation")
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri u = Uri.parse(url);
                String host = u.getHost();
                if (host == null || host.equals(HOME_HOST) || host.endsWith("." + HOME_HOST)) {
                    return false;
                }
                if (url.startsWith("http")) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, u));
                    } catch (ActivityNotFoundException ignored) {}
                }
                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                progressBar.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog,
                    boolean isUserGesture, Message resultMsg) {
                WebView newView = new WebView(MainActivity.this);
                newView.getSettings().setJavaScriptEnabled(true);
                newView.getSettings().setDomStorageEnabled(true);
                newView.setWebViewClient(new WebViewClient() {
                    @Override
                    @SuppressWarnings("deprecation")
                    public void onPageStarted(WebView v, String url, android.graphics.Bitmap f) {
                        if (url != null && !url.isEmpty() && MainActivity.this.webView != null) {
                            MainActivity.this.webView.loadUrl(url);
                        }
                        v.destroy();
                    }
                });
                WebView.WebViewTransport t = (WebView.WebViewTransport) resultMsg.obj;
                t.setWebView(newView);
                resultMsg.sendToTarget();
                return true;
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> request.grant(request.getResources()));
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin,
                    GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
            }

            @Override
            public boolean onShowFileChooser(WebView wv, ValueCallback<Uri[]> cb,
                    FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = cb;
                Intent intent = params.createIntent();
                try {
                    startActivityForResult(intent, REQUEST_FILE_CHOOSER);
                } catch (ActivityNotFoundException e) {
                    filePathCallback = null;
                    return false;
                }
                return true;
            }
        });

        webView.setDownloadListener((url, userAgent, contentDisposition, mimetype, contentLength) -> {
            try {
                String filename = URLUtil.guessFileName(url, contentDisposition, mimetype);
                DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                req.setMimeType(mimetype);
                req.addRequestHeader("User-Agent", userAgent);
                req.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);
                req.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                dm.enqueue(req);
                Toast.makeText(MainActivity.this, "开始下载：" + filename, Toast.LENGTH_SHORT).show();
            } catch (Exception e) {
                Toast.makeText(MainActivity.this, "下载失败", Toast.LENGTH_SHORT).show();
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == REQUEST_FILE_CHOOSER) {
            if (filePathCallback != null) {
                Uri[] results = null;
                if (resultCode == RESULT_OK && data != null) {
                    String ds = data.getDataString();
                    if (ds != null) {
                        results = new Uri[]{ Uri.parse(ds) };
                    } else if (data.getClipData() != null) {
                        int n = data.getClipData().getItemCount();
                        results = new Uri[n];
                        for (int i = 0; i < n; i++) {
                            results[i] = data.getClipData().getItemAt(i).getUri();
                        }
                    }
                }
                filePathCallback.onReceiveValue(results);
                filePathCallback = null;
            }
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView != null && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.loadUrl("about:blank");
            webView.removeAllViews();
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
'''

APP_BUILD_GRADLE = r'''
plugins {
    id 'com.android.application'
}

android {
    namespace 'cn.yexingchen.app'
    compileSdkVersion 36
    defaultConfig {
        applicationId 'cn.yexingchen.app'
        minSdkVersion 21
        targetSdkVersion 36
        versionCode 3
        versionName '2.1.0'
    }
    signingConfigs {
        release {
            storeFile file('%s')
            storePassword '%s'
            keyAlias '%s'
            keyPassword '%s'
        }
    }
    buildTypes {
        release {
            minifyEnabled false
            signingConfig signingConfigs.release
        }
        debug {
            signingConfig signingConfigs.release
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
    lintOptions {
        checkReleaseBuilds false
        abortOnError false
    }
}
''' % (apk_env["KEYSTORE_PATH"], apk_env["KEYSTORE_PASS"], apk_env["KEYSTORE_ALIAS"], apk_env["KEYSTORE_PASS"])

ROOT_BUILD_GRADLE = r'''
buildscript {
    repositories { google(); mavenCentral() }
    dependencies { classpath 'com.android.tools.build:gradle:8.9.1' }
}
allprojects { repositories { google(); mavenCentral() } }
task clean(type: Delete) { delete rootProject.buildDir }
'''

SETTINGS = r'''rootProject.name = 'yexingchen'
include ':app'
'''

GRADLE_PROPS = r'''android.useAndroidX=true
android.nonTransitiveRClass=true
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
'''

MANIFEST = r'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="cn.yexingchen.app">
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
    <uses-permission android:name="android.permission.CAMERA"/>
    <uses-permission android:name="android.permission.RECORD_AUDIO"/>
    <uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS"/>
    <uses-permission android:name="android.permission.VIBRATE"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="28"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="28"/>
    <application
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="true"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="false">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTask"
            android:configChanges="orientation|screenSize|screenLayout|keyboard|keyboardHidden|smallestScreenSize|uiMode|locale|layoutDirection">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>
'''

STRINGS = r'''<resources>
    <string name="app_name">玄黄</string>
</resources>
'''

THEMES = r'''<resources>
    <style name="AppTheme" parent="android:Theme.Material.Light.NoActionBar">
        <item name="android:colorPrimary">#10140F</item>
        <item name="android:colorPrimaryDark">#10140F</item>
        <item name="android:colorAccent">#caa466</item>
        <item name="android:windowBackground">#10140F</item>
        <item name="android:statusBarColor">#10140F</item>
        <item name="android:navigationBarColor">#10140F</item>
        <item name="android:windowLightStatusBar">false</item>
        <item name="android:windowLightNavigationBar">false</item>
    </style>
</resources>
'''

files = {
    "settings.gradle": SETTINGS,
    "build.gradle": ROOT_BUILD_GRADLE,
    "gradle.properties": GRADLE_PROPS,
    "app/build.gradle": APP_BUILD_GRADLE,
    "app/src/main/AndroidManifest.xml": MANIFEST,
    "app/src/main/java/cn/yexingchen/app/MainActivity.java": MAIN_JAVA,
    "app/src/main/res/values/strings.xml": STRINGS,
    "app/src/main/res/values/themes.xml": THEMES,
}

t = paramiko.Transport((ssh_cfg["HOST"], int(ssh_cfg["PORT"])))
t.connect(username=ssh_cfg["USER"], password=ssh_cfg["PASSWORD"])

def cexec(cmd, timeout=600):
    ch = t.open_session(); ch.settimeout(timeout); ch.exec_command(cmd); out = b""
    while True:
        if ch.recv_ready(): out += ch.recv(8192)
        if ch.exit_status_ready():
            while ch.recv_ready(): out += ch.recv(8192)
            break
    code = ch.recv_exit_status(); ch.close()
    return code, out.decode(errors="replace")

PROJ = "/opt/android-build/webview/yexingchen"
APK_SRC = "/var/www/yexingchen/dist/download/yexingchen-1.0.0.apk"
TWA = "/opt/android-build/twa/yexingchen"

print("== 1/6 准备工程目录并上传源码 ==")
base_cmd = "rm -rf %s && mkdir -p %s/{app/src/main/java/cn/yexingchen/app,app/src/main/res/values,app/src/main/res/mipmap,app/src/main/res/mipmap-xxxhdpi,gradle/wrapper}" % (PROJ, PROJ)
print(cexec(base_cmd)[1])
sftp = paramiko.SFTPClient.from_transport(t)
for rel, content in files.items():
    # 先用占位上传到临时，再 base64 精确写（避免引号/编码问题）
    enc = base64.b64encode(content.encode("utf-8")).decode()
    path = "%s/%s" % (PROJ, rel)
    sftp.posix_rename if hasattr(sftp, "posix_rename") else None
    import io
    with sftp.open(path, "wb") as f:
        f.write(content.encode("utf-8"))
print("上传 %d 个源码文件完成" % len(files))

print("== 2/6 复用 gradle wrapper（从 TWA 工程）==")
print(cexec("cp %s/gradlew %s/gradlew && cp -r %s/gradle/wrapper/. %s/gradle/wrapper/ && chmod +x %s/gradlew" % (TWA, PROJ, TWA, PROJ, PROJ))[1])

print("== 3/6 生成 launcher 图标（本地烘焙 app-icon 设计稿 → 各密度 mipmap）==")
from io import BytesIO
from PIL import Image
_icon_src = os.path.join(os.path.dirname(__file__), "apk-icon", "app-icon-1024.png")
# Android res 各密度图标规格（px）：mdpi48 / hdpi72 / xhdpi96 / xxhdpi144 / xxxhdpi192
_dens = {"mipmap-mdpi": 48, "mipmap-hdpi": 72, "mipmap-xhdpi": 96,
         "mipmap-xxhdpi": 144, "mipmap-xxxhdpi": 192}
for _d_res, _d_px in _dens.items():
    _icon = Image.open(_icon_src).convert("RGBA").resize((_d_px, _d_px), Image.LANCZOS)
    _buf = BytesIO(); _icon.save(_buf, "PNG")
    _dir = "%s/app/src/main/res/%s" % (PROJ, _d_res)
    cexec("mkdir -p %s" % _dir)
    with sftp.open("%s/ic_launcher.png" % _dir, "wb") as _f:
        _f.write(_buf.getvalue())
print("icon baked from %s" % _icon_src)

print("== 4/6 gradle assembleRelease ==")
code, out = cexec(
    "cd %s && export ANDROID_HOME=/opt/android-build && "
    "export JAVA_HOME=%s && export PATH=$JAVA_HOME/bin:$PATH && "
    "./gradlew --no-daemon assembleRelease -x lint 2>&1 | tail -40" % (PROJ, apk_env["JDK17_HOME"]), timeout=900)
print(out)
print("BUILD_CODE=%s" % code)
outapk = "%s/app/build/outputs/apk/release/app-release.apk" % PROJ
print("== 5/6 校验产物 ==")
print(cexec("ls -la %s 2>&1; %s/aapt dump badging %s 2>&1 | grep -E 'package:|sdkVersion|application-label:|launchable-activity' | head; "
            "export JAVA_HOME=%s; %s/bin/java -jar %s verify --print-certs %s 2>&1 | grep -iE 'SHA-256 digest'" %
            (outapk, apk_env["ANDROID_BUILD_TOOLS_DIR"], outapk, apk_env["JDK17_HOME"],
             apk_env["JDK17_HOME"], apk_env["APKSIGNER_JAR"], outapk))[1])

print("== 6/6 部署新 APK + 更新下载页 ==")
VER = "yexingchen-2.1.0.apk"
print(cexec("cp %s /var/www/yexingchen/dist/download/%s && "
            "chmod 644 /var/www/yexingchen/dist/download/%s && "
            "python3 - <<'PY'\n"
            "import re\n"
            "p='/var/www/yexingchen/dist/download/index.html'\n"
            "s=open(p,encoding='utf-8').read()\n"
            "s=re.sub(r'yexingchen-[0-9.]+\\\\.apk','%s',s)\n"
            "open(p,'w',encoding='utf-8').write(s)\n"
            "PY\n"
            "grep -o 'yexingchen-[0-9.]*\\\\.apk' /var/www/yexingchen/dist/download/index.html | head -3" % (outapk, VER, VER, VER))[1])
print("curl 验证：")
print(cexec("curl -s -o /dev/null -w 'download_page=%%{http_code}\\n' https://yexingchen.cn/download/")[1])
print(cexec("curl -s -o /dev/null -w 'new_apk=%%{http_code}\\n' https://yexingchen.cn/download/%s" % VER)[1])
t.close()