<template>
  <div class="gw">
    <!-- ============ 积分中心 ============ -->
    <section class="gw-card">
      <header class="gw-head">
        <h2>积分中心</h2>
        <span class="gw-head-sub">棋牌三件套 · 积分与欢乐豆</span>
      </header>

      <div class="gw-balance">
        <div class="gw-bal">
          <i>积分</i>
          <b>{{ wallet.points ?? '—' }}</b>
          <em>日常行为 / 对局可得，可兑换欢乐豆</em>
        </div>
        <div class="gw-bal gold">
          <i>欢乐豆</i>
          <b>{{ fmt(wallet.beans) }}</b>
          <em>对局下注货币，输光可领救济金</em>
        </div>
      </div>

      <div class="gw-ops">
        <button
          class="gw-btn"
          :disabled="busy || wallet.signed_today"
          :aria-label="wallet.signed_today ? '今天已签到' : '每日签到'"
          @click="doSignin"
        >
          {{ wallet.signed_today ? '今日已签到' : '每日签到' }}
          <em v-if="wallet.signin_streak">连签 {{ wallet.signin_streak }} 天</em>
        </button>
        <button class="gw-btn ghost" :aria-label="'兑换欢乐豆'" @click="toggle('exchange')">
          兑换欢乐豆
        </button>
        <button class="gw-btn ghost" :aria-label="'赠送欢乐豆给家人'" @click="toggle('gift')">
          赠送家人
        </button>
        <button
          v-if="wallet.can_relief"
          class="gw-btn relief"
          :disabled="busy"
          aria-label="领取破产救济金"
          @click="doRelief"
        >领救济金 +{{ wallet.relief?.amount ?? 5000 }}</button>
      </div>

      <p class="gw-tip">
        签到每日 +10 积分（连签满 7 天额外 +50）；记账、写笔记、记体重等日常行为每次 +1 积分（每日上限
        {{ wallet.behavior_cap ?? 10 }}）。
        兑换比例 {{ wallet.exchange_rate?.points ?? 100 }} 积分 = {{ wallet.exchange_rate?.beans ?? 10000 }} 豆。
        今日已赠送 {{ wallet.gift_used_today ?? 0 }} / {{ wallet.gift_limit ?? 20000 }} 豆。
      </p>

      <!-- 兑换（内联，不弹窗） -->
      <div v-if="panel === 'exchange'" class="gw-inline">
        <div class="gw-inline-head">
          <b>积分兑换欢乐豆</b>
          <button class="gw-x" aria-label="收起兑换面板" @click="panel = ''">✕</button>
        </div>
        <div class="gw-inline-body">
          <label class="gw-field">
            <span>消耗积分</span>
            <input
              v-model.number="exchangePoints"
              type="number"
              min="0"
              :step="rate.points"
              :max="wallet.points || 0"
              aria-label="要消耗的积分数"
            />
          </label>
          <span class="gw-eq">=</span>
          <div class="gw-preview">{{ fmt(Math.floor((exchangePoints || 0) / rate.points) * rate.beans) }} 豆</div>
          <button class="gw-btn" :disabled="busy || !canExchange" @click="doExchange">确认兑换</button>
        </div>
        <p class="gw-inline-hint">积分需为 {{ rate.points }} 的整数倍；当前积分 {{ wallet.points ?? 0 }}。</p>
      </div>

      <!-- 赠送（内联，不弹窗） -->
      <div v-if="panel === 'gift'" class="gw-inline">
        <div class="gw-inline-head">
          <b>赠送欢乐豆给家人</b>
          <button class="gw-x" aria-label="收起赠送面板" @click="panel = ''">✕</button>
        </div>
        <div class="gw-inline-body">
          <label class="gw-field">
            <span>选择家人</span>
            <select v-model.number="giftTo" aria-label="选择要赠送的家人">
              <option :value="0" disabled>请选择</option>
              <option v-for="m in others" :key="m.user_id" :value="m.user_id">
                {{ m.avatar }} {{ m.name }}
              </option>
            </select>
          </label>
          <label class="gw-field">
            <span>赠送豆数</span>
            <input v-model.number="giftBeans" type="number" min="0" step="100" aria-label="要赠送的欢乐豆数量" />
          </label>
          <button class="gw-btn" :disabled="busy || !canGift" @click="doGift">送出</button>
        </div>
        <p class="gw-inline-hint">
          每人每日最多赠送 {{ wallet.gift_limit ?? 20000 }} 豆，今日已赠 {{ wallet.gift_used_today ?? 0 }} 豆。
        </p>
      </div>

      <p v-if="msg" class="gw-msg" :class="msgKind">{{ msg }}</p>
    </section>

    <!-- ============ 战绩与流水 ============ -->
    <section class="gw-card">
      <header class="gw-head">
        <h2>我的战绩</h2>
        <div class="gw-seg" role="tablist" aria-label="战绩与流水切换">
          <button
            v-for="t in tabs" :key="t.key"
            class="gw-seg-btn" :class="{ on: tab === t.key }"
            role="tab" :aria-selected="tab === t.key"
            @click="tab = t.key"
          >{{ t.label }}</button>
        </div>
      </header>

      <!-- 战绩 -->
      <div v-if="tab === 'stats'" class="gw-stats">
        <div v-for="s in stats" :key="s.game_key" class="gw-stat">
          <b>{{ s.label }}</b>
          <div class="gw-stat-nums">
            <span><i>{{ s.plays }}</i>局</span>
            <span><i>{{ s.wins }}</i>胜</span>
            <span><i>{{ s.win_rate }}%</i>胜率</span>
            <span><i>{{ s.best_streak }}</i>最高连胜</span>
          </div>
          <div class="gw-bar" :style="{ '--p': Math.min(100, s.win_rate || 0) + '%' }"><span></span></div>
        </div>
        <p v-if="!stats.length" class="gw-empty">还没有对局记录，去棋牌三件套开一局吧。</p>
      </div>

      <!-- 流水 -->
      <div v-else class="gw-ledger">
        <div class="gw-ledger-tabs">
          <button :class="{ on: ledgerKind === 'bean' }" @click="setLedger('bean')">欢乐豆</button>
          <button :class="{ on: ledgerKind === 'point' }" @click="setLedger('point')">积分</button>
        </div>
        <ul class="gw-ledger-list">
          <li v-for="r in ledger" :key="r.id">
            <span class="gw-ledger-amt" :class="r.amount >= 0 ? 'up' : 'down'">
              {{ r.amount >= 0 ? '+' : '' }}{{ r.amount }}
            </span>
            <span class="gw-ledger-note">{{ r.note || r.source }}</span>
            <span class="gw-ledger-time">{{ r.created_at }}</span>
          </li>
        </ul>
        <p v-if="!ledger.length" class="gw-empty">暂无流水。</p>
      </div>
    </section>

    <!-- ============ 家庭排行榜 ============ -->
    <section class="gw-card">
      <header class="gw-head">
        <h2>家庭排行榜</h2>
        <div class="gw-seg" role="tablist" aria-label="排行榜分类切换">
          <button
            class="gw-seg-btn" :class="{ on: rankTab === 'beans' }"
            role="tab" :aria-selected="rankTab === 'beans'"
            @click="rankTab = 'beans'"
          >欢乐豆</button>
          <button
            v-for="g in rankGames" :key="g.key"
            class="gw-seg-btn" :class="{ on: rankTab === g.key }"
            role="tab" :aria-selected="rankTab === g.key"
            @click="rankTab = g.key"
          >{{ g.label }}</button>
        </div>
      </header>

      <ol v-if="rankTab === 'beans'" class="gw-rank">
        <li v-for="(r, i) in leaderboard.beans" :key="r.user_id">
          <span class="gw-medal" :class="'m' + (i + 1)">{{ i + 1 }}</span>
          <span class="gw-rank-av">{{ r.avatar }}</span>
          <b class="gw-rank-name">{{ r.name }}</b>
          <span class="gw-rank-val">{{ fmt(r.beans) }} 豆</span>
          <span class="gw-rank-sub">{{ r.points }} 积分</span>
        </li>
      </ol>
      <ol v-else class="gw-rank">
        <li v-for="(r, i) in currentRank" :key="r.user_id">
          <span class="gw-medal" :class="'m' + (i + 1)">{{ i + 1 }}</span>
          <span class="gw-rank-av">{{ r.avatar }}</span>
          <b class="gw-rank-name">{{ r.name }}</b>
          <span class="gw-rank-val">{{ r.wins }} 胜</span>
          <span class="gw-rank-sub">{{ r.win_rate }}% · {{ r.plays }} 局</span>
        </li>
      </ol>
      <p v-if="!rankRows.length" class="gw-empty">还没有人对局过，快去开第一局。</p>
    </section>
  </div>
</template>

<script setup>
/** 棋牌三件套 · 积分中心 + 战绩 + 家庭排行榜（v2.43）。
 *
 * 挂在「个人中心」，全部内联呈现（无弹窗）。数据源 /api/game/*。
 * 家庭共享：排行榜按 household_id 汇总，能看到所有家人的战绩与豆子。
 */
import { ref, computed, onMounted } from 'vue'
import { gameEconomyApi } from '@/api/gameEconomy'
import { listMembers } from '@/api/life'

const busy = ref(false)
const msg = ref('')
const msgKind = ref('ok')
const panel = ref('')          // '' | 'exchange' | 'gift'
const tab = ref('stats')       // stats | ledger
const tabs = [
  { key: 'stats', label: '战绩' },
  { key: 'ledger', label: '流水' },
]
const ledgerKind = ref('bean')
const rankTab = ref('beans')

const wallet = ref({})
const stats = ref([])
const ledger = ref([])
const leaderboard = ref({ games: {}, beans: [] })
const members = ref([])
const exchangePoints = ref(0)
const giftTo = ref(0)
const giftBeans = ref(0)

const rate = computed(() => wallet.value.exchange_rate || { points: 100, beans: 10000 })
const others = computed(() => members.value)
const canExchange = computed(() => {
  const n = Number(exchangePoints.value) || 0
  return n > 0 && n % rate.value.points === 0 && n <= (wallet.value.points || 0)
})
const canGift = computed(() => {
  const n = Number(giftBeans.value) || 0
  return n > 0 && giftTo.value > 0 && n <= (wallet.value.beans || 0)
})

const rankGames = computed(() =>
  Object.entries(leaderboard.value.games || {}).map(([key, v]) => ({ key, label: v.label })),
)
const currentRank = computed(() => leaderboard.value.games?.[rankTab.value]?.list || [])
const rankRows = computed(() =>
  rankTab.value === 'beans' ? leaderboard.value.beans || [] : currentRank.value,
)

function fmt(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  return v.toLocaleString('zh-CN')
}

function flash(text, kind = 'ok') {
  msg.value = text
  msgKind.value = kind
  window.setTimeout(() => { if (msg.value === text) msg.value = '' }, 2600)
}

function toggle(name) {
  panel.value = panel.value === name ? '' : name
}

async function loadWallet() {
  const res = await gameEconomyApi.wallet()
  wallet.value = res?.data || {}
}
async function loadStats() {
  const res = await gameEconomyApi.stats()
  stats.value = res?.data?.list || []
}
async function loadLedger() {
  const res = await gameEconomyApi.ledger(ledgerKind.value, 30)
  ledger.value = res?.data?.list || []
}
async function loadLeaderboard() {
  const res = await gameEconomyApi.leaderboard()
  leaderboard.value = res?.data || { games: {}, beans: [] }
}
async function loadMembers() {
  try {
    const res = await listMembers()
    members.value = (res?.data?.list || []).filter(m => !m.is_owner || true)
  } catch { members.value = [] }
}

function setLedger(kind) {
  ledgerKind.value = kind
  loadLedger().catch(() => {})
}

async function doSignin() {
  busy.value = true
  try {
    const res = await gameEconomyApi.signin()
    wallet.value = res?.data || wallet.value
    flash(`签到成功，+${res?.data?.gained ?? 10} 积分`)
    loadLedger().catch(() => {})
  } catch (e) {
    flash(e?.response?.data?.msg || e?.message || '签到失败', 'bad')
  } finally { busy.value = false }
}

async function doExchange() {
  busy.value = true
  try {
    const res = await gameEconomyApi.exchange(Number(exchangePoints.value))
    wallet.value = res?.data || wallet.value
    flash(`兑换成功，+${fmt(res?.data?.gained)} 豆`)
    exchangePoints.value = 0
    panel.value = ''
    loadLedger().catch(() => {})
  } catch (e) {
    flash(e?.response?.data?.msg || e?.message || '兑换失败', 'bad')
  } finally { busy.value = false }
}

async function doGift() {
  busy.value = true
  try {
    await gameEconomyApi.gift(Number(giftTo.value), Number(giftBeans.value))
    await loadWallet()
    flash(`已送出 ${fmt(giftBeans.value)} 豆`)
    giftBeans.value = 0
    panel.value = ''
    loadLedger().catch(() => {})
  } catch (e) {
    flash(e?.response?.data?.msg || e?.message || '赠送失败', 'bad')
  } finally { busy.value = false }
}

async function doRelief() {
  busy.value = true
  try {
    const res = await gameEconomyApi.relief()
    wallet.value = res?.data || wallet.value
    flash(`已领取救济金 +${fmt(res?.data?.gained)} 豆`)
    loadLedger().catch(() => {})
  } catch (e) {
    flash(e?.response?.data?.msg || e?.message || '领取失败', 'bad')
  } finally { busy.value = false }
}

onMounted(() => {
  Promise.allSettled([
    loadWallet(), loadStats(), loadLedger(), loadLeaderboard(), loadMembers(),
  ])
})
</script>

<style scoped>
.gw { display: grid; grid-template-columns: 1fr; gap: 24px; }

.gw-card {
  position: relative;
  background: var(--xiu-card);
  backdrop-filter: blur(14px);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, .32), inset 0 1px 0 rgba(255, 255, 255, .04);
  border: 1px solid var(--xiu-line);
}
.gw-card::before {
  content: ""; position: absolute; top: 0; left: 18%; right: 18%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--xiu-gold), transparent); opacity: .5;
}

.gw-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  margin-bottom: 18px; padding-bottom: 14px;
  border-bottom: 1px solid rgba(201, 169, 108, .2);
  flex-wrap: wrap;
}
.gw-head h2 { font-size: 18px; font-weight: 600; color: var(--color-text); margin: 0; }
.gw-head-sub { font-size: 12px; color: var(--color-text-secondary); opacity: .8; }

/* 余额 */
.gw-balance { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.gw-bal {
  position: relative; padding: 16px 18px; border-radius: 14px;
  background: rgba(127, 168, 163, .10);
  border: 1px solid rgba(127, 168, 163, .24);
  display: flex; flex-direction: column; gap: 4px;
}
.gw-bal.gold { background: rgba(201, 169, 110, .12); border-color: rgba(201, 169, 110, .3); }
.gw-bal i { font-style: normal; font-size: 12.5px; color: var(--color-text-secondary); }
.gw-bal b {
  font-size: 30px; font-weight: 700; line-height: 1.1; color: var(--color-text);
  font-variant-numeric: tabular-nums;
}
.gw-bal.gold b { color: var(--color-gold); }
.gw-bal em { font-style: normal; font-size: 11.5px; color: var(--color-text-secondary); opacity: .78; }

/* 操作 */
.gw-ops { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.gw-btn {
  appearance: none; font-family: inherit; cursor: pointer;
  display: inline-flex; align-items: center; gap: 8px;
  padding: 9px 18px; border-radius: 999px; font-size: 13.5px; font-weight: 600;
  color: #2a1d05; border: 1px solid rgba(201, 169, 110, .5);
  background: linear-gradient(180deg, #e6cf9a, #c9a96e);
  transition: transform .16s, filter .16s, opacity .16s;
}
.gw-btn em { font-style: normal; font-size: 11.5px; opacity: .78; font-weight: 500; }
.gw-btn:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.05); }
.gw-btn:disabled { opacity: .45; cursor: not-allowed; }
.gw-btn.ghost {
  color: var(--color-text); border-color: var(--xiu-line);
  background: rgba(127, 168, 163, .12);
}
.gw-btn.relief {
  color: #fff; border-color: rgba(251, 113, 133, .5);
  background: linear-gradient(180deg, #e06a7c, #b8445a);
}

.gw-tip { margin: 14px 0 0; font-size: 12px; line-height: 1.7; color: var(--color-text-secondary); opacity: .85; }
.gw-msg { margin: 12px 0 0; font-size: 12.5px; }
.gw-msg.ok { color: #3fae7a; }
.gw-msg.bad { color: var(--dp-danger, #fb7185); }
.gw-empty { margin: 12px 0 0; font-size: 12.5px; color: var(--color-text-secondary); opacity: .8; }

/* 内联面板 */
.gw-inline {
  margin-top: 16px; padding: 14px 16px; border-radius: 14px;
  background: rgba(127, 168, 163, .08);
  border: 1px solid var(--xiu-line);
}
.gw-inline-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.gw-inline-head b { font-size: 13.5px; color: var(--color-text); }
.gw-x {
  appearance: none; cursor: pointer; border: none; background: transparent;
  color: var(--color-text-secondary); font-size: 14px; padding: 2px 6px; border-radius: 6px;
}
.gw-x:hover { background: rgba(127, 168, 163, .16); }
.gw-inline-body { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px; }
.gw-field { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--color-text-secondary); }
.gw-field input, .gw-field select {
  font-family: inherit; font-size: 13.5px; color: var(--color-text);
  padding: 8px 10px; border-radius: 10px; min-width: 130px;
  background: rgba(0, 0, 0, .18); border: 1px solid var(--xiu-line);
}
.gw-eq { color: var(--color-text-secondary); font-size: 14px; padding-bottom: 8px; }
.gw-preview {
  font-size: 16px; font-weight: 700; color: var(--color-gold);
  padding-bottom: 8px; font-variant-numeric: tabular-nums;
}
.gw-inline-hint { margin: 10px 0 0; font-size: 11.5px; color: var(--color-text-secondary); opacity: .8; }

/* 分段控件 */
.gw-seg {
  display: inline-flex; padding: 3px; border-radius: 999px; flex: none;
  background: rgba(127, 168, 163, .12); border: 1px solid rgba(127, 168, 163, .22);
}
.gw-seg-btn {
  appearance: none; border: none; background: transparent; cursor: pointer;
  font-family: inherit; font-size: 12.5px; padding: 5px 14px; border-radius: 999px;
  color: var(--color-text-secondary); transition: background .18s, color .18s;
}
.gw-seg-btn.on { background: var(--xiu-gold); color: #2a1d05; font-weight: 600; }

/* 战绩 */
.gw-stats { display: grid; gap: 14px; }
.gw-stat { display: flex; flex-direction: column; gap: 8px; }
.gw-stat > b { font-size: 13.5px; color: var(--color-text); }
.gw-stat-nums { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: var(--color-text-secondary); }
.gw-stat-nums i { font-style: normal; font-weight: 700; color: var(--color-text); font-size: 14px; margin-right: 3px; }
.gw-bar { height: 6px; border-radius: 999px; background: rgba(127, 168, 163, .18); overflow: hidden; }
.gw-bar span { display: block; height: 100%; width: var(--p, 0%); border-radius: 999px;
  background: linear-gradient(90deg, #7fa8a3, #c9a96e); transition: width .4s ease; }

/* 流水 */
.gw-ledger-tabs { display: flex; gap: 8px; margin-bottom: 10px; }
.gw-ledger-tabs button {
  appearance: none; cursor: pointer; font-family: inherit; font-size: 12.5px;
  padding: 5px 14px; border-radius: 999px; color: var(--color-text-secondary);
  background: transparent; border: 1px solid var(--xiu-line);
}
.gw-ledger-tabs button.on { background: rgba(201, 169, 110, .18); color: var(--color-gold); border-color: rgba(201, 169, 110, .45); }
.gw-ledger-list { list-style: none; margin: 0; padding: 0; max-height: 320px; overflow-y: auto; }
.gw-ledger-list li {
  display: flex; align-items: center; gap: 12px; padding: 9px 2px;
  border-bottom: 1px solid rgba(201, 169, 108, .1); font-size: 12.5px;
}
.gw-ledger-amt { font-weight: 700; font-variant-numeric: tabular-nums; flex: none; min-width: 58px; }
.gw-ledger-amt.up { color: #3fae7a; }
.gw-ledger-amt.down { color: var(--dp-danger, #fb7185); }
.gw-ledger-note { flex: 1; color: var(--color-text); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gw-ledger-time { flex: none; color: var(--color-text-secondary); opacity: .7; font-size: 11.5px; }

/* 排行榜 */
.gw-rank { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.gw-rank li {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px;
  background: rgba(127, 168, 163, .08); border: 1px solid var(--xiu-line);
}
.gw-medal {
  width: 22px; height: 22px; flex: none; border-radius: 50%; display: grid; place-items: center;
  font-size: 11.5px; font-weight: 700; color: var(--color-text-secondary);
  background: rgba(127, 168, 163, .18);
}
.gw-medal.m1 { background: linear-gradient(160deg, #f4dc9c, #c9a96e); color: #2a1d05; }
.gw-medal.m2 { background: linear-gradient(160deg, #e3e6ea, #a9b2bd); color: #2a1d05; }
.gw-medal.m3 { background: linear-gradient(160deg, #e0b48a, #b57e4c); color: #2a1d05; }
.gw-rank-av { font-size: 17px; flex: none; }
.gw-rank-name { flex: 1; font-size: 13.5px; color: var(--color-text); min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gw-rank-val { font-size: 13px; font-weight: 700; color: var(--color-gold); font-variant-numeric: tabular-nums; }
.gw-rank-sub { font-size: 11.5px; color: var(--color-text-secondary); flex: none; min-width: 92px; text-align: right; }

@media (max-width: 640px) {
  .gw-balance { grid-template-columns: 1fr; }
  .gw-bal b { font-size: 26px; }
  .gw-rank-sub { display: none; }
  .gw-card { padding: 18px; }
}
</style>
