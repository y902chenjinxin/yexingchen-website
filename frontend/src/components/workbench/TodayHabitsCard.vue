<template>
  <section v-if="total" class="thc glass-card" aria-label="今天要做">
    <header class="thc-head">
      <div class="thc-title">
        <span class="thc-dot" :class="{ done: allDone }" aria-hidden="true"></span>
        今天
        <!-- v2.46.245：按「次」计数（3 杯水算 3 次），与下面进度条同一口径。
             纯布尔习惯时 unitTotal === total，显示与以前完全一样。 -->
        <em class="thc-count">{{ unitDone }}/{{ unitTotal }}</em>
      </div>
      <button class="thc-more" @click="$router.push('/habits')">全部 ›</button>
    </header>

    <div class="thc-bar" :aria-label="`今日完成 ${progress}%`">
      <i :style="{ width: progress + '%' }" :class="{ full: allDone }"></i>
    </div>

    <p v-if="allDone" class="thc-done-text">今天的 {{ unitTotal }} 项都做完了，收工。</p>

    <ul v-else class="thc-list">
      <li v-for="h in pending.slice(0, 3)" :key="h.id">
        <div class="thc-row">
          <button class="thc-item" @click="onToggle(h)">
            <span class="thc-ico"><AppIcon :icon="h.icon || '✓'" :size="15" /></span>
            <span class="thc-name">{{ h.name }}</span>
            <!-- v2.46.245：一天 N 次的习惯显示「已做/目标」；≤6 次用小圆点更直观 -->
            <span v-if="isCount(h)" class="thc-prog">
              <template v-if="h.daily_target <= 6">
                <i v-for="k in h.daily_target" :key="k" class="thc-pip" :class="{ on: k <= (h.today_count || 0) }"></i>
              </template>
              <em v-else class="thc-num">{{ h.today_count || 0 }}/{{ h.daily_target }}</em>
            </span>
            <span v-else-if="h.streak" class="thc-streak">{{ h.streak }}天</span>
            <span class="thc-check" :class="{ half: isCount(h) && (h.today_count || 0) > 0 }" aria-hidden="true"></span>
          </button>
          <button
            v-if="isCount(h)"
            class="thc-plus"
            :title="`记一次（${h.today_count || 0}/${h.daily_target}）`"
            @click.stop="onStep(h)"
          >＋</button>
        </div>
      </li>
    </ul>

    <p v-if="!allDone && pending.length > 3" class="thc-rest">还有 {{ pending.length - 3 }} 件</p>
    <p v-if="restCount" class="thc-rest">另有 {{ restCount }} 个排在别的日子</p>
  </section>

  <!-- 空态：有提醒价值 —— 没设每日动作的人，等于没有「今天该做什么」 -->
  <!-- 今天没有安排，但有别的日子的任务（月度/年度）—— 别误导他去新建 -->
  <section v-else-if="loaded && restCount" class="thc thc--empty glass-card">
    <div class="thc-empty-title">今天没有安排</div>
    <p class="thc-empty-sub">你还有 {{ restCount }} 个习惯排在别的日子，去「今天」页能看到全部和下一个到期日。</p>
    <button class="thc-cta" @click="$router.push('/habits')">去看看 ›</button>
  </section>

  <section v-else-if="loaded" class="thc thc--empty glass-card">
    <div class="thc-empty-title">今天还没有要做的事</div>
    <p class="thc-empty-sub">先设 1~3 个每天想坚持的小动作，这里就会出现打卡和连续天数。</p>
    <button class="thc-cta" @click="$router.push('/habits')">去设置 ›</button>
  </section>
</template>

<script setup>
/**
 * 工作台「今天」卡片（v2.46.140）
 *
 * 为什么要它：夜星要「每天知道做什么 + 有提醒 + 工作台能看到」。
 * 工作台原来只有记账/足迹/自选这类**回顾性数字**，没有「向前看」的那一块。
 *
 * 数据全部走 habits store（同一来源），打卡是乐观更新，点一下就走。
 * 提醒：每天首次进工作台时，若还有未打卡 → 弹一条；20:00 后语气变急。
 * 用 localStorage 按日期去重，避免刷一次弹一次。
 */
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElNotification } from 'element-plus'
import AppIcon from '@/components/common/AppIcon.vue'
import { useHabitsStore } from '@/stores/habits'

const store = useHabitsStore()
// ⚠️ setup store 直接解构会丢掉响应性（store 代理已经把 ref 拆成值），必须 storeToRefs
const { total, unitDone, unitTotal, progress, pending, allDone, restCount } = storeToRefs(store)

/** 是否「一天 N 次」型习惯（喝水 3 杯这种） */
function isCount(h) { return Number(h?.daily_target || 0) > 1 }
const loaded = ref(false)

function localDay() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function onToggle(h) {
  try {
    await store.toggle(h)
  } catch {
    ElNotification({ title: '打卡没成功', message: '网络不太行，刚才那下没记上，再点一次。', type: 'warning', duration: 2600 })
  }
}

/** 记一次进度：喝一杯点一下（v2.46.245） */
async function onStep(h) {
  try {
    const n = await store.step(h, 1)
    // 刚达成目标时给一句反馈，不用每次都弹
    if (n && n >= h.daily_target) {
      ElNotification({
        title: '今日目标达成',
        message: `${h.name} ${h.daily_target}/${h.daily_target}，这个习惯今天算完成了。`,
        type: 'success',
        duration: 2600,
        position: 'bottom-right',
      })
    }
  } catch {
    ElNotification({ title: '没记上', message: '网络不太行，这一下没提交成功，再点一次。', type: 'warning', duration: 2600 })
  }
}

function maybeRemind() {
  if (!pending.value.length) return
  const key = `xh_habit_reminded_${localDay()}`
  try {
    if (localStorage.getItem(key)) return
    localStorage.setItem(key, '1')
  } catch { /* 隐私模式忽略，最多多弹一次 */ }
  const hour = new Date().getHours()
  const late = hour >= 20
  // v2.46.245：带进度的习惯直接把「1/3」写进提醒，用户不用点开就知道差多少
  const line = (h) => (Number(h.daily_target || 0) > 1
    ? `${h.name} ${Number(h.today_count || 0)}/${h.daily_target}`
    : h.name)
  ElNotification({
    title: late ? '今天还剩几件没做' : '今天要做的事',
    message: late
      ? `还有 ${pending.value.length} 件没完成：${pending.value.slice(0, 3).map(line).join('、')}。现在补还来得及。`
      : `今天有 ${pending.value.length} 件：${pending.value.slice(0, 3).map(line).join('、')}`,
    type: late ? 'warning' : 'info',
    duration: late ? 6000 : 4200,
    position: 'bottom-right',
  })
}

onMounted(async () => {
  try {
    await store.load()
  } catch { /* 卡片静默失败，不影响工作台其它模块 */ }
  loaded.value = true
  maybeRemind()
})
</script>

<style scoped>
.thc { padding: 16px 18px 14px; }
.thc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.thc-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; letter-spacing: .02em; color: var(--tc-text, #0b1622); }
.thc-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--tc-cyan, #0e93b8); box-shadow: 0 0 0 3px rgba(14, 147, 184, .16); }
.thc-dot.done { background: var(--color-success, #0f7a56); box-shadow: 0 0 0 3px rgba(15, 122, 86, .16); }
.thc-count { font-style: normal; font-variant-numeric: tabular-nums; color: var(--tc-text-2, #46586e); font-weight: 600; }
.thc-more { border: 0; background: transparent; color: var(--tc-text-3, #5b6f8a); font: inherit; font-size: 12px; cursor: pointer; padding: 2px 4px; }
.thc-more:hover { color: var(--tc-cyan, #0e93b8); }

.thc-bar { height: 4px; border-radius: 999px; background: var(--tc-line, rgba(15, 60, 110, .14)); overflow: hidden; }
.thc-bar i { display: block; height: 100%; border-radius: 999px; background: var(--tc-btn-grad, linear-gradient(135deg, #8b5cff, #2de2ff)); transition: width .28s cubic-bezier(.2, .8, .2, 1); }
.thc-bar i.full { background: var(--color-success, #0f7a56); }

.thc-list { list-style: none; margin: 10px 0 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.thc-item {
  width: 100%; display: flex; align-items: center; gap: 9px;
  padding: 8px 4px; border: 0; background: transparent; border-radius: 9px;
  font: inherit; text-align: left; cursor: pointer; color: var(--tc-text, #0b1622);
  transition: background-color .15s;
}
.thc-item:hover { background: rgba(14, 147, 184, .07); }
.thc-ico { display: inline-flex; color: var(--tc-cyan, #0e93b8); flex: none; }
.thc-name { flex: 1; min-width: 0; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.thc-streak { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; flex: none; }
.thc-check { width: 16px; height: 16px; border-radius: 50%; border: 1.5px solid var(--tc-line-strong, rgba(15, 60, 110, .26)); flex: none; }
/* v2.46.245 进度：行内 ＋ 按钮 + 小圆点 */
.thc-row { display: flex; align-items: center; gap: 4px; }
.thc-row .thc-item { flex: 1; min-width: 0; }
.thc-plus {
  width: 24px; height: 24px; flex: none; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--tc-line-strong, rgba(15, 60, 110, .26));
  background: transparent; color: var(--tc-cyan, #0e93b8);
  font-size: 15px; line-height: 1; padding: 0;
  transition: background-color .15s, border-color .15s;
}
.thc-plus:hover { background: rgba(14, 147, 184, .12); border-color: var(--tc-cyan, #0e93b8); }
.thc-plus:active { transform: scale(.94); }
.thc-prog { display: inline-flex; align-items: center; gap: 3px; flex: none; margin-right: 2px; }
.thc-pip {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--tc-line, rgba(15, 60, 110, .14));
  transition: background-color .18s;
}
.thc-pip.on { background: var(--tc-cyan, #0e93b8); }
.thc-num { font-style: normal; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; }
.thc-check.half { border-color: var(--tc-cyan, #0e93b8); box-shadow: inset 0 0 0 3px rgba(14, 147, 184, .28); }
.thc-done-text { margin: 10px 0 2px; font-size: 12.5px; color: var(--color-success, #0f7a56); }
.thc-rest { margin: 6px 0 0; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }

.thc--empty { text-align: center; padding: 18px; }
.thc-empty-title { font-size: 13.5px; font-weight: 700; color: var(--tc-text, #0b1622); }
.thc-empty-sub { margin: 6px 0 10px; font-size: 12px; color: var(--tc-text-2, #46586e); line-height: 1.6; }
.thc-cta { border: 1px solid var(--tc-line-strong, rgba(15, 60, 110, .26)); background: transparent; color: var(--tc-cyan, #0e93b8); border-radius: 9px; padding: 7px 14px; font: inherit; font-size: 12.5px; cursor: pointer; }
</style>
