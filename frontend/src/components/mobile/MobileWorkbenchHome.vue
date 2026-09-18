<template>
  <section class="abb" aria-label="主页">
    <!-- 顶部：几何 Logo + 品牌 + AI 胶囊 -->
    <header class="abb-top">
      <div class="abb-brand" @click="go('/workbench')" aria-label="玄黄">
        <span class="abb-logo" aria-hidden="true">
          <span class="abb-logo__l"></span>
          <span class="abb-logo__r"></span>
        </span>
        <span class="abb-title">玄黄</span>
      </div>
      <button class="abb-ai" @click="go('/assistant')" aria-label="AI 对话">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/></svg>
        <span>AI</span>
      </button>
    </header>

    <!-- 数据总览：首屏只放可行动的数据，不放装饰性趋势占位 -->
    <div class="abb-hero glass-card" aria-label="数据总览">
      <div class="abb-hero__lab">本月净流入</div>
      <div class="abb-hero__num">{{ fmtMoney(monthNet) }}</div>
      <div class="abb-hero__sub">
        <span>本月收入 <b :class="income > 0 ? 'up' : undefined">{{ fmtMoney(income) }}</b></span>
        <span>本月支出 <b :class="expense > 0 ? 'dn' : undefined">{{ fmtMoney(expense) }}</b></span>
      </div>
    </div>

    <div class="abb-stats" aria-label="关键数据">
      <div class="abb-stat">
        <span class="abb-stat__label">流水笔数</span>
        <strong>{{ count ?? '—' }}</strong>
        <small>本月记录</small>
      </div>
      <div class="abb-stat">
        <span class="abb-stat__label">持仓盈亏</span>
        <strong :class="{ positive: stockPnl > 0, negative: stockPnl < 0 }">{{ fmtPnl(stockPnl) }}</strong>
        <small>今日变化</small>
      </div>
      <div class="abb-stat">
        <span class="abb-stat__label">已接入</span>
        <strong>8</strong>
        <small>个功能模块</small>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="abb-sec">
      <h2 class="abb-sec__title">快捷入口</h2>
      <div class="abb-grid">
        <button
          v-for="(m, i) in quick"
          :key="m.path"
          class="abb-cell"
          :style="{ '--c': 'var(' + m.acc + ')', '--d': (i % 4) + 'ms' }"
          @click="go(m.path)"
          :aria-label="m.label"
        >
          <span class="abb-cell__ico" aria-hidden="true" v-html="m.icon"></span>
          <span class="abb-cell__lab">{{ m.label }}</span>
        </button>
      </div>
    </div>


  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { financeApi } from '@/api/finance'
import { stocksApi } from '@/api/stocks'

const router = useRouter()

/* 快捷入口：线性描边图标 + 模块语义色（工具已含：证件照/倒计时） */
const ICONS = {
  music: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="7.5"/><path d="M9.5 9.5 14.5 12l-5 2.5z"/></svg>',
  notes: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h14v16H5z"/><path d="M9 9h6M9 13h6M9 17h3"/></svg>',
  finance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 5V3.5A1 1 0 0 1 9 2.5h6a1 1 0 0 1 1 1V5"/><path d="M8 12h8M8 16h5"/></svg>',
  stocks: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18l5-6 3 3 8-9"/><path d="M15 6h5v5"/></svg>',
  travels: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c3.5 2 6 5 6 9a6 6 0 0 1-12 0c0-4 2.5-7 6-9z"/><path d="M9.5 19h5"/></svg>',
  contacts: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7-4.5-7-10a7 7 0 0 1 14 0c0 5.5-7 10-7 10z"/><circle cx="12" cy="10" r="2.4"/></svg>',
  idphoto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="4" width="14" height="16" rx="3"/><circle cx="12" cy="10" r="2.6"/><path d="M8.5 18c.8-2.3 2.2-3.4 3.5-3.4s2.7 1.1 3.5 3.4"/></svg>',
  countdown: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13" r="7"/><path d="M12 9v4l2.6 1.5"/><path d="M9 3h6M12 3v1.5"/></svg>',
}

/* 快捷宫格（3 列），带可达性过滤；工具以证件照/倒计时独立暴露 */
const QUICK = [
  { label:'音乐',   path:'/music',   acc:'--ab-blu', icon:ICONS.music },
  { label:'笔记',   path:'/notes',   acc:'--ab-pur', icon:ICONS.notes },
  { label:'记账',   path:'/finance', acc:'--ab-grn', icon:ICONS.finance },
  { label:'股票',   path:'/stocks',  acc:'--ab-cor', icon:ICONS.stocks },
  { label:'足迹',   path:'/travels', acc:'--ab-cyn', icon:ICONS.travels },
  { label:'通讯录', path:'/contacts',acc:'--ab-amb', icon:ICONS.contacts },
  { label:'证件照', path:'/tool/idphoto', acc:'--ab-cyn', icon:ICONS.idphoto },
  { label:'倒计时', path:'/tool/countdown', acc:'--ab-vio', icon:ICONS.countdown },
]
const quick = QUICK

const income = ref(null)
const expense = ref(null)
const count = ref(null)
const stockPnl = ref(null)

const monthNet = computed(() => income.value === null || expense.value === null ? null : income.value - expense.value)
const fmtMoney = (v) => v === null || v === undefined ? '—' : '¥ ' + Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const fmtPnl = (v) => v === null || v === undefined ? '—' : (Number(v) > 0 ? '+' : '') + Number(v).toFixed(2) + '%'

function go(path) {
  try { if (navigator && navigator.vibrate) navigator.vibrate(6) } catch {}
  router.push(path)
}

onMounted(async () => {
  try {
    const res = await financeApi.summary()
    const d = res?.data
    if (d) {
      income.value = d.month_income ?? d.income ?? null
      expense.value = d.month_expense ?? d.expense ?? null
      count.value = d.month_count ?? d.count ?? null
    }
  } catch { /* 未就绪保持占位 */ }
  try {
    const res = await stocksApi.dashboard()
    const t = res?.data?.today_pnl
    if (typeof t === 'number') stockPnl.value = t
  } catch { /* 未就绪保持占位 */ }
})
</script>

<style scoped>
.abb {
  position: relative;
  min-height: 100svh;
  padding: calc(env(safe-area-inset-top, 0px) + 16px) 16px calc(40px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
  overflow-x: hidden;
  background:
    radial-gradient(120% 72% at 18% 0%, rgba(124, 141, 255, 0.14), transparent 58%),
    radial-gradient(90% 56% at 88% 24%, rgba(139, 92, 246, 0.10), transparent 55%);
}

/* 顶部品牌行 */
.abb-top { display: flex; align-items: center; justify-content: space-between; padding: 6px 2px 2px; }
.abb-brand { display: flex; align-items: center; gap: 10px; border: none; background: none; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.abb-logo {
  position: relative; width: 28px; height: 28px; border-radius: 8px; overflow: hidden;
  box-shadow: 0 6px 14px rgba(80, 95, 200, 0.30), inset 0 1px 0 rgba(255,255,255,.4);
}
.abb-logo__l { position: absolute; inset: 0; transform: skewX(-18deg); transform-origin: top left; left: -4%; width: 115%;
  background: linear-gradient(150deg, var(--lj-dai, #5b6ae0), var(--lj-seal, #8b5cf6)); }
.abb-logo__r { position: absolute; inset: 0; transform: skewX(18deg); transform-origin: top right; right: -10%; width: 118%;
  background: linear-gradient(150deg, var(--lj-ochre, #5b6ae0), var(--color-accent, #8b5cf6)); opacity: .9; }
.abb-title {
  font-size: 20px; font-weight: 800; letter-spacing: .16em; color: var(--lj-text, #0f1530);
}

.abb-ai {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 8px 15px; border-radius: 999px; border: none; cursor: pointer;
  color: #fff; font-size: 13px; font-weight: 600;
  background: linear-gradient(135deg, var(--lj-dai, #5b6ae0), var(--color-accent, #8b5cf6));
  box-shadow: 0 8px 18px rgba(100, 110, 230, 0.28), inset 0 1px 0 rgba(255,255,255,.28);
  transition: transform .18s;
  -webkit-tap-highlight-color: transparent;
}
.abb-ai:active { transform: scale(.94); }
.abb-ai svg { width: 15px; height: 15px; }

/* 今日速览 Hero */
.abb-hero {
  margin-top: 22px; padding: 20px 18px; border-radius: 24px;
  animation: rise .5s cubic-bezier(.2,.8,.2,1) both;
  transition: transform .18s;
}
.abb-hero:active { transform: scale(.98); }
.abb-hero__lab { font-size: 12px; letter-spacing: .06em; color: var(--ls-text-2, #5b6b8a); }
.abb-hero__num {
  margin-top: 6px; font-size: 34px; font-weight: 800; font-variant-numeric: tabular-nums;
  letter-spacing: .01em; color: var(--ls-text, #0f1530);
}
.abb-hero__sub { display: flex; gap: 18px; margin-top: 8px; font-size: 12.5px; color: var(--ls-text-3, #8a8f98); }
.abb-hero__sub b { font-weight: 700; }
.abb-hero__sub .up { color: var(--pnl-up, #e5484d); }
.abb-hero__sub .dn { color: var(--pnl-down, #1aa86a); }

/* 快捷入口 */
.abb-sec { margin-top: 28px; }
.abb-sec__title {
  margin: 0 0 12px; font-size: 13px; font-weight: 600; letter-spacing: .12em;
  color: var(--ls-text-3, #8a8f98);
}
.abb-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.abb-cell {
  display: flex; flex-direction: column; align-items: center; gap: 9px;
  padding: 18px 4px 13px; border-radius: 20px; border: 1px solid transparent;
  background: var(--lj-glass, rgba(255,255,255,.66));
  -webkit-backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.65);
  cursor: pointer;
  animation: rise .45s cubic-bezier(.2,.8,.2,1) both;
  animation-delay: calc(var(--d) * 0.03s);
  transition: transform .16s, box-shadow .2s;
  -webkit-tap-highlight-color: transparent;
}
@media (prefers-reduced-motion: reduce) { .abb-cell { animation: none; } }
.abb-cell:active { transform: scale(.96); box-shadow: inset 0 1px 0 rgba(255,255,255,.5), 0 4px 16px rgba(80,95,200,.14); }
.abb-cell__ico { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: var(--c); }
.abb-cell__ico svg { width: 26px; height: 26px; }
.abb-cell__lab { font-size: 12px; font-weight: 500; color: var(--lj-text-2, #5b6b8a); letter-spacing: .01em; }

/* 本月趋势数据带 */
.abb-trend {
  margin-top: 22px; padding: 14px 16px; border-radius: 20px;
  display: flex; align-items: center; justify-content: space-between; gap: 14px;
}
.abb-trend__lab { font-size: 12px; color: var(--ls-text-3, #8a8f98); }
.abb-trend__right { display: flex; align-items: center; gap: 14px; }
.abb-trend__val { font-size: 15px; font-weight: 700; color: var(--lj-dai, #5b6ae0); font-variant-numeric: tabular-nums; }
.abb-trend__bar { display: flex; align-items: flex-end; gap: 5px; height: 26px; }
.abb-trend__bar i {
  flex: 1; width: 2px; border-radius: 2px;
  background: linear-gradient(180deg, var(--lj-dai, #5b6ae0), var(--color-accent, #8b5cf6));
  opacity: .85;
}

@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
</style>
