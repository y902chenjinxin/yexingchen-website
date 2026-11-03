<template>
  <slot v-if="ok" />
  <div v-else class="dg" role="alert">
    <div class="dg-box">
      <span class="dg-ico" aria-hidden="true">{{ need === 'phone' ? '📱' : '💻' }}</span>
      <b class="dg-title">{{ title || (need === 'phone' ? '请在手机上打开' : '请在电脑上打开') }}</b>
      <p class="dg-desc">{{ desc || defaultDesc }}</p>
      <div class="dg-acts">
        <slot name="actions" />
        <button v-if="showBack" class="dg-btn" type="button" @click="goBack">返回</button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 设备门槛（v2.46.347）
 *
 * 夜星：「3D 粒子只支持手机端打开，电脑端点击提示请在手机端打开」
 *       「拆站小游戏只支持电脑端打开，手机端点击提示请在电脑端打开」。
 *
 * 为什么要单独一个组件：这类"只能在某端用"的页面以后还会有
 * （音乐造物主是 PC-only、粒子是 phone-only），
 * 每个页面各写一遍提示文案和样式必然走样。
 *
 * 判定走 `useDevice.isPhoneDevice()`，**不是** `useIsMobile()` ——
 * 后者是"是否启用移动端外壳"的语义（手机浏览器返回 false），详见那个文件的注释。
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { isPhoneDevice } from '@/composables/useDevice'

const props = defineProps({
  /**
   * phone：只有手机能进；pc：只有电脑能进。
   *
   * 🔴 名字不能叫 `require` —— 那是 CommonJS 的全局变量，模板表达式里出现
   * 会被工具链当成未定义的全局调用，运行时直接 `ReferenceError: require is not defined`，
   * 而且报错位置在渲染函数的 Proxy getter 上，极难定位。
   */
  need: { type: String, default: 'phone' },
  title: { type: String, default: '' },
  desc: { type: String, default: '' },
  showBack: { type: Boolean, default: true },
})

const router = useRouter()

const ok = computed(() => (props.need === 'phone' ? isPhoneDevice() : !isPhoneDevice()))

const defaultDesc = computed(() =>
  props.need === 'phone'
    ? '这个功能需要多点触控和竖屏，电脑上体验不了。用手机打开这个页面就能玩。'
    : '这个功能需要键盘和大屏，请换到电脑上打开。',
)

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/workbench')
}
</script>

<style scoped>
.dg {
  min-height: 60vh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
}
.dg-box {
  max-width: 380px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  padding: 28px 24px;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
  background: color-mix(in srgb, currentColor 5%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.dg-ico { font-size: 40px; line-height: 1; }
.dg-title { font-size: 17px; font-weight: 700; letter-spacing: .01em; }
.dg-desc {
  margin: 0; font-size: 13px; line-height: 1.75; opacity: .7;
}
.dg-acts { display: flex; gap: 10px; margin-top: 6px; }
.dg-btn {
  height: 34px; padding: 0 18px; border-radius: 9px; cursor: pointer;
  border: 1px solid color-mix(in srgb, currentColor 22%, transparent);
  background: transparent; color: inherit;
  font: inherit; font-size: 13px; font-weight: 600;
  transition: background-color .15s;
}
.dg-btn:hover { background: color-mix(in srgb, currentColor 10%, transparent); }
</style>
