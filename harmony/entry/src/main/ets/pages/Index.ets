/**
 * 玄黄 · 鸿蒙 NEXT 客户端主页面
 *
 * 这是一个「WebView 壳」：App 本体只负责承载 https://yexingchen.cn，
 * 站点更新时无需重新发版。
 *
 * 行为刻意与安卓壳（android-project MainActivity.java）保持一致：
 *   1. 首页 /workbench
 *   2. 站内链接留在 App 内，站外 http(s) 交给系统浏览器
 *   3. target=_blank / window.open 不新开窗口，改由当前 Web 加载
 *   4. 返回键优先让 Web 后退，退无可退才退出 App
 *   5. 网页里的 <input type="file"> 走系统文件选择器（账本导入用得到）
 *   6. 媒体不要求用户手势即可播放（对应安卓 mediaPlaybackRequiresUserGesture(false)）
 *   7. 混合内容放行（站点有跨域字体/图标）
 *
 * 注意：安卓壳里还有 DownloadManager 下载接管，鸿蒙这版暂未接下载代理
 *      （Web 内点击文件下载链接目前无响应）。见 docs/HARMONYOS_BUILD.md「已知差异」。
 */
import { webview } from '@kit.ArkWeb';
import { common } from '@kit.AbilityKit';
import { picker } from '@kit.CoreFileKit';
import { url } from '@kit.ArkTS';
import { BusinessError } from '@kit.BasicServicesKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const DOMAIN: number = 0x0001;
const TAG: string = 'XuanHuang';

/** App 启动页：与安卓壳 START_URL 相同 */
const START_URL: string = 'https://yexingchen.cn/workbench';
/** 视为「站内」的域名；子域名同样算站内 */
const HOME_HOST: string = 'yexingchen.cn';

/** 判断是否为站内地址。解析失败按站外处理，避免把异常 URL 塞进 Web。 */
function isInternalUrl(raw: string): boolean {
  let host: string = '';
  try {
    host = new url.URL(raw).hostname;
  } catch (e) {
    return false;
  }
  return host === HOME_HOST || host.endsWith('.' + HOME_HOST);
}

@Entry
@Component
struct Index {
  private controller: webview.WebviewController = new webview.WebviewController();
  private ctx: common.UIAbilityContext = getContext(this) as common.UIAbilityContext;

  /** 顶部细进度条，对应安卓壳的 ProgressBar */
  @State progress: number = 0;
  @State isLoading: boolean = true;

  /** 首屏加载失败时的兜底界面 */
  @State hasError: boolean = false;
  @State errorText: string = '';

  build() {
    Stack() {
      Column() {
        if (this.isLoading) {
          Progress({ value: this.progress, total: 100, type: ProgressType.Linear })
            .width('100%')
            .height(3)
            .color('#8E6A2C')
            .backgroundColor('#E8E2D6')
        }

        Web({ src: START_URL, controller: this.controller })
          .width('100%')
          .layoutWeight(1)
          // —— 与安卓 WebSettings 对齐 ——
          .javaScriptAccess(true)
          .domStorageAccess(true)
          .fileAccess(false)
          .imageAccess(true)
          .onlineImageAccess(true)
          .mixedMode(MixedMode.All)
          .zoomAccess(true)
          .mediaPlayGestureAccess(false)
          // —— 站内留 App、站外跳浏览器（对应 shouldOverrideUrlLoading）——
          .onLoadIntercept((event) => {
            if (!event) {
              return false;
            }
            const target: string = event.data.getRequestUrl();
            if (isInternalUrl(target)) {
              return false;
            }
            if (target.startsWith('http')) {
              this.openInBrowser(target);
              return true;
            }
            return false;
          })
          // —— target=_blank / window.open：不新开窗口，用当前 Web 打开（对应 onCreateWindow）——
          .multiWindowAccess(true)
          .onWindowNew((event) => {
            if (!event) {
              return;
            }
            this.controller.loadUrl(event.targetUrl);
            try {
              // 传 null 表示拒绝创建新窗口
              event.handler.setWebController(null);
            } catch (e) {
              hilog.warn(DOMAIN, TAG, 'refuse new window failed');
            }
          })
          // —— 进度与生命周期 ——
          .onPageBegin(() => {
            this.isLoading = true;
            this.hasError = false;
          })
          .onProgressChange((event) => {
            if (event) {
              this.progress = event.newProgress;
            }
          })
          .onPageEnd(() => {
            this.isLoading = false;
          })
          .onErrorReceive((event) => {
            // 只对主文档错误兜底，子资源（图片/字体）失败不打扰用户
            if (!event || !event.request.isMainFrame()) {
              return;
            }
            this.errorText = event.error.getErrorInfo();
            this.hasError = true;
            this.isLoading = false;
            hilog.error(DOMAIN, TAG, 'main frame load error: %{public}s', this.errorText);
          })
          // —— 网页文件上传（对应 onShowFileChooser）——
          .onShowFileSelector((event) => {
            const options = new picker.DocumentSelectOptions();
            options.maxSelectNumber = 1;
            const documentPicker = new picker.DocumentViewPicker(this.ctx);
            documentPicker.select(options)
              .then((uris: Array<string>) => {
                event.result.handleFileList(uris && uris.length > 0 ? uris : []);
              })
              .catch((err: BusinessError) => {
                hilog.error(DOMAIN, TAG, 'file picker failed: %{public}s', JSON.stringify(err));
                event.result.handleFileList([]);
              });
            return true;
          })
      }
      .width('100%')
      .height('100%')

      // 首屏加载失败兜底
      if (this.hasError) {
        Column({ space: 12 }) {
          Text('页面加载失败').fontSize(16).fontColor('#2C2C2A')
          Text(this.errorText).fontSize(12).fontColor('#8A8A85').textAlign(TextAlign.Center)
          Button('重试')
            .fontSize(14)
            .backgroundColor('#8E6A2C')
            .onClick(() => {
              this.hasError = false;
              this.isLoading = true;
              this.controller.loadUrl(START_URL);
            })
        }
        .width('78%')
        .padding(20)
        .backgroundColor('#FFFFFF')
        .borderRadius(14)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F6F4EE')
  }

  /**
   * 返回键处理（对应安卓 onKeyDown KEYCODE_BACK）：
   * Web 栈能后退就后退并吞掉事件，否则返回 false 交给系统退出 App。
   */
  onBackPress(): boolean {
    if (this.controller.accessBackward()) {
      this.controller.backward();
      return true;
    }
    return false;
  }

  /** 站外链接用系统浏览器打开。 */
  openInBrowser(target: string): void {
    try {
      this.ctx.startAbility({
        action: 'ohos.want.action.viewData',
        entities: ['entity.system.browsable'],
        uri: target
      }).catch((err: BusinessError) => {
        hilog.error(DOMAIN, TAG, 'open in browser failed: %{public}s', JSON.stringify(err));
      });
    } catch (e) {
      hilog.error(DOMAIN, TAG, 'open in browser exception');
    }
  }
}
