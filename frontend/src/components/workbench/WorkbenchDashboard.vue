<template>
  <section class="wd-section">
    <header class="wd-head">
      <div class="wd-title-block">
        <h2 class="wd-title">数据一览</h2>
        <span class="wd-sub">账本 · 资讯 · 行情，一眼入目</span>
      </div>
    </header>

    <div class="wd-grid">
      <!-- 账本卡 -->
      <a class="wd-card" @click.prevent="$router.push('/finance')">
        <div class="wd-card-head">
          <span class="wd-card-name">💰 账本</span>
          <span class="wd-more">查看全部 →</span>
        </div>
        <div v-if="empty" class="wd-empty">
          <span class="wd-empty-icon">🧾</span>
          <span class="wd-empty-text">还没有流水</span>
          <span class="wd-empty-hint">点击「记一笔」开始记账</span>
        </div>
        <div v-else class="wd-body">
          <div class="wd-rows">
            <div class="wd-row"><span class="wd-k">本月收入</span><span class="wd-v up">+ ¥ {{ finance.month_income ?? 0 }}</span></div>
            <div class="wd-row"><span class="wd-k">本月支出</span><span class="wd-v down">− ¥ {{ finance.month_expense ?? 0 }}</span></div>
          </div>
          <div class="wd-bar" :style="{ background: barBg }"><i :style="{ width: finance.barPercent + '%', background: barFill }"></i></div>
          <div class="wd-foot">累计结余 <b :class="(finance.balance ?? 0) >= 0 ? 'up-v' : 'down-v'">{{ (finance.balance ?? 0) >= 0 ? '+' : '−' }}¥ {{ Math.abs(finance.balance ?? 0).toFixed(2) }}</b> · 共 {{ finance.month_count }} 笔</div>
        </div>
      </a>

      <!-- 资讯卡 -->
      <a class="wd-card" @click.prevent="$router.push('/feeds')">
        <div class="wd-card-head">
          <span class="wd-card-name">📡 资讯</span>
          <span class="wd-more">查看全部 →</span>
        </div>
        <div v-if="empty" class="wd-empty">
          <span class="wd-empty-icon">📰</span>
          <span class="wd-empty-text">暂无订阅源</span>
          <span class="wd-empty-hint">添加 RSS 源后自动抓取</span>
        </div>
        <div v-else class="wd-body">
          <div class="wd-rows">
            <a v-for="it in feeds.slice(0, 3)" :key="it.id" class="wd-item" @click.prevent.stop="$router.push('/feeds')">
              <span class="wd-item-dot">→</span><span class="wd-item-txt">{{ it.title }}</span>
            </a>
          </div>
          <div class="wd-foot">今日 {{ feeds.length }} 条摘要</div>
        </div>
      </a>

      <!-- 行情卡 -->
      <a class="wd-card" @click.prevent="$router.push('/stocks')">
        <div class="wd-card-head">
          <span class="wd-card-name">📈 行情</span>
          <span class="wd-more">查看全部 →</span>
        </div>
        <div v-if="empty" class="wd-empty">
          <span class="wd-empty-icon">📊</span>
          <span class="wd-empty-text">还没有自选股</span>
          <span class="wd-empty-hint">点击「加自选股」盯盘</span>
        </div>
        <div v-else class="wd-body">
          <div class="wd-rows">
            <div class="wd-row"><span class="wd-k">持仓市值</span><span class="wd-v">¥ {{ stocks.marketValue }}</span></div>
            <div class="wd-row"><span class="wd-k">今日盈亏</span><span class="wd-v" :class="stocks.profit >= 0 ? 'up' : 'down'">{{ stocks.profit >= 0 ? '+' : '' }}{{ stocks.profit }}</span></div>
          </div>
          <div class="wd-chip-row">
            <span v-for="h in holdings.slice(0, 3)" :key="h.code" class="wd-chip" :class="h.pct >= 0 ? 'up' : 'down'">{{ h.name }} {{ h.pct >= 0 ? '+' : '' }}{{ h.pct }}%</span>
          </div>
        </div>
      </a>
    </div>
  </section>
</template>

<script setup>
defineProps({
  empty: { type: Boolean, default: true },
  finance: { type: Object, default: () => ({}) },
  feeds: { type: Array, default: () => [] },
  stocks: { type: Object, default: () => ({}) },
  holdings: { type: Array, default: () => [] }
})
</script>

<style scoped>
.wd-section { margin-bottom: 8px; }
.wd-head { display: flex; align-items: baseline; margin-bottom: 14px; }
.wd-title { margin: 0; font-size: 18px; letter-spacing: .12em; color: var(--lj-text); }
.wd-sub { margin-left: 12px; font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }

.wd-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.wd-card {
  position: relative; display: block; padding: 18px; border-radius: 16px; text-decoration: none;
  background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow);
  transition: all .28s; cursor: pointer; color: var(--lj-text); overflow: hidden;
}
.wd-card::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--lj-dai), transparent); opacity: .5; }
.wd-card:hover { transform: translateY(-3px); border-color: var(--lj-line-strong); box-shadow: var(--glass-highlight), 0 14px 30px rgba(0,0,0,.30); }

.wd-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.wd-card-name { font-size: 15px; letter-spacing: .06em; color: var(--lj-text); }
.wd-more { font-size: 12px; color: var(--lj-text-2); opacity: 0; transition: all .25s; }
.wd-card:hover .wd-more { opacity: 1; color: var(--lj-dai); }

.wd-empty { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 18px 8px; }
.wd-empty-icon { font-size: 28px; opacity: .7; }
.wd-empty-text { font-size: 14px; color: var(--lj-text-2); }
.wd-empty-hint { font-size: 12px; color: var(--lj-text-3); }

.wd-body { display: flex; flex-direction: column; gap: 10px; }
.wd-row { display: flex; justify-content: space-between; font-size: 13px; }
.wd-k { color: var(--lj-text-2); }
.wd-v { color: var(--lj-dai); font-weight: 600; }
.wd-v.up, .wd-chip.up, .up-v { color: var(--lj-ochre); }
.wd-v.down, .wd-chip.down, .down-v { color: var(--lj-vermilion); }
.wd-bar { height: 6px; border-radius: 999px; background: rgba(74,95,99,.14); overflow: hidden; }
.wd-bar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--lj-dai), var(--lj-ochre)); transition: width .6s; }
.wd-foot { font-size: 11px; color: var(--lj-text-3); }

.wd-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--lj-text-2); }
.wd-item-dot { color: var(--lj-ochre); flex: none; }
.wd-item-txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wd-chip-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 2px; }
.wd-chip { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: rgba(74,95,99,.08); }

@media (max-width: 900px) { .wd-grid { grid-template-columns: 1fr; } }
</style>