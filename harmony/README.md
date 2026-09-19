# 玄黄 · 鸿蒙 NEXT 客户端

HarmonyOS NEXT（5.0+ 纯血鸿蒙）的 **WebView 壳** App。只有 `entry/src/main/ets/pages/Index.ets`
这一个页面有实质逻辑：它承载 <https://yexingchen.cn>，站点更新无需重新发版。

- **包名**：`cn.yexingchen.app`（与安卓包名相同，但两个生态互不冲突）
- **首屏**：`https://yexingchen.cn/workbench`
- **行为对齐**：安卓壳 `MainActivity.java`（站外跳浏览器、返回键后退、文件上传等）

## 构建

完整步骤见 **[docs/HARMONYOS_BUILD.md](../docs/HARMONYOS_BUILD.md)**（注册华为开发者账号 → 装 DevEco Studio → 配签名 → 出 HAP → 上传）。

速查：

```
DevEco Studio → Open → 选择本目录（harmony/）
File → Project Structure → Signing Configs → Automatically generate signature（需连真机）
Build → Build Hap(s)/APP(s) → Build Hap(s)
产物：entry/build/default/outputs/default/entry-default-signed.hap
```

出包后上传到服务器下载目录即可，下载页会自动识别：

```bash
scp entry/build/default/outputs/default/entry-default-signed.hap \
    root@203.195.208.25:/var/www/yexingchen/dist/download/yexingchen-harmony-1.0.0.hap
```

## 为什么不用 APK

鸿蒙 4 及以下是 AOSP 内核，用安卓的 APK 就行；鸿蒙 NEXT 移除了 AOSP 兼容层，
只认 `.hap`，所以必须单独做一个包。

## 注意

`Index.ets` 是照着 HarmonyOS API 12 文档写的，**未在本机编译验证**（本机没装 HarmonyOS SDK）。
用 DevEco 打开后如有个别 API 签名报错，按 IDE 提示微调即可——最可能要动的是
`onWindowNew` 里的 `event.handler.setWebController(null)`。详见指南第 8 节「代码说明 & 已知差异」。
