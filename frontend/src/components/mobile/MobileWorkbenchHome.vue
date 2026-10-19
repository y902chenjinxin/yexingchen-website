<template>
  <section class="abb" aria-label="主页">
    <!-- 顶部：几何 Logo + 品牌 -->
    <header class="abb-top">
      <div class="abb-brand" @click="go('/workbench')" aria-label="玄黄">
        <span class="abb-logo" aria-hidden="true">
          <span class="abb-logo__l"></span>
          <span class="abb-logo__r"></span>
        </span>
        <span class="abb-title">玄黄</span>
      </div>
    </header>

    <!-- 数据总览：首屏只放可行动的数据，不放装饰性趋势占位。
         原先主视觉是「本月净流入」大数字、下面再列收入与支出 —— 但净流入本身就是
         「收入 − 支出」，三项互相重复，与桌面账本同一个问题，故一并去掉，
         改为收入 / 支出两栏并列。 -->
    <div class="abb-hero glass-card" aria-label="数据总览" :style="{ transform: heroShift ? `translateY(${heroShift}px)` : '' }">
      <div class="abb-hero__pair">
        <div class="abb-hero__col">
          <div class="abb-hero__lab">本月收入</div>
          <div class="abb-hero__num up">{{ heroIncomeText }}</div>
        </div>
        <div class="abb-hero__col">
          <div class="abb-hero__lab">本月支出</div>
          <div class="abb-hero__num dn">{{ heroExpenseText }}</div>
        </div>
      </div>
    </div>

    <div class="abb-stats" aria-label="关键数据">
      <div class="abb-stat">
        <span class="abb-stat__label">流水笔数</span>
        <strong>{{ count ?? '—' }}</strong>
        <small>本月记录</small>
      </div>
      <div class="abb-stat">
        <span class="abb-stat__label">已接入</span>
        <strong>{{ quick.length }}</strong>
        <small>个功能模块</small>
      </div>
    </div>

    <!-- 快捷入口（精选）＋ 全部模块目录入口 -->
    <div class="abb-sec">
      <div class="abb-sec__head">
        <h2 class="abb-sec__title">快捷入口</h2>
        <button class="abb-more" @click="go('/modules')" aria-label="查看全部模块">全部模块 ›</button>
      </div>
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { financeApi } from '@/api/finance'
import countUp from '@/utils/games/countUp'
import { haptic } from '@/utils/haptic'
import { useMenusStore } from '@/stores/menus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const menus = useMenusStore()
const auth = useAuthStore()
/* v2.46.117 权限口径与 ModulesView 完全一致（超管判定抄 DesktopSidebar/ModulesView 现役写法） */
const isSuper = computed(() => auth.user?.role === 'super_admin' || auth.user?.is_super_admin === 1)
/* 非授权对象：工作台是主页，不参与角色菜单授权 */
const NAV_EXEMPT = new Set(['/workbench'])

/* 快捷入口：线性描边图标 + 模块语义色（工具已含：证件照/倒计时） */
const ICONS = {
  music: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="7.5"/><path d="M9.5 9.5 14.5 12l-5 2.5z"/></svg>',
  notes: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h14v16H5z"/><path d="M9 9h6M9 13h6M9 17h3"/></svg>',
  finance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 5V3.5A1 1 0 0 1 9 2.5h6a1 1 0 0 1 1 1V5"/><path d="M8 12h8M8 16h5"/></svg>',
  travels: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c3.5 2 6 5 6 9a6 6 0 0 1-12 0c0-4 2.5-7 6-9z"/><path d="M9.5 19h5"/></svg>',
  contacts: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7-4.5-7-10a7 7 0 0 1 14 0c0 5.5-7 10-7 10z"/><circle cx="12" cy="10" r="2.4"/></svg>',
  idphoto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="4" width="14" height="16" rx="3"/><circle cx="12" cy="10" r="2.6"/><path d="M8.5 18c.8-2.3 2.2-3.4 3.5-3.4s2.7 1.1 3.5 3.4"/></svg>',
  games: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 19 6v5.2c0 4.6-3 8-7 9.3-4-1.3-7-4.7-7-9.3V6l7-2.5z"/><path d="M12 8.2v5.6M9.5 10.4c.6-1.1 1.6-1.7 2.5-1.7s1.9.6 2.5 1.7"/></svg>',
  // v2.40.21 生活三件套：遗失物件 / 穿搭推荐 / 密码保险箱
  lost: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8.5 12 4l8 4.5v9L12 22l-8-4.5z"/><path d="M4 8.5 12 13l8-4.5M12 13v9"/></svg>',
  wardrobe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4"/><path d="M12 7c-4.4 0-8 2.2-8 5v9h16v-9c0-2.8-3.6-5-8-5z"/><path d="M12 12v9"/></svg>',
  vault: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10.5" width="16" height="10" rx="2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/><circle cx="12" cy="15.5" r="1.6"/><path d="M12 17.1v1.6"/></svg>',
  countdown: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13" r="7"/><path d="M12 9v4l2.6 1.5"/><path d="M9 3h6M12 3v1.5"/></svg>',
  // v2.46.116 翻页时钟：一张牌 + 中缝 + 上下两行点阵（翻页钟点）
  flipclock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="12" height="16" rx="2.5"/><path d="M6 12h12"/><path d="M9 8.5h2M13 8.5h2M9 15.5h2M13 15.5h2"/></svg>',
  ai: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11.6c0 3.4-3.6 6.2-8 6.2-.9 0-1.7-.1-2.5-.3L5.5 20l1.1-3.1A6.6 6.6 0 0 1 4 11.6C4 8.2 7.6 5.4 12 5.4s8 2.8 8 6.2z"/><path d="M12 8.6v3.6M10.2 10.4h3.6"/></svg>',
  // v2.46.76 新五入口：手持弹幕 / 自定义标签 / 体重记录 / 美食记忆 / 摸鱼日历
  danmu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="10" rx="3"/><path d="M7 13h7M16.5 13h.5"/><path d="M8 5l1.2 1.8M16 5l-1.2 1.8"/></svg>',
  spin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="13" r="8"/><path d="M12 13V5.2M12 13l5.6 5.4M12 13l-5.6 5.4"/><path d="M12 2.6v1.6"/></svg>',
  weight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="12" cy="10" r="2.6"/><path d="M10 16h4"/></svg>',
  meals: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11h16a8 8 0 0 1-16 0z"/><path d="M8 11V6.5M12 11V5M16 11V6.5"/></svg>',
  fish: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12c3-4 7-6 11-6 3 0 5.5 2 7 6-1.5 4-4 6-7 6-4 0-8-2-11-6z"/><circle cx="15.5" cy="11" r=".9"/><path d="M3 12l2.5-3M3 12l2.5 3"/></svg>',
}

/* 快捷宫格（3 列），带可达性过滤。
   v2.46.76（夜星）：9 个固定顺序（记账/音乐/棋牌游戏/股票/足迹/通讯录/时光痕迹/AI对话/笔记），
   原生活三件套（遗失物件/穿搭推荐/密码保险箱）下架，换为手持弹幕/自定义标签/体重记录/美食记忆/摸鱼日历；
   密码生成器只在工具岛（/tool/password），不占工作台。 */
const QUICK = [
  { label:'记账',   path:'/finance/book', acc:'--ab-grn', icon:ICONS.finance },
  { label:'音乐',   path:'/music',   acc:'--ab-blu', icon:ICONS.music },
  { label:'棋牌游戏', path:'/tool/games', acc:'--ab-cyn', icon:ICONS.games },
  { label:'足迹',   path:'/travels', acc:'--ab-cyn', icon:ICONS.travels },
  { label:'通讯录', path:'/contacts',acc:'--ab-amb', icon:ICONS.contacts },
  { label:'时光痕迹', path:'/tool/countdown', acc:'--ab-vio', icon:ICONS.countdown },
  { label:'翻页时钟', path:'/tool/flipclock', acc:'--ab-amb', icon:ICONS.flipclock },
  { label:'AI 对话', path:'/assistant', acc:'--ab-vio', icon:ICONS.ai },
  { label:'笔记',   path:'/notes',   acc:'--ab-pur', icon:ICONS.notes },
  // v2.46.76 新五入口
  { label:'手持弹幕', path:'/tool/danmu', acc:'--ab-cor', icon:ICONS.danmu },
  { label:'自定义标签', path:'/tool/spin', acc:'--ab-vio', icon:ICONS.spin },
  { label:'体重记录', path:'/life/weight', acc:'--ab-cyn', icon:ICONS.weight },
  { label:'美食记忆', path:'/life/meals', acc:'--ab-grn', icon:ICONS.meals },
  { label:'摸鱼日历', path:'/tool/fish', acc:'--ab-blu', icon:ICONS.fish },
]
const quick = computed(() => {
  // v2.46.117 按账号权限过滤（与「全部模块」同口径）：
  // 超管全部；菜单接口未加载成功不拦截（宁多勿少）；工作台等非授权对象豁免
  if (isSuper.value || !menus.loadedOk) return QUICK
  return QUICK.filter((m) => NAV_EXEMPT.has(m.path) || menus.isPathAllowed(m.path))
})

const income = ref(null)
const expense = ref(null)
const count = ref(null)

/* 数字滚动（#26）：hero 收支从 0 滚到位；null 期间维持「—」占位 */
const animIncome = countUp(() => income.value ?? 0, 700, 2)
const animExpense = countUp(() => expense.value ?? 0, 700, 2)
const heroIncomeText = computed(() => income.value == null ? '—' : '¥ ' + animIncome.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const heroExpenseText = computed(() => expense.value == null ? '—' : '¥ ' + animExpense.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

/* 视差（#21 · 克制版）：hero 卡随滚动 0.12x 上浮，位移封顶 12px；reduced-motion 直关 */
const heroShift = ref(0)
const prefersReduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
function onScroll() {
  if (prefersReduced) return
  heroShift.value = Math.min(12, window.scrollY * 0.12)
}

function go(path) {
  haptic.light()          // Tab/轻点 = light（#13），原裸 vibrate 收编
  router.push(path)
}

onMounted(async () => {
  window.addEventListener('scroll', onScroll, { passive: true })
  menus.load()   // 权限过滤数据源（store 内 inflight 去重，与 ModulesView 共用一次请求）
  try {
    const res = await financeApi.summary()
    const d = res?.data
    if (d) {
      income.value = d.month_income ?? d.income ?? null
      expense.value = d.month_expense ?? d.expense ?? null
      count.value = d.month_count ?? d.count ?? null
    }
  } catch { /* 未就绪保持占位 */ }
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
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
/* 收入 / 支出两栏并列（净流入已去掉） */
.abb-hero__pair { display: flex; gap: 16px; }
.abb-hero__col { flex: 1; min-width: 0; }
.abb-hero__num {
  margin-top: 6px; font-size: 24px; font-weight: 800; font-variant-numeric: tabular-nums;
  letter-spacing: .01em; color: var(--ls-text, #0f1530);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.abb-hero__num.up { color: var(--pnl-up, #e5484d); }
.abb-hero__num.dn { color: var(--pnl-down, #1aa86a); }

/* 快捷入口 */
.abb-sec { margin-top: 28px; }
.abb-sec__head {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin-bottom: 12px;
}
.abb-sec__title {
  margin: 0 0 12px; font-size: 13px; font-weight: 600; letter-spacing: .12em;
  color: var(--ls-text-3, #8a8f98);
}
.abb-sec__head .abb-sec__title { margin-bottom: 0; }
.abb-more {
  flex: none;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--m-accent, var(--lj-dai, #5b6ae0));
  -webkit-tap-highlight-color: transparent;
}
.abb-more:active { opacity: .7; }
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
