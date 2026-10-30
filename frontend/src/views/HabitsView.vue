<template>
  <div class="hb-page">
    <div class="hb-inner">
      <header class="hb-head">
        <BackButton class="hb-back" />
        <div class="hb-titles">
          <h1 class="hb-title">{{ managing ? '全部习惯' : '今天' }}</h1>
          <p class="hb-sub">
            <template v-if="managing">
              共 {{ list.length }} 条 · 点行尾的笔与垃圾桶可以修改或删除
            </template>
            <template v-else>
              {{ doneCount }}/{{ total }} 已完成<template v-if="bestStreak"> · 最长连续 {{ bestStreak }} 天</template>
            </template>
          </p>
        </div>
        <div class="hb-head-right">
          <IconButton
            :icon="managing ? 'check' : 'settings'"
            :label="managing ? '完成管理' : '管理'"
            size="sm"
            @click="managing = !managing"
          />
          <IconButton icon="plus" label="新习惯" variant="primary" @click="openCreate" />
        </div>
      </header>

      <!-- 今日进度 -->
      <section v-if="total" class="hb-progress glass-card">
        <div class="hb-ring">
          <svg viewBox="0 0 64 64" aria-hidden="true">
            <circle class="hb-ring-bg" cx="32" cy="32" r="27" />
            <circle
              class="hb-ring-fg"
              :class="{ full: allDone }"
              cx="32" cy="32" r="27"
              :stroke-dasharray="`${(progress / 100) * 169.6} 169.6`"
            />
          </svg>
          <span class="hb-ring-txt">{{ progress }}<i>%</i></span>
        </div>
        <div class="hb-progress-side">
          <div class="hb-progress-line" :class="{ done: allDone }">
            <template v-if="allDone">今天的都做完了</template>
            <template v-else>还剩 <b>{{ pending.length }}</b> 件没做</template>
          </div>
          <div class="hb-progress-hint">
            <template v-if="bestStreak">最长连续 {{ bestStreak }} 天 · 别断链</template>
            <template v-else>点一下就算打卡，连续天数会自动累计</template>
          </div>
        </div>
      </section>

      <!-- 六账户雷达（P2） -->
      <section v-if="radar && total" class="hb-card glass-card">
        <div class="hb-card-head">
          <h2 class="hb-card-title">复利六账户</h2>
          <span class="hb-card-sub">本周至今 · 总 {{ radar.overall }}%</span>
        </div>
        <div class="hb-radar-wrap">
          <!-- v2.46.247：viewBox 由 0 0 120 120 扩到 -20 -12 160 144。
               原来图形占满整块画布，四字标签（信用人脉 / 情绪关系）在左下用
               text-anchor=end 向左延伸，起点算下来是负数 → 被 SVG 裁掉，
               线上看到的就是「?关系」。四周留白后标签完整。 -->
          <svg class="hb-radar" viewBox="-20 -12 160 144" role="img" aria-label="六账户完成率雷达图">
            <g class="hb-radar-grid">
              <polygon v-for="g in RADAR_GRID" :key="g.key" :points="g.points" />
              <line
                v-for="(p, i) in RADAR_AXIS"
                :key="'ax' + i"
                :x1="60" :y1="60" :x2="p.x" :y2="p.y"
              />
            </g>
            <polygon class="hb-radar-area" :points="radarPoints" />
            <circle
              v-for="(p, i) in radarDots"
              :key="'d' + i"
              :cx="p.x" :cy="p.y" :r="1.6"
              class="hb-radar-dot"
            />
            <text
              v-for="(l, i) in radarLabels"
              :key="'l' + i"
              :x="l.x" :y="l.y"
              :text-anchor="l.anchor"
              dominant-baseline="middle"
              class="hb-radar-label"
              :class="{ empty: l.empty }"
            >{{ l.label }}</text>
          </svg>
        </div>
        <p v-if="radar.unclassified" class="hb-radar-tip">
          有 {{ radar.unclassified }} 个习惯没归账户，点「管理 → 编辑」给它选一个，雷达才画得全。
        </p>
      </section>

      <!-- 家人（P2）：被看见才有约束，只给汇总不给明细 -->
      <section v-if="household && household.members && household.members.length > 1" class="hb-card glass-card">
        <div class="hb-card-head">
          <h2 class="hb-card-title">家人</h2>
          <span class="hb-card-sub">今天打卡情况</span>
        </div>
        <ul class="hb-fam">
          <li v-for="m in household.members" :key="m.user_id" class="hb-fam-item">
            <span class="hb-fam-ava" aria-hidden="true">{{ m.avatar }}</span>
            <span class="hb-fam-name">
              {{ m.name }}<em v-if="m.is_me">（我）</em>
            </span>
            <span class="hb-fam-today" :class="{ all: m.today_done === m.today_total }">
              {{ m.today_done }}/{{ m.today_total }}
            </span>
            <span class="hb-fam-meta">本周 {{ m.week_rate }}% · 连续 {{ m.best_streak }} 天</span>
          </li>
        </ul>
      </section>

      <!-- 今日清单 / 全部习惯（v2.46.275 补管理入口与分组） -->
      <section v-if="total || restCount || managing" class="hb-card glass-card">
        <ul class="hb-list">
          <!-- 日常：只列今天该做的。v2.46.266 起不再把月/年/周频塞进「今天」 -->
          <template v-if="!managing">
            <!-- 今天确实没有安排（比如只剩月频习惯），别留一张空卡片 -->
            <li v-if="!todayList.length" class="hb-row hb-row--empty">
              今天没有安排要做的事<template v-if="restCount"> · 其余 {{ restCount }} 个在别的日子</template>
            </li>
            <li v-for="h in todayList" :key="h.id" class="hb-row" :class="{ done: h.checked_today }">
            <div class="hb-line">
            <button
              class="hb-hit"
              :aria-pressed="h.checked_today ? 'true' : 'false'"
              :aria-label="`${h.name}，${h.checked_today ? '已完成，点击清零' : '未完成，点击打满'}`"
              @click="onToggle(h)"
            >
              <span class="hb-ico" :style="h.color ? { color: h.color } : null">
                <AppIcon :icon="h.icon || '✓'" :size="18" />
              </span>
              <span class="hb-main">
                <span class="hb-name">{{ h.name }}</span>
                <span class="hb-meta">
                  <b v-if="isCount(h)" class="hb-prog" :class="{ full: h.checked_today }">
                    今天 {{ h.today_count || 0 }}/{{ h.daily_target }}
                  </b>
                  <template v-if="h.freq_text">{{ h.freq_text }} · </template>
                  连续 {{ h.streak }} 次 · 本周 {{ h.week_count }}<template v-if="h.weekly_goal">/{{ h.weekly_goal }}</template>
                  · 累计 {{ h.total_count }}
                  <template v-if="h.account"> · {{ accountLabel(h.account) }}</template>
                  <template v-if="h.penalty_cents"> · 罚 ¥{{ (h.penalty_cents / 100).toFixed(0) }}/天</template>
                </span>
              </span>
              <span class="hb-tick" :class="{ on: h.checked_today }" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12.6 9.6 17l9.4-10" />
                </svg>
              </span>
            </button>
            <!-- v2.46.245：一天 N 次的习惯，右侧 ＋ 记一次 -->
            <button
              v-if="isCount(h)"
              class="hb-plus"
              :title="`记一次（${h.today_count || 0}/${h.daily_target}）`"
              @click.stop="onStep(h)"
            >＋</button>
            </div>
            </li>
          </template>

          <!-- 管理模式（v2.46.275）：按「今天 / 排在其他日子」分组。
               夜星：「排在别的日子里的习惯，我如果需要修改或删除，该怎么操作，要有个入口。」
               原来管理态只多几行、且看不出哪条是「每月 15 号」—— 现在每行都带周期。 -->
          <template v-else>
            <template v-for="g in manageGroups" :key="g.key">
              <li class="hb-grouphd" :class="{ 'hb-grouphd--rest': g.key === 'rest' }">
                {{ g.title }}
                <em v-if="g.hint">{{ g.hint }}</em>
              </li>
              <li v-for="h in g.items" :key="h.id" class="hb-row">
                <div class="hb-manage">
                  <span class="hb-ico" :style="h.color ? { color: h.color } : null">
                    <AppIcon :icon="h.icon || '✓'" :size="17" />
                  </span>
                  <span class="hb-main">
                    <span class="hb-name">{{ h.name }}</span>
                    <span class="hb-meta">
                      {{ h.freq_text || '每天' }}
                      <template v-if="h.is_due_today === false"> · 今天不做</template>
                      <template v-if="isCount(h)"> · 一天 {{ h.daily_target }} 次</template>
                      <template v-if="h.account"> · {{ accountLabel(h.account) }}</template>
                    </span>
                  </span>
                  <IconButton icon="edit" size="sm" label="编辑" @click="openEdit(h)" />
                  <IconButton icon="trash" size="sm" label="删除" variant="danger" @click="onRemove(h)" />
                </div>
              </li>
            </template>
          </template>
        </ul>

        <!-- 入口：今天只该做 N 条时，明确告诉其余的在哪儿 —— 原来只有右上角一个「管理」，
             看不出「点它能找到每月 15 号那条」。 -->
        <button v-if="!managing && restCount" class="hb-more" @click="managing = true">
          <span>还有 {{ restCount }} 个习惯排在别的日子</span>
          <span class="hb-more-go">管理全部 ›</span>
        </button>
      </section>

      <!-- 空态 -->
      <!-- 空态按「有没有习惯」判断，不按「今天有没有该做的」——
           否则今天全做完（total=0）时也会弹「还没有每天要做的事」 -->
      <section v-if="!list.length && !loading" class="hb-empty">
        <EmptyState
          tone="data"
          title="还没有每天要做的事"
          description="先设 1~3 个每天想坚持的小动作（喝水、走 6000 步、写 200 字）。坚持 30 天，这里会给你一条链。"
          action-label="＋ 新建第一个"
          @action="openCreate"
        />
      </section>

      <!-- 本周复盘（v2.46.143） -->
      <section v-if="weekly && total" class="hb-card glass-card">
        <div class="hb-card-head">
          <h2 class="hb-card-title">本周复盘</h2>
          <span class="hb-card-sub">{{ weekly.week_start }} 起 · 第 {{ weekly.days_elapsed }} 天</span>
        </div>
        <div class="hb-wk">
          <div class="hb-wk-stat">
            <b>{{ weekly.rate }}<i>%</i></b>
            <span>完成率</span>
          </div>
          <div class="hb-wk-stat">
            <b>{{ weekly.checked }}<i>/{{ weekly.possible }}</i></b>
            <span>打卡</span>
          </div>
          <div class="hb-wk-stat" :class="{ warn: weekly.penalty_count > 0 }">
            <b>{{ weekly.penalty_count }}</b>
            <span>断链</span>
          </div>
          <div class="hb-wk-stat" :class="{ warn: weekly.penalty_cents > 0 }">
            <b>¥{{ (weekly.penalty_cents / 100).toFixed(0) }}</b>
            <span>罚金</span>
          </div>
        </div>
        <p class="hb-wk-text">{{ weekly.text }}</p>
        <p class="hb-wk-advice"><span>小玄</span>{{ weekly.suggestion }}</p>
      </section>

      <!-- 历史复盘（P2） -->
      <section v-if="reviews.length" class="hb-card glass-card">
        <div class="hb-card-head">
          <h2 class="hb-card-title">历史复盘</h2>
          <button class="hb-link" @click="showHistory = !showHistory">
            {{ showHistory ? '收起' : `展开 ${reviews.length} 周` }}
          </button>
        </div>
        <ul v-if="showHistory" class="hb-hist">
          <li v-for="r in reviews" :key="r.week_start" class="hb-hist-item">
            <span class="hb-hist-week">{{ r.week_start.slice(5) }} 周</span>
            <span class="hb-hist-rate" :class="{ low: r.rate < 60 }">{{ r.rate }}%</span>
            <span class="hb-hist-n">{{ r.checked }}/{{ r.possible }}<template v-if="r.penalty_count"> · 罚 {{ r.penalty_count }} 次</template></span>
            <span class="hb-hist-text">{{ r.text }}</span>
          </li>
        </ul>
      </section>

      <!-- 最近 30 天记录 -->
      <section v-if="total" class="hb-card glass-card">
        <div class="hb-card-head">
          <h2 class="hb-card-title">最近 30 天</h2>
          <span class="hb-card-sub">一共 {{ totalCheckins }} 次打卡</span>
        </div>
        <div v-for="h in list" :key="'heat' + h.id" class="hb-heat-row">
          <span class="hb-heat-name" :title="h.name">{{ h.name }}</span>
          <span class="hb-cells" :aria-label="`${h.name} 最近 30 天打卡 ${heatCount(h)} 天`">
            <i
              v-for="(c, i) in h.heat"
              :key="i"
              :class="{ on: c.checked }"
              :title="c.date + (c.checked ? ' 已打卡' : '')"
            ></i>
          </span>
          <span class="hb-heat-n">{{ heatCount(h) }}/30</span>
        </div>
      </section>
    </div>

    <!-- 新建 / 编辑（hb-dlg-compact：v2.46.279 手机端一屏化，见 mobile-paper.css） -->
    <el-dialog
      v-model="dialog"
      class="hb-dlg-compact"
      :title="form.id ? '编辑习惯' : '新建习惯'"
      width="420px"
      append-to-body
    >
      <div class="hb-form">
        <label class="hb-field">
          <span>名称</span>
          <el-input v-model="form.name" maxlength="64" placeholder="例如：走 6000 步" />
        </label>
        <!-- v2.46.248：维度放最前面 —— 先定「这属于哪一块」，图标自动跟着换，
             也顺带解释了雷达图那六个轴是怎么来的 -->
        <div class="hb-field">
          <span>归属维度（雷达图按这个维度汇总）</span>
          <div class="hb-acc-pick">
            <button
              v-for="a in ACCOUNT_OPTIONS"
              :key="a.key"
              type="button"
              class="hb-acc-btn"
              :class="{ on: form.account === a.key }"
              @click="pickAccount(a.key)"
            >
              <AppIcon :icon="a.icon" :size="14" />
              {{ a.label }}
            </button>
          </div>
        </div>
        <div class="hb-field">
          <span>图标（选了维度会自动带出，可改）</span>
          <div class="hb-icons">
            <button
              v-for="ic in ICON_CHOICES"
              :key="ic"
              type="button"
              class="hb-icon-btn"
              :class="{ on: form.icon === ic }"
              @click="form.icon = ic"
            >
              <AppIcon :icon="ic" :size="18" />
            </button>
          </div>
        </div>
        <!-- 多久做一次（v2.46.256）：原来只能设「每周几次」，表达不了「每月 15 号交房租」 -->
        <div class="hb-field">
          <span>多久做一次</span>
          <div class="hb-seg">
            <button
              v-for="f in FREQ_OPTIONS"
              :key="f.key"
              type="button"
              class="hb-seg-btn"
              :class="{ on: form.freq === f.key }"
              @click="form.freq = f.key"
            >{{ f.label }}</button>
          </div>
        </div>

        <label v-if="form.freq === 'daily'" class="hb-field">
          <span>间隔（1 = 每天）</span>
          <el-input-number v-model="form.interval" :min="1" :max="365" controls-position="right" />
        </label>

        <div v-if="form.freq === 'weekly'" class="hb-field">
          <span>选星期（都不选 = 每周任意 N 次）</span>
          <div class="hb-week">
            <button
              v-for="(w, i) in WEEKDAY_LABELS"
              :key="w"
              type="button"
              class="hb-wd-btn"
              :class="{ on: form.weekdays.includes(i + 1) }"
              @click="toggleWeekday(i + 1)"
            >{{ w }}</button>
          </div>
        </div>
        <label v-if="form.freq === 'weekly' && !form.weekdays.length" class="hb-field">
          <span>每周做够几次（0 = 不限）</span>
          <el-input-number v-model="form.weekly_goal" :min="0" :max="7" controls-position="right" />
        </label>

        <label v-if="form.freq === 'monthly'" class="hb-field">
          <span>每月几号（多个用逗号；31 = 当月最后一天）</span>
          <el-input v-model="form.monthDays" maxlength="40" placeholder="15 或 1,15,31" />
        </label>

        <div v-if="form.freq === 'yearly'" class="hb-field">
          <span>每年哪天</span>
          <div class="hb-year">
            <el-input-number v-model="form.yearMonth" :min="1" :max="12" controls-position="right" />
            <em>月</em>
            <el-input-number v-model="form.yearDay" :min="1" :max="31" controls-position="right" />
            <em>日</em>
          </div>
        </div>

        <label class="hb-field">
          <span>当天做几次算完成（0/1 = 做一次就完成）</span>
          <el-input-number v-model="form.daily_target" :min="0" :max="50" controls-position="right" />
        </label>
        <p class="hb-hint">{{ freqHint }}</p>
        <label class="hb-field">
          <span>断链自罚（每天，元；填 0 = 关闭）</span>
          <el-input-number v-model="form.penalty_yuan" :min="0" :max="1000" :step="1" :precision="2" controls-position="right" />
        </label>
        <label class="hb-field">
          <span>宽限天数（连续漏的前 N 天不罚）</span>
          <el-input-number v-model="form.penalty_grace" :min="0" :max="7" controls-position="right" />
        </label>
        <p class="hb-form-tip">
          开了自罚后，漏一天会自动从「个人零花」转一笔到「存款」，漏几天转几笔 ——
          罚的钱不消失，变成存款。
        </p>
      </div>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!form.name.trim()" @click="submit">
          {{ form.id ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 「今天」页（v2.46.140）
 *
 * 夜星的两条需求落点：
 *   1) 每天做什么 + 提醒 + 工作台可见 → 本页 + TodayHabitsCard（工作台卡片含每日一次提醒）
 *   2) 完成进度和记录 → 今日完成率环 / 连续天数 / 本周次数 / 最近 30 天热力格 / 累计次数
 *
 * 后端接口是现成的（app/routers/workbench/habits.py），本页只做界面；
 * 数据统一走 stores/habits，保证工作台卡片和本页永远同一个数。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import IconButton from '@/components/common/IconButton.vue'
import { useHabitsStore } from '@/stores/habits'

const store = useHabitsStore()
const {
  list, todayList, weekly, radar, household, reviews,
  loading, doneCount, total, progress, pending, bestStreak, allDone,
  restCount,
} = storeToRefs(store)

/** 六账户（顺序与后端 ACCOUNTS 一致，雷达图按这个顺序画） */
const ACCOUNT_OPTIONS = [
  { key: 'health', label: '身体', icon: '💪' },
  { key: 'mind', label: '认知', icon: '🧠' },
  { key: 'wealth', label: '财富', icon: '💰' },
  { key: 'social', label: '人脉', icon: '🤝' },
  { key: 'emotion', label: '关系', icon: '❤️' },
  { key: 'work', label: '作品', icon: '🎨' },
]

const showHistory = ref(false)

/* ---------- 雷达图几何（自绘，不引图表库） ---------- */
const RD_C = 60      // 圆心
const RD_R = 40      // 满值半径
const pointAt = (i, ratio) => {
  const ang = -Math.PI / 2 + (i * Math.PI * 2) / 6
  return {
    x: +(RD_C + Math.cos(ang) * RD_R * ratio).toFixed(2),
    y: +(RD_C + Math.sin(ang) * RD_R * ratio).toFixed(2),
  }
}
const ringPoints = (ratio) =>
  Array.from({ length: 6 }, (_, i) => pointAt(i, ratio)).map((p) => `${p.x},${p.y}`).join(' ')

const RADAR_GRID = [
  { key: 'r1', points: ringPoints(1) },
  { key: 'r2', points: ringPoints(0.66) },
  { key: 'r3', points: ringPoints(0.33) },
]
const RADAR_AXIS = Array.from({ length: 6 }, (_, i) => pointAt(i, 1))

const radarPoints = computed(() => {
  const accs = radar.value?.accounts || []
  if (!accs.length) return ''
  return accs
    .map((a, i) => {
      const p = pointAt(i, Math.max(0, Math.min(100, a.rate)) / 100)
      return `${p.x},${p.y}`
    })
    .join(' ')
})

const radarDots = computed(() => {
  const accs = radar.value?.accounts || []
  return accs.map((a, i) => pointAt(i, Math.max(0, Math.min(100, a.rate)) / 100))
})

const radarLabels = computed(() => {
  const accs = radar.value?.accounts || []
  return accs.map((a, i) => {
    const p = pointAt(i, 1.22)
    return {
      label: a.label,
      x: +p.x.toFixed(1),
      y: +p.y.toFixed(1),
      anchor: p.x > RD_C + 2 ? 'start' : p.x < RD_C - 2 ? 'end' : 'middle',
      empty: !a.items,
    }
  })
})

const managing = ref(false)

/**
 * 管理模式的分组（v2.46.275）
 *
 * 夜星：「排在别的日子里的习惯，我如果需要修改或删除，该怎么操作，要有个入口。」
 * 原来管理态只是把全量 list 直接铺开 —— 看不出哪条是「每月 15 号」，
 * 也不知道「今天不做」是为什么。现在按 is_due_today 分成两组，各带条数，
 * 其他日子那组还显式写一句「改或删都在这里」。
 */
const manageGroups = computed(() => {
  const todayItems = list.value.filter((h) => h.is_due_today !== false)
  const restItems = list.value.filter((h) => h.is_due_today === false)
  const out = []
  if (todayItems.length) {
    out.push({ key: 'today', title: `今天该做 · ${todayItems.length} 条`, hint: '', items: todayItems })
  }
  if (restItems.length) {
    out.push({
      key: 'rest',
      title: `排在别的日子 · ${restItems.length} 条`,
      hint: '平时不出现在「今天」，要改要删都在这里',
      items: restItems,
    })
  }
  return out
})
const dialog = ref(false)
const saving = ref(false)
const form = reactive({
  id: 0,
  name: '',
  icon: '✓',
  weekly_goal: 0,
  daily_target: 0,
  penalty_yuan: 0,   // 存「元」，提交时转分
  penalty_grace: 0,
  account: '',
  // 周期调度（v2.46.256）
  freq: 'daily',          // daily | weekly | monthly | yearly
  interval: 1,            // 每天 → 每 N 天
  weekdays: [],           // 每周 → 选中的星期（1=周一…7=周日）
  monthDays: '',          // 每月 → "15" 或 "1,15,31"
  yearMonth: 3,           // 每年 → 月
  yearDay: 1,             // 每年 → 日
})

/** 频率四个档位 */
const FREQ_OPTIONS = [
  { key: 'daily', label: '每天' },
  { key: 'weekly', label: '每周' },
  { key: 'monthly', label: '每月' },
  { key: 'yearly', label: '每年' },
]
const WEEKDAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function toggleWeekday(n) {
  const i = form.weekdays.indexOf(n)
  if (i >= 0) form.weekdays.splice(i, 1)
  else form.weekdays.push(n)
  form.weekdays.sort((a, b) => a - b)
}

/** 表单底下的说明：让人一眼确认「这个习惯到底哪几天会出现」 */
const freqHint = computed(() => {
  if (form.freq === 'daily') {
    return form.interval > 1
      ? `每 ${form.interval} 天出现一次，其他日子不进「今天要做」。`
      : '每天都会出现在「今天要做」里。'
  }
  if (form.freq === 'weekly') {
    if (form.weekdays.length) {
      const names = form.weekdays.map((i) => WEEKDAY_LABELS[i - 1]).join('、')
      return `只在 ${names} 出现。`
    }
    return `每天都可做，一周凑够 ${form.weekly_goal || '不限'} 次即可（不计漏）。`
  }
  if (form.freq === 'monthly') {
    return '只在设定的那几天出现；写 31 遇到小月会落到月末。'
  }
  return '一年只出现一次；2 月 29 日遇平年会落到 2 月 28。'
})

/** 图标候选 = 六个复利维度（v2.46.248）。
 *  夜星：「习惯的图标看不懂，做几个通用点的图标，对应 6 个维度的，具体的不用细分」。
 *  所以不再给十几个具体物件（水滴/扫帚/相机…），只留六个维度图标，
 *  选了维度就自动带出对应图标，想换还可以在下面手动点。 */
const ICON_CHOICES = ACCOUNT_OPTIONS.map((a) => a.icon)

/** 选维度：顺手把图标换成该维度的（用户手动挑过别的不覆盖） */
function pickAccount(key) {
  if (form.account === key) {
    form.account = ''
    return
  }
  form.account = key
  const dimIcons = ACCOUNT_OPTIONS.map((a) => a.icon)
  if (!form.icon || dimIcons.includes(form.icon)) {
    form.icon = ACCOUNT_OPTIONS.find((a) => a.key === key)?.icon || form.icon
  }
}

const totalCheckins = computed(() => list.value.reduce((s, h) => s + (h.total_count || 0), 0))

function heatCount(h) {
  return (h.heat || []).filter((c) => c.checked).length
}

/** 是否「一天 N 次」型习惯（喝水 3 杯这种，v2.46.245） */
function isCount(h) { return Number(h?.daily_target || 0) > 1 }

/** 记一次进度 */
async function onStep(h) {
  try {
    const n = await store.step(h, 1)
    if (n && n >= h.daily_target) {
      ElMessage({ message: `${h.name} 今天 ${h.daily_target}/${h.daily_target}，达标了`, type: 'success', duration: 1600 })
    }
  } catch { /* 拦截器已提示 */ }
}

async function onToggle(h) {
  try {
    await store.toggle(h)
    if (store.allDone && store.total) ElMessage({ message: '今天的都做完了，收工。', type: 'success', duration: 1800 })
  } catch {
    ElMessage({ message: '打卡没成功，再点一次', type: 'warning', duration: 2200 })
  }
}

function openCreate() {
  Object.assign(form, {
    id: 0, name: '', icon: ICON_CHOICES[0], weekly_goal: 0, daily_target: 0,
    penalty_yuan: 0, penalty_grace: 0, account: ACCOUNT_OPTIONS[0].key,
    freq: 'daily', interval: 1, weekdays: [], monthDays: '', yearMonth: 3, yearDay: 1,
  })
  dialog.value = true
}

function openEdit(h) {
  Object.assign(form, {
    id: h.id,
    name: h.name,
    icon: h.icon || '✓',
    weekly_goal: h.weekly_goal || 0,
    daily_target: h.daily_target || 0,
    penalty_yuan: (h.penalty_cents || 0) / 100,
    penalty_grace: h.penalty_grace || 0,
    account: h.account || '',
    freq: h.freq || 'daily',
    interval: h.interval || 1,
    weekdays: (h.weekdays || '').split(',').filter(Boolean).map(Number),
    monthDays: h.month_days || '',
    yearMonth: h.year_month || 3,
    yearDay: h.year_day || 1,
  })
  dialog.value = true
}

async function submit() {
  if (!form.name.trim()) return
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      icon: form.icon,
      color: null,
      weekly_goal: form.weekly_goal || 0,
      daily_target: form.daily_target || 0,
      // 元 → 分（后端只认分，避免浮点误差）
      penalty_cents: Math.round((Number(form.penalty_yuan) || 0) * 100),
      penalty_grace: form.penalty_grace || 0,
      account: form.account || '',
      // 周期调度：只把当前档位用得上的字段发过去（其余留空，后端也会归一化）
      freq: form.freq,
      interval: form.freq === 'daily' ? (Number(form.interval) || 1) : 1,
      weekdays: form.freq === 'weekly' ? form.weekdays.join(',') : '',
      month_days: form.freq === 'monthly' ? String(form.monthDays || '').trim() : '',
      year_month: form.freq === 'yearly' ? (Number(form.yearMonth) || 1) : 0,
      year_day: form.freq === 'yearly' ? (Number(form.yearDay) || 1) : 0,
    }
    if (form.id) await store.update(form.id, payload)
    else await store.create(payload)
    dialog.value = false
    ElMessage({ message: form.id ? '已保存' : '已创建，今天就可以开始打卡', type: 'success', duration: 1800 })
  } catch (e) {
    ElMessage({ message: e?.message || '保存失败', type: 'error' })
  } finally {
    saving.value = false
  }
}

async function onRemove(h) {
  try {
    await ElMessageBox.confirm(`删除「${h.name}」会连同它的全部打卡记录一起删掉，确定吗？`, '删除习惯', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }
  try {
    await store.remove(h.id)
    ElMessage({ message: '已删除', type: 'success', duration: 1500 })
  } catch (e) {
    ElMessage({ message: e?.message || '删除失败', type: 'error' })
  }
}

/** 进页面先结算断链罚金（幂等），有新罚单就弹一条，再拉本周复盘 */
async function bootSettle() {
  const items = await store.settle()
  if (!items.length) return
  const yuan = (items.reduce((s, i) => s + i.amount_cents, 0) / 100).toFixed(0)
  ElNotification({
    title: `断链了 ${items.length} 天，已记 ¥${yuan}`,
    message: `断链 ${items.length} 天，已自动从零花转进存款：${items.slice(0, 3).map((i) => `${i.date.slice(5)} ${i.habit}`).join('、')}${items.length > 3 ? ' …' : ''}`,
    type: 'warning',
    duration: 7000,
    position: 'bottom-right',
  })
}

onMounted(async () => {
  try {
    await store.load(true)
  } catch {
    ElMessage({ message: '加载失败，稍后重试', type: 'warning' })
  }
  await bootSettle()
  await store.loadWeekly()
  await Promise.all([store.loadRadar(), store.loadHousehold(), store.loadReviews()])
  await maybeWeekendReview()
})

/** 账户 key → 中文（行内展示用） */
function accountLabel(key) {
  return ACCOUNT_OPTIONS.find((a) => a.key === key)?.label || ''
}

/**
 * 周日 / 周一首次进站时，把上周（周一快照里是本周）的复盘存一份并弹一条。
 * 幂等由后端 (user_id, week_start) 唯一约束保证，所以不需要前端记「今天推过了」。
 */
async function maybeWeekendReview() {
  const dow = new Date().getDay() // 0=周日 1=周一
  if (dow !== 0 && dow !== 1) return
  const r = await store.makeReview()
  if (!r?.created) return
  ElNotification({
    title: '这周的复盘已经存下来了',
    message: `${r.review?.text || ''} ${r.review?.suggestion || ''}`.trim(),
    type: r.review?.rate >= 60 ? 'success' : 'warning',
    duration: 8000,
    position: 'bottom-right',
  })
}
</script>

<style scoped>
.hb-page { min-height: 100%; padding: 22px 20px 40px; }
.hb-inner { max-width: 780px; margin: 0 auto; }

/* 页头 */
.hb-head { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.hb-titles { flex: 1; min-width: 0; }
.hb-title {
  margin: 0; font-size: 26px; font-weight: 700; letter-spacing: .02em;
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
  color: var(--tc-text, #0b1622);
}
.hb-sub { margin: 3px 0 0; font-size: 12.5px; color: var(--tc-text-2, #46586e); }
.hb-head-right { display: flex; align-items: center; gap: 8px; flex: none; }

/* 进度 */
.hb-progress { display: flex; align-items: center; gap: 16px; padding: 16px 18px; margin-bottom: 14px; }
.hb-ring { position: relative; width: 64px; height: 64px; flex: none; }
.hb-ring svg { width: 64px; height: 64px; transform: rotate(-90deg); }
.hb-ring-bg { fill: none; stroke: var(--tc-line, rgba(15, 60, 110, .14)); stroke-width: 6; }
.hb-ring-fg {
  fill: none; stroke: var(--tc-cyan, #0e93b8); stroke-width: 6; stroke-linecap: round;
  transition: stroke-dasharray .35s cubic-bezier(.2, .8, .2, 1);
}
.hb-ring-fg.full { stroke: var(--color-success, #0f7a56); }
.hb-ring-txt {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--tc-text, #0b1622);
}
.hb-ring-txt i { font-size: 9px; font-style: normal; margin-left: 1px; opacity: .6; }
.hb-progress-side { min-width: 0; }
.hb-progress-line { font-size: 14px; font-weight: 600; color: var(--tc-text, #0b1622); }
.hb-progress-line b { color: var(--tc-cyan, #0e93b8); }
.hb-progress-line.done { color: var(--color-success, #0f7a56); }
.hb-progress-hint { margin-top: 4px; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }

/* 列表 */
.hb-card { padding: 10px 8px; margin-bottom: 14px; }
.hb-card-head { display: flex; align-items: baseline; justify-content: space-between; padding: 6px 10px 10px; }
.hb-card-title { margin: 0; font-size: 13.5px; font-weight: 700; color: var(--tc-text, #0b1622); }
.hb-card-sub { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }

.hb-list { list-style: none; margin: 0; padding: 0; }
.hb-row + .hb-row { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .14)); }

/* ---------- 管理模式的分组小标题（v2.46.275） ---------- */
.hb-grouphd {
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
  padding: 12px 2px 6px;
  font-size: 11.5px; font-weight: 600; letter-spacing: .04em;
  color: var(--tc-text-3, #5b6f8a);
  border-top: 1px solid var(--tc-line, rgba(15, 60, 110, .1));
}
.hb-grouphd:first-child { border-top: 0; padding-top: 4px; }
.hb-grouphd em {
  font-style: normal; font-weight: 400; font-size: 11px;
  color: var(--tc-text-3, #5b6f8a); opacity: .85;
}
.hb-grouphd--rest { color: var(--lj-seal, #a9812f); }

/* 管理行也带周期（原来只显示名字，看不出「每月 15 号」是哪条） */
.hb-manage .hb-meta { display: block; margin-top: 1px; }

.hb-row--empty {
  display: block; padding: 14px 2px;
  font-size: 12.5px; color: var(--tc-text-3, #5b6f8a);
}

/* ---------- 「还有 N 个排在别的日子」入口 ---------- */
.hb-more {
  width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 10px;
  margin-top: 10px; padding: 10px 2px 2px;
  border: 0; border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .14));
  background: transparent; cursor: pointer; font: inherit;
  font-size: 12px; color: var(--tc-text-3, #5b6f8a); text-align: left;
  transition: color .15s;
}
.hb-more:hover { color: var(--tc-cyan-deep, #0a708c); }
.hb-more-go { flex: none; font-weight: 600; color: var(--tc-cyan-deep, #0a708c); }
.hb-hit, .hb-manage {
  width: 100%; display: flex; align-items: center; gap: 11px;
  padding: 12px 10px; border: 0; background: transparent; border-radius: 10px;
  font: inherit; text-align: left; color: var(--tc-text, #0b1622); cursor: pointer;
}
.hb-hit:hover { background: rgba(14, 147, 184, .07); }
.hb-manage { cursor: default; }
.hb-ico { display: inline-flex; color: var(--tc-cyan, #0e93b8); flex: none; }
.hb-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.hb-name { font-size: 14.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hb-row.done .hb-name { color: var(--tc-text-2, #46586e); }
.hb-meta { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; }
.hb-tick {
  width: 24px; height: 24px; border-radius: 50%; flex: none;
  border: 1.5px solid var(--tc-line-strong, rgba(15, 60, 110, .26));
  display: flex; align-items: center; justify-content: center; color: transparent;
  transition: background-color .16s, border-color .16s, color .16s;
}
.hb-tick svg { width: 15px; height: 15px; }
.hb-tick.on {
  background: var(--tc-cyan, #0e93b8); border-color: var(--tc-cyan, #0e93b8); color: #fff;
}

/* 热力 */
.hb-heat-row { display: flex; align-items: center; gap: 10px; padding: 7px 10px; }
.hb-heat-name {
  width: 88px; flex: none; font-size: 12px; color: var(--tc-text-2, #46586e);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.hb-cells { display: flex; gap: 3px; flex: 1; min-width: 0; }
.hb-cells i {
  /* 30 格排一行：给明确高度，别靠 aspect-ratio（flex 里宽度先定，高度会被算成 0，看着像虚线） */
  flex: 1 1 0; height: 9px; min-width: 4px; border-radius: 2.5px;
  background: var(--tc-line, rgba(15, 60, 110, .14));
}
.hb-cells i.on { background: var(--tc-cyan, #0e93b8); }
.hb-heat-n { width: 42px; text-align: right; font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; }

.hb-empty { padding: 20px 0; }

/* 本周复盘 */
.hb-wk { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 4px 10px 2px; }
.hb-wk-stat {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 10px 4px; border-radius: 10px; background: rgba(14, 147, 184, .06);
}
.hb-wk-stat b { font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--tc-text, #0b1622); }
.hb-wk-stat b i { font-size: 10px; font-style: normal; opacity: .55; margin-left: 1px; }
.hb-wk-stat span { font-size: 11px; color: var(--tc-text-3, #5b6f8a); }
.hb-wk-stat.warn { background: rgba(255, 83, 71, .10); }
.hb-wk-stat.warn b { color: var(--color-danger, #cf2540); }
.hb-wk-text { margin: 10px 10px 0; font-size: 12.5px; color: var(--tc-text-2, #46586e); line-height: 1.65; }
.hb-wk-advice {
  margin: 8px 10px 6px; padding-left: 8px; font-size: 12.5px; line-height: 1.65;
  color: var(--tc-text, #0b1622); border-left: 2px solid var(--tc-cyan, #0e93b8);
}
.hb-wk-advice span {
  display: inline-block; margin-right: 6px; padding: 1px 6px; border-radius: 999px;
  background: rgba(14, 147, 184, .12); color: var(--tc-cyan-deep, #0a708c);
  font-size: 10.5px; font-weight: 700;
}

/* 弹窗表单 */
.hb-form { display: flex; flex-direction: column; gap: 14px; }
.hb-field { display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; color: var(--tc-text-2, #46586e); }
.hb-icons { display: flex; flex-wrap: wrap; gap: 6px; }
.hb-icon-btn {
  width: 34px; height: 34px; border-radius: 9px; border: 1px solid var(--tc-line, rgba(15, 60, 110, .14));
  background: transparent; color: var(--tc-text-2, #46586e); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.hb-icon-btn.on { border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan, #0e93b8); background: rgba(14, 147, 184, .08); }
.hb-form-tip { margin: -4px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--tc-text-3, #5b6f8a); }

/* 账户选择 */
.hb-acc-pick { display: flex; flex-wrap: wrap; gap: 6px; }

/* 周期选择（v2.46.256）：档位 + 星期，都是轻量胶囊，和维度选择同一套观感 */
.hb-seg { display: flex; gap: 5px; flex-wrap: wrap; }
.hb-seg-btn {
  padding: 5px 14px; border-radius: 999px; cursor: pointer; font: inherit; font-size: 12.5px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14)); background: transparent;
  color: var(--tc-text-2, #46586e); transition: border-color .15s, color .15s, background-color .15s;
}
.hb-seg-btn:hover { border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan-deep, #0a708c); }
.hb-seg-btn.on {
  border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan-deep, #0a708c);
  background: rgba(14, 147, 184, .1); font-weight: 600;
}
.hb-week { display: flex; gap: 5px; flex-wrap: wrap; }
.hb-wd-btn {
  min-width: 44px; padding: 5px 8px; border-radius: 8px; cursor: pointer; font: inherit; font-size: 12.5px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14)); background: transparent;
  color: var(--tc-text-2, #46586e); transition: border-color .15s, color .15s, background-color .15s;
}
.hb-wd-btn:hover { border-color: var(--tc-cyan, #0e93b8); }
.hb-wd-btn.on {
  border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan-deep, #0a708c);
  background: rgba(14, 147, 184, .12); font-weight: 600;
}
.hb-year { display: flex; align-items: center; gap: 6px; }
.hb-year em { font-style: normal; font-size: 12px; color: var(--tc-text-3, #5b6f8a); }
.hb-acc-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 11px; border-radius: 999px; cursor: pointer;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14));
  background: transparent; color: var(--tc-text-2, #46586e);
  font: inherit; font-size: 12.5px; line-height: 1.4;
}
.hb-acc-btn.on {
  border-color: var(--tc-cyan, #0e93b8);
  color: var(--tc-cyan-deep, #0a708c);
  background: rgba(14, 147, 184, .10);
  font-weight: 600;
}

/* 雷达 */
.hb-radar-wrap { display: flex; justify-content: center; padding: 4px 8px 2px; }
.hb-radar { width: 100%; max-width: 380px; height: auto; overflow: visible; }
.hb-radar-grid polygon { fill: none; stroke: var(--tc-line, rgba(15, 60, 110, .14)); stroke-width: .6; }
.hb-radar-grid line { stroke: var(--tc-line, rgba(15, 60, 110, .12)); stroke-width: .5; }
.hb-radar-area {
  fill: rgba(14, 147, 184, .18);
  stroke: var(--tc-cyan, #0e93b8);
  stroke-width: 1.1;
  stroke-linejoin: round;
}
.hb-radar-dot { fill: var(--tc-cyan, #0e93b8); }
.hb-radar-label { font-size: 5.6px; fill: var(--tc-text-2, #46586e); }
.hb-radar-label.empty { fill: var(--tc-text-3, #5b6f8a); opacity: .55; }
.hb-radar-tip { margin: 6px 12px 8px; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); line-height: 1.6; }

/* 家人 */
.hb-fam { list-style: none; margin: 0; padding: 0 6px 4px; }
.hb-fam-item {
  display: grid; grid-template-columns: 26px 1fr auto; grid-template-rows: auto auto;
  align-items: center; gap: 2px 8px; padding: 9px 6px;
}
.hb-fam-item + .hb-fam-item { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .12)); }
.hb-fam-ava { grid-row: span 2; font-size: 18px; text-align: center; }
.hb-fam-name { font-size: 13.5px; font-weight: 600; color: var(--tc-text, #0b1622); }
.hb-fam-name em { font-style: normal; font-weight: 400; color: var(--tc-text-3, #5b6f8a); font-size: 11.5px; }
.hb-fam-today {
  grid-row: span 2; font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums;
  color: var(--tc-text-2, #46586e);
}
.hb-fam-today.all { color: var(--color-success, #0f7a56); }
.hb-fam-meta { font-size: 11px; color: var(--tc-text-3, #5b6f8a); }

/* 历史复盘 */
.hb-link {
  border: 0; background: transparent; padding: 2px 4px; cursor: pointer;
  font: inherit; font-size: 11.5px; color: var(--tc-cyan-deep, #0a708c);
}
.hb-hist { list-style: none; margin: 0; padding: 0 10px 6px; }
.hb-hist-item {
  display: grid; grid-template-columns: auto auto 1fr; align-items: baseline; gap: 2px 8px;
  padding: 8px 2px; font-size: 12px;
}
.hb-hist-item + .hb-hist-item { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .12)); }
.hb-hist-week { color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; }
.hb-hist-rate { font-weight: 700; font-variant-numeric: tabular-nums; color: var(--color-success, #0f7a56); }
.hb-hist-rate.low { color: var(--color-danger, #cf2540); }
.hb-hist-n { color: var(--tc-text-2, #46586e); font-variant-numeric: tabular-nums; }
.hb-hist-text { grid-column: 1 / -1; color: var(--tc-text-3, #5b6f8a); font-size: 11.5px; line-height: 1.5; }

/* 手机端 */

:global(#app.is-mobile .hb-page) { padding: 14px 14px 90px; }
:global(#app.is-mobile .hb-title) { font-size: 30px; }
:global(#app.is-mobile .hb-progress) { padding: 14px; gap: 12px; }
:global(#app.is-mobile .hb-heat-name) { width: 68px; }
:global(#app.is-mobile .hb-cells i) { height: 8px; min-width: 3px; border-radius: 2px; }
.hb-line { display: flex; align-items: center; gap: 4px; }
.hb-line .hb-hit { flex: 1; min-width: 0; }
.hb-plus {
  width: 30px; height: 30px; flex: none; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--lj-line-strong); background: transparent;
  color: var(--lj-seal); font-size: 16px; line-height: 1; padding: 0;
}
.hb-plus:hover { background: var(--lj-seal-soft); border-color: var(--lj-seal); }
.hb-prog { font-weight: 700; color: var(--lj-seal); font-variant-numeric: tabular-nums; }
.hb-prog.full { color: var(--color-success, #0f7a56); }
.hb-hint { margin-left: 8px; font-size: 11.5px; color: var(--lj-text-3); line-height: 1.5; }
</style>
