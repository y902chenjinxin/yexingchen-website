# 鸿蒙 NEXT（HarmonyOS 5.0+）HAP 构建指南

> 目标：把 `harmony/` 下的 ArkTS 工程打成 `.hap`，上传到 `yexingchen.cn/download/`，
> 下载页会自动识别并把它显示成「可下载」。

---

## 0. 先搞清楚为什么需要 HAP

| 系统 | 能不能装 APK | 说明 |
|------|--------------|------|
| 安卓 | ✅ | 现有的 `yexingchen-2.1.0.apk` |
| **鸿蒙 4 及以下** | ✅ | 内核仍是 AOSP，APK 直接装 |
| **鸿蒙 NEXT（5.0+ 纯血鸿蒙）** | ❌ | 移除了 AOSP 兼容层，**只认 `.hap`** |

所以「鸿蒙安装包」= 给鸿蒙 NEXT 用的 `.hap`。鸿蒙 4 用户不用管这一节。

---

## 1. 前置：华为开发者账号

- 注册地址：<https://developer.huawei.com/consumer/cn/>
- 个人开发者**免费**注册即可，实名认证需要身份证
- 下载 DevEco Studio 也必须先登录这个账号

> 不需要企业认证、不需要上架应用市场。我们要的只是「签名证书」，让 HAP 能在自己的设备上装。

---

## 2. 装 DevEco Studio（Windows）

1. 下载页：<https://developer.huawei.com/consumer/cn/deveco-studio/>
2. 选 **Windows** 版，要求 **DevEco Studio 5.0 或更高**（对应 HarmonyOS NEXT / API 12+）
3. 安装时勾选 **HarmonyOS SDK**（默认会带上）
4. 首次启动会引导安装 SDK，按默认走即可

验证装好了：

```bash
# DevEco 自带命令行工具，路径按实际安装位置调整
"C:\Program Files\Huawei\DevEco Studio\tools\hvigor\bin\hvigorw.bat" --version
```

---

## 3. 打开工程

DevEco Studio → **Open** → 选中仓库里的 **`harmony/`** 目录（注意：是 `harmony/`，不是 `harmony/entry/`）。

首次打开会自动跑 `ohpm install` + 同步。如果提示 SDK 版本不匹配，按提示点 **Sync Now**。

工程结构：

```
harmony/
├── AppScope/
│   ├── app.json5                 # 包名 cn.yexingchen.app、版本号
│   └── resources/base/media/app_icon.png
├── entry/
│   ├── src/main/
│   │   ├── ets/
│   │   │   ├── entryability/EntryAbility.ets   # Ability，只负责起窗口
│   │   │   └── pages/Index.ets                 # ★ WebView 壳主页面
│   │   ├── resources/
│   │   └── module.json5          # 权限 / 图标 / 入口声明
│   └── build-profile.json5
└── build-profile.json5           # SDK 版本、构建模式
```

**要改的东西基本都在 `entry/src/main/ets/pages/Index.ets`**。

---

## 4. 配签名（关键一步）

### 方式 A：自动签名（推荐，最省事）

1. 手机开 **开发者模式**（设置 → 关于本机 → 连点版本号 7 次）
2. 开 **USB 调试**，用数据线连电脑
3. DevEco Studio → **File → Project Structure → Signing Configs**
4. 勾选 **Automatically generate signature**
5. 按提示登录华为开发者账号 → 点 **Sign In** / **OK**

DevEco 会自动去 AGC 申请调试证书并写入 `build-profile.json5` 的 `signingConfigs`，同时把设备加进调试设备列表。

> ⚠️ 自动签名要求**至少连一次真机**——它需要读取设备 UDID 去注册调试设备。

### 方式 B：手动签名（不连设备也能签名，适合 CI）

1. 登录 **AGC 控制台** → 我的项目 → 创建项目
2. **证书、App ID 和 Profile** 里依次生成：
   - `.p12`（密钥库，密码自己设）
   - `.cer`（证书）
   - `.p7b`（Profile，需先建好 App ID `cn.yexingchen.app`）
3. DevEco → Signing Configs → 取消勾选自动 → 手动指定上面三个文件、Profile 名、密码

---

## 5. 出包

### 真机调试（先跑通再说）

点顶部 **▶ Run**，选已连接的鸿蒙 NEXT 设备。装好后桌面出现「玄黄」，
点开应直接进 `yexingchen.cn/workbench`。

### 出正式 HAP

**图形界面**：`Build → Build Hap(s)/APP(s) → Build Hap(s)`

**命令行**（在 `harmony/` 目录下）：

```bash
hvigorw assembleHap --mode module -p product=default -p buildMode=release --no-daemon
```

产物路径：

```
harmony/entry/build/default/outputs/default/entry-default-signed.hap
```

> 文件名带 `-signed` 的才是能装的。`-unsigned` 那个装不上。
> 构建完可以双击 HAP 用 DevEco 的「Device File Browser」推送到设备验证。

---

## 6. 上传到服务器，下载页自动识别

```bash
# 1) 传到服务器下载目录（文件名建议带版本号）
scp harmony/entry/build/default/outputs/default/entry-default-signed.hap \
    root@203.195.208.25:/var/www/yexingchen/dist/download/yexingchen-harmony-1.0.0.hap

# 2) 重写下载页（会自动扫描 .hap，把它显示成「可下载」）
backend/.venv/Scripts/python.exe scripts/deploy_download_page.py

# 3) 验证
curl -s -o /dev/null -w '%{http_code}\n' https://yexingchen.cn/download/yexingchen-harmony-1.0.0.hap
curl -s https://yexingchen.cn/download/ | grep -o 'yexingchen-harmony[^"]*'
```

**下载页不需要改代码**：`write_download_page()` 每次生成前都会扫一遍下载目录里的 `*.hap`，
有就显示下载按钮 + SHA-256，没有就显示「待构建」+ 临时用浏览器添加到桌面的说明。

---

## 7. 常见坑

| 现象 | 原因 / 解法 |
|------|-------------|
| `hvigorw` 找不到 | 用 DevEco 安装目录下的绝对路径，或把 `tools/hvigor/bin` 加进 PATH |
| 自动签名按钮是灰的 | 没连真机 / 没登录华为账号 / 没开 USB 调试 |
| 安装报 `signature verify failed` | 用了 `-unsigned` 的包，或设备不在调试设备列表里 |
| 装到设备提示「不受信任」 | 调试签名有效期短，正式分发要么上架华为应用市场，要么用正式 Profile |
| 真机跑起来白屏 | 检查手机能不能访问 `yexingchen.cn`；看 DevEco 的 Log 面板过滤 `XuanHuang` |
| 构建报 SDK 版本不匹配 | `harmony/build-profile.json5` 里 `compatibleSdkVersion` 改成你装到的版本 |
| ArkTS 编译报某 API 签名不符 | 见下面「代码说明」——SDK 小版本间 API 偶有微调，按 IDE 提示改即可 |

---

## 8. 代码说明 & 已知差异

### ArkTS 源码是照着 API 12 文档写的，但**没有在本机编译验证过**

本机没有 HarmonyOS SDK（DevEco 是 Windows GUI 工具，需你本地安装），
所以 `Index.ets` 里可能有个别 API 因为 SDK 小版本差异需要微调。
第一处最可能要动的是 `onWindowNew` 里的 `event.handler.setWebController(null)`。
DevEco 会直接标红并给出正确签名，按提示改就行。

### 与安卓壳的行为对照

| 能力 | 安卓壳 | 鸿蒙壳 |
|------|--------|--------|
| 首页 `/workbench` | ✅ | ✅ |
| 站内留 App / 站外跳浏览器 | ✅ | ✅ |
| `target=_blank` 回站内加载 | ✅ | ✅ |
| 返回键 Web 后退 | ✅ | ✅ |
| 文件上传选择器 | ✅ | ✅ |
| 媒体免手势播放 | ✅ | ✅ |
| 混合内容放行 | ✅ | ✅ |
| **文件下载接管** | ✅ DownloadManager | ❌ **未实现** |
| **UA 追加 App 标识** | ✅ `XuanHuangApp/2.1.0` | ❌ 未追加 |
| **URL 唤起 App（Deep Link）** | ✅ | ❌ 未配置 |

三项差异都**不影响主流程**：

- **下载**：网页里点「下载文件」类链接目前没反应。要补的话在 `Index.ets` 里给
  `this.controller.setDownloadDelegate(...)` 挂一个 `WebDownloadDelegate`，把文件落盘到沙箱再提示用户。
- **UA 标识**：站点目前没有依赖这个标识，纯标识用途。要加的话在 `Web` 组件上设 `.userAgent(...)`，
  但 ArkWeb 的「取默认 UA 再追加」API 在不同 SDK 版本上有出入，建议装好 SDK 后查一下再写。
- **Deep Link**：安卓壳支持从别的 App 跳到 `yexingchen.cn/xxx` 并带上路径。鸿蒙要做需要在
  `module.json5` 的 `skills` 里加 `uris` 配置。

---

## 9. 版本号维护

改版本号要动两处（HarmonyOS 和安卓各自的版本是独立的）：

- `harmony/AppScope/app.json5` → `versionCode` / `versionName`
- HAP 文件名建议带版本，如 `yexingchen-harmony-1.0.0.hap`

`versionCode` 是整数，每次发版必须递增，否则设备拒绝覆盖安装。
