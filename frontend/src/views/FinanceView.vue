<template>
  <div class="fin-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="fin-inner">
      <!-- 页头：返回 + 标题 -->
      <header class="fin-head">
        <div class="fin-head-left">
          <BackButton class="fin-back" />
        </div>
        <div class="fin-titles">
          <h1 class="fin-title">家庭账本</h1>
          <p class="fin-sub">流水明账 · 家人共享</p>
        </div>
        <div class="fin-head-right">
          <button class="fin-btn primary" @click="openNew">＋ 记一笔</button>
        </div>
      </header>

      <!-- 月份切换 + 记一笔面板 -->
      <div class="fin-toolbar">
        <div class="fin-period">
          <div class="fin-dim">
            <button class="fin-dim-btn" :class="{ on: dim === 'day' }" @click="setDim('day')">日</button>
            <button class="fin-dim-btn" :class="{ on: dim === 'month' }" @click="setDim('month')">月</button>
            <button class="fin-dim-btn" :class="{ on: dim === 'year' }" @click="setDim('year')">年</button>
          </div>
          <button class="fin-nav" @click="shift(-1)">‹</button>
          <div class="fin-dd-wrap" @keydown.esc="ddOpen = false">
            <button class="fin-month-label" @click.stop="toggleDd">
              {{ periodLabel }}<span v-if="!isNowPeriod" class="fin-this" @click.stop="goNow">回{{ dim === 'day' ? '今天' : (dim === 'year' ? '今年' : '本月') }}</span>
              <span class="fin-dd-caret">▾</span>
            </button>
            <transition name="fd">
              <div v-if="ddOpen" class="fin-dd glass" @click.stop>
                <div class="fin-dd-col">
                  <div class="fin-dd-head">年</div>
                  <div class="fin-dd-list" ref="ddYearList">
                    <button v-for="y in yearOptions" :key="y" class="fin-dd-item" :class="{ on: y === ddYear }" @click="pickYear(y)">{{ y }}</button>
                  </div>
                </div>
                <div v-if="dim !== 'year'" class="fin-dd-col">
                  <div class="fin-dd-head">月</div>
                  <div class="fin-dd-list">
                    <button v-for="m in 12" :key="m" class="fin-dd-item" :class="{ on: m === ddMonth }" @click="pickMonth(m)">{{ m }}</button>
                  </div>
                </div>
                <div v-if="dim === 'day'" class="fin-dd-col">
                  <div class="fin-dd-head">日</div>
                  <div class="fin-dd-list">
                    <button v-for="d in ddDays" :key="d" class="fin-dd-item" :class="{ on: d === ddSelDay }" @click="pickDay(d)">{{ d }}</button>
                  </div>
                </div>
              </div>
            </transition>
          </div>
          <button class="fin-nav" @click="shift(1)">›</button>
        </div>
        <div class="fin-io">
          <button class="fin-btn ghost small" @click="exportCsv">导出 CSV</button>
          <label class="fin-btn ghost small fin-import">
            导入账本
            <input type="file" accept=".csv,.xlsx,.xlsm,.xls,text/csv,text/plain,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel" class="fin-import-file" @change="onImportFile" />
          </label>
          <a class="fin-help" href="javascript:void(0)" @click="showImportHelp = !showImportHelp">导入格式说明</a>
        </div>
      </div>

      <!-- 导入说明 -->
      <transition name="fd">
        <div v-if="showImportHelp" class="fin-io-help glass">
          <h4 class="fin-io-help-title">导入格式说明</h4>
          <p class="fin-io-help-line">支持 <b>.csv / .xlsx / .xlsm</b>（表格与文本均可）。</p>
          <p class="fin-io-help-line">无需手动整理：任意表头或杂乱格式（微信/支付宝/银行/Excel 导出），均由 <b>AI 自动识别</b>为「日期 / 收支 / 分类 / 金额 / 备注」并精简后展示，确认后再入库。</p>
          <p class="fin-io-help-line">规则参考：金额为负或「支/消费」语境归支出、为正归收入；分类缺失归「其他」；可上传本站「导出 CSV」的文件批量还原。</p>
          <p class="fin-io-help-line">旧版 <code>.xls</code> 请先另存为 <code>.xlsx</code> 或 CSV。</p>
        </div>
      </transition>

      <!-- 智能导入预览（内联面板，非弹窗） -->
      <transition name="fd">
        <section v-if="importing.analyzing || importing.rows.length || importing.skipped || importing.errors.length" class="fin-import-panel glass">
          <div class="fin-import-panel-head">
            <span class="fin-import-panel-title">🤖 智能导入预览</span>
            <span v-if="importing.analyzing" class="fin-import-loading">AI 正在识别并精简数据…</span>
            <span v-else class="fin-import-done">识别完成</span>
            <button class="fin-form-close" @click="cancelImport">✕</button>
          </div>

          <div v-if="importing.analyzing" class="fin-import-empty">正在读取并识别文件，请稍候…</div>

          <template v-else>
            <div class="fin-import-summary">
              <span>识别出 <b>{{ importing.rows.length }}</b> 条流水</span>
              <span v-if="importing.skipped">跳过 <b class="warn">{{ importing.skipped }}</b> 条无效数据</span>
              <span v-if="importing.summary" class="fin-import-ai">{{ importing.summary }}</span>
              <span v-if="importing.is_fake" class="fin-import-fake">未配置 AI Provider，已用本地规则解析</span>
            </div>

            <div v-if="importing.errors.length" class="fin-import-errors">
              <span v-for="(err, i) in importing.errors" :key="i" class="fin-import-err">{{ err }}</span>
            </div>

            <table v-if="importing.rows.length" class="fin-import-table">
              <thead>
                <tr><th>日期</th><th>收支</th><th>分类</th><th>金额</th><th>备注</th></tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in importing.rows" :key="i">
                  <td>{{ r.date }}</td>
                  <td><span class="fin-import-type" :class="r.type">{{ r.type === 'income' ? '收' : '支' }}</span></td>
                  <td>{{ r.category }}</td>
                  <td class="fin-import-amt" :class="r.type">{{ r.type === 'income' ? '+' : '−' }} ¥ {{ money(r.amount) }}</td>
                  <td class="fin-import-note">{{ r.note }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="fin-import-empty">没有识别到有效流水，请检查文件格式。</div>

            <div class="fin-import-actions">
              <button class="fin-btn ghost" @click="cancelImport">取消</button>
              <button class="fin-btn primary" :disabled="!importing.rows.length || importing.confirming" @click="doConfirmImport">
                {{ importing.confirming ? '导入中…' : `确认导入 ${importing.rows.length} 条` }}
              </button>
            </div>
          </template>
        </section>
      </transition>

      <!-- 记一笔（内联面板，非弹窗） -->
      <transition name="fd">
        <section v-if="form.show" class="fin-form glass">
          <div class="fin-form-head">
            <span class="fin-form-title">{{ form.editing ? '编辑流水' : '记一笔' }}</span>
            <span v-if="form.editing" class="fin-form-edit-tag">正在编辑 #{{ form.editingId }}</span>
            <button class="fin-form-close" @click="form.show = false">✕</button>
          </div>

          <div class="fin-form-body">
            <div class="fin-f-type">
              <button
                v-for="t in typeTabs"
                :key="t.key"
                class="fin-tab"
                :class="{ active: form.type === t.key }"
                @click="pickType(t.key)"
              >{{ t.label }}</button>
            </div>

            <div class="fin-f-row">
              <div class="fin-f-field grow">
                <label class="fin-f-label">金额（元）</label>
                <el-input-number
                  v-model="form.amount"
                  :min="0.01"
                  :precision="2"
                  :step="10"
                  :controls="false"
                  class="fin-amount"
                  placeholder="0.00"
                />
              </div>
              <div class="fin-f-field">
                <label class="fin-f-label">日期</label>
                <el-date-picker
                  v-model="form.date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  :clearable="false"
                  class="fin-date"
                />
              </div>
            </div>

            <!-- 资金池：收入=进哪个池 / 支出=从哪个池出 / 调拨=转出→转入 -->
            <div class="fin-f-field">
              <div class="fin-f-label-row">
                <label class="fin-f-label">
                  {{ form.type === 'income' ? '进入哪个池' : (form.type === 'expense' ? '从哪个池出' : '调拨方向') }}
                </label>
                <span v-if="form.type === 'transfer'" class="fin-f-hint">转出 → 转入</span>
              </div>

              <template v-if="form.type === 'transfer'">
                <div class="fin-transfer-row">
                  <el-select v-model="form.fundFrom" class="fin-transfer-sel">
                    <el-option v-for="f in FUND_ORDER" :key="f" :label="FUND_META[f].label" :value="f" />
                  </el-select>
                  <span class="fin-transfer-arrow">→</span>
                  <el-select v-model="form.fundTo" class="fin-transfer-sel">
                    <el-option v-for="f in FUND_ORDER" :key="f" :label="FUND_META[f].label" :value="f" />
                  </el-select>
                </div>
                <div class="fin-quick-tags">
                  <span class="fin-quick-label">快捷理由</span>
                  <button
                    v-for="tag in TRANSFER_TAGS"
                    :key="tag"
                    class="fin-quick-tag"
                    :class="{ on: form.note === tag }"
                    @click="form.note = form.note === tag ? '' : tag"
                  >{{ tag }}</button>
                </div>
              </template>

              <div v-else class="fin-funds">
                <button class="fin-fund" :class="{ active: form.fund === 'none' }" @click="pickFund('none')">🚫 未归类</button>
                <button
                  v-for="f in FUND_ORDER"
                  :key="f"
                  class="fin-fund"
                  :class="[{ active: form.fund === f }, f]"
                  @click="pickFund(f)"
                >{{ FUND_META[f].icon }} {{ FUND_META[f].label }}</button>
              </div>
            </div>

            <!-- 归属人：只有涉及「个人零花」时才需要指定是谁的 -->
            <div v-if="needOwner" class="fin-f-field">
              <label class="fin-f-label">归属人</label>
              <div class="fin-funds">
                <button
                  v-for="m in ownerOptions"
                  :key="m.user_id"
                  class="fin-fund"
                  :class="{ active: String(form.member) === String(m.user_id) }"
                  @click="form.member = m.user_id"
                >{{ m.avatar }} {{ m.name }}</button>
              </div>
            </div>

            <div v-if="form.type !== 'transfer'" class="fin-f-field">
              <div class="fin-f-label-row">
                <label class="fin-f-label">分类</label>
                <button class="fin-cat-manage" @click="openCatDialog">管理分类</button>
              </div>
              <div class="fin-cats">
                <button
                  v-for="c in currentCats"
                  :key="c.key"
                  class="fin-cat"
                  :class="{ active: form.category === c.key }"
                  @click="form.category = c.key"
                >{{ c.icon }} {{ c.key }}</button>
              </div>
            </div>

            <div class="fin-f-field">
              <label class="fin-f-label">备注</label>
              <div class="fin-note-row">
                <input
                  v-model="form.note"
                  class="fin-note-input"
                  placeholder="写点什么（可语音）…"
                  maxlength="255"
                />
                <VoiceInputButton @result="onVoiceNote" />
              </div>
            </div>

            <div class="fin-form-actions">
              <button v-if="form.editing" class="fin-btn ghost" @click="form.show = false">取消</button>
              <button class="fin-btn primary" :disabled="saving" @click="save">{{ form.editing ? '保存修改' : '记入账本' }}</button>
            </div>
          </div>
        </section>
      </transition>

      <!-- 资金池卡片（公私账核心视觉锚点）：点击切到对应 Tab -->
      <section class="fin-pools" aria-label="资金池">
        <button
          v-for="p in poolCards"
          :key="p.fund"
          class="fin-pool glass"
          :class="[p.fund, { on: activeTab === p.fund }]"
          @click="openPool(p.fund)"
        >
          <span class="fin-pool-top">
            <span class="fin-pool-icon">{{ FUND_META[p.fund].icon }}</span>
            <span class="fin-pool-name">{{ p.label }}</span>
          </span>
          <span class="fin-pool-val" :class="{ neg: p.balance < 0 }">¥ {{ money(p.balance) }}</span>
          <span class="fin-pool-flags">
            <span v-if="p.balance < 0" class="fin-pool-over">已透支</span>
            <span v-else class="fin-pool-ok">余 {{ money(p.balance) }}</span>
          </span>
          <span class="fin-pool-sub">转入 ¥ {{ money(p.inflow) }} · 已用 ¥ {{ money(p.outflow) }}</span>
        </button>
      </section>

      <!-- 待归类提醒条：只统计 2026-10 之后的流水，历史数据不在此列 -->
      <div v-if="funds.unclassified > 0 && activeTab !== 'ledger'" class="fin-todo glass">
        <span class="fin-todo-text">有 <b>{{ funds.unclassified }}</b> 笔流水还没归到任何池子，池子数字暂不含它们。</span>
        <button class="fin-btn ghost small" @click="showUnclassified">去归类</button>
      </div>

      <!-- 分栏 Tab -->
      <div class="fin-tabs" role="tablist">
        <button
          v-for="t in tabs"
          :key="t.key"
          class="fin-tab-item"
          :class="{ on: activeTab === t.key }"
          role="tab"
          :aria-selected="activeTab === t.key"
          @click="activeTab = t.key"
        >{{ t.label }}</button>
      </div>

      <!-- 账本数据概览：只保留一组（收入 / 支出 / 笔数 / 累计结余）。
           原先还另有一组「手机端」变体（净流入 / 支出 / 笔数），但它既没有被媒体查询
           切换，又被后面同特异性的 .fin-kpis{display:grid} 覆盖了 display:none，
           于是两组同时渲染 —— 看起来就像同一组数据被画了两遍。
           净流入本质是「收入 − 支出」，与已有的收入、支出两张卡重复，故一并去掉。 -->
      <!-- ===== 总览 Tab ===== -->
      <template v-if="activeTab === 'overview'">
      <section class="fin-kpis" aria-label="账本数据概览">
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}收入</span>
          <span class="fin-kpi-val income">+ ¥ {{ money(summary.income) }}</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}支出</span>
          <span class="fin-kpi-val expense">− ¥ {{ money(summary.expense) }}</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">{{ unitLabel }}笔数</span>
          <span class="fin-kpi-val">{{ summary.count }}</span>
          <span class="fin-kpi-sub">笔流水</span>
        </div>
        <div class="fin-kpi glass">
          <span class="fin-kpi-label">累计结余</span>
          <span class="fin-kpi-val" :class="summary.balance >= 0 ? 'income' : 'expense'">{{ summary.balance >= 0 ? '+' : '−' }} ¥ {{ money(Math.abs(summary.balance)) }}</span>
        </div>
      </section>

      <!-- 家人账目：人员标签 + 汇总数据 -->
      <section class="fin-members glass">
        <div class="fin-members-head">
          <h2 class="fin-chart-title">家人账目</h2>
          <span class="fin-members-hint">点标签看各自的，合计为全家</span>
        </div>

        <div class="fin-mtags">
          <button class="fin-mtag" :class="{ on: !memberFilter }" @click="pickMember('')">
            <span class="fin-mtag-avatar">🏠</span>
            <span class="fin-mtag-name">全部家人</span>
            <span class="fin-mtag-amt">¥ {{ money(breakdown.total?.expense) }}</span>
          </button>
          <button
            v-for="m in memberTags"
            :key="m.user_id"
            class="fin-mtag"
            :class="{ on: String(memberFilter) === String(m.user_id) }"
            @click="pickMember(m.user_id)"
          >
            <span class="fin-mtag-avatar">{{ m.avatar }}</span>
            <span class="fin-mtag-name">{{ m.name }}</span>
            <span class="fin-mtag-amt">¥ {{ money(m.expense) }}</span>
          </button>
        </div>

        <div v-if="breakdown.members && breakdown.members.length" class="fin-mtable-wrap">
          <table class="fin-mtable">
            <thead>
              <tr>
                <th class="c-name">成员</th>
                <th class="c-num">{{ unitLabel }}收入</th>
                <th class="c-num">{{ unitLabel }}支出</th>
                <th class="c-num">笔数</th>
                <th class="c-num">结余</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="m in breakdown.members"
                :key="m.user_id"
                class="fin-mtr"
                :class="{ on: String(memberFilter) === String(m.user_id) }"
                @click="pickMember(m.user_id)"
              >
                <td class="c-name"><span class="fin-mtd-avatar">{{ m.avatar }}</span>{{ m.name }}</td>
                <td class="c-num income">+ ¥ {{ money(m.income) }}</td>
                <td class="c-num expense">− ¥ {{ money(m.expense) }}</td>
                <td class="c-num">{{ m.count }}</td>
                <td class="c-num" :class="m.balance >= 0 ? 'income' : 'expense'">
                  {{ m.balance >= 0 ? '+' : '−' }} ¥ {{ money(Math.abs(m.balance)) }}
                </td>
              </tr>
              <tr class="fin-mtr total">
                <td class="c-name">全家合计</td>
                <td class="c-num income">+ ¥ {{ money(breakdown.total?.income) }}</td>
                <td class="c-num expense">− ¥ {{ money(breakdown.total?.expense) }}</td>
                <td class="c-num">{{ breakdown.total?.count || 0 }}</td>
                <td class="c-num" :class="(breakdown.total?.balance || 0) >= 0 ? 'income' : 'expense'">
                  {{ (breakdown.total?.balance || 0) >= 0 ? '+' : '−' }} ¥ {{ money(Math.abs(breakdown.total?.balance || 0)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="fin-members-empty">{{ unitLabel }}暂无流水</div>
      </section>

      <!-- 图表区 -->
      <section class="fin-charts">
        <div class="fin-chart glass">
          <h2 class="fin-chart-title">{{ unitLabel }}支出分类占比</h2>
          <div v-if="summary.categories.length" class="fin-chart-body">
            <DonutChart :data="summary.categories" />
            <ul class="fin-legend">
              <li v-for="c in summary.categories" :key="c.category" class="fin-legend-item">
                <i class="fin-dot" :style="{ background: c.color }"></i>
                <span class="fin-legend-name">{{ c.icon }} {{ c.category }}</span>
                <span class="fin-legend-pct">{{ pct(c.amount) }}%</span>
                <span class="fin-legend-amt">¥ {{ money(c.amount) }}</span>
              </li>
            </ul>
          </div>
          <div v-else class="fin-chart-empty">{{ unitLabel }}暂无支出，去「记一笔」吧</div>
        </div>

        <div class="fin-chart glass">
          <h2 class="fin-chart-title">{{ unitLabel }}收支趋势</h2>
          <div v-if="dim !== 'day' && summary.trends.length" class="fin-chart-body">
            <TrendChart :days="summary.trends" :has-any="hasAnyTrend" />
          </div>
          <div v-else class="fin-chart-empty">{{ dim === 'day' ? '单日无跨期趋势，切换「月/年」查看' : '暂无数据' }}</div>
        </div>
      </section>
      </template>

      <!-- ===== 存款 / 公款 Tab：单池看板 ===== -->
      <template v-if="activeTab === 'savings' || activeTab === 'public'">
        <section class="fin-panel">
          <div class="fin-pool-hero glass" :class="activeTab">
            <div class="fin-pool-hero-left">
              <span class="fin-pool-hero-icon">{{ FUND_META[activeTab].icon }}</span>
              <div>
                <h2 class="fin-panel-title">{{ FUND_META[activeTab].label }}</h2>
                <p class="fin-panel-sub">累计转入 ¥ {{ money(activePool.inflow) }} · 累计已用 ¥ {{ money(activePool.outflow) }}</p>
              </div>
            </div>
            <div class="fin-pool-hero-right">
              <span class="fin-pool-hero-label">当前余额</span>
              <span class="fin-pool-hero-val" :class="{ neg: activePool.balance < 0 }">¥ {{ money(activePool.balance) }}</span>
              <span v-if="activePool.balance < 0" class="fin-pool-over">已透支</span>
            </div>
          </div>

          <div class="fin-chart glass">
            <h2 class="fin-chart-title">各人各月转入</h2>
            <FundMatrix v-if="matrixRows.length" :rows="matrixRows" :members="matrixMembers" />
            <div v-else class="fin-chart-empty">还没有转入记录</div>
          </div>

          <div class="fin-chart glass">
            <h2 class="fin-chart-title">{{ FUND_META[activeTab].label }}流水</h2>
            <div v-if="poolTxns.length" class="fin-list">
              <div v-for="row in poolTxns" :key="row.id" class="fin-row">
                <div class="fin-row-icon">{{ row.category_icon }}</div>
                <div class="fin-row-main">
                  <div class="fin-row-top">
                    <span class="fin-row-cat">{{ row.category }}</span>
                    <span class="fin-row-note">{{ row.note }}</span>
                  </div>
                  <div class="fin-row-date">
                    <span v-if="row.member" class="fin-row-member">{{ row.member.avatar }} {{ row.member.name }}</span>
                    {{ fmtDay(row.occurred_at) }}
                  </div>
                </div>
                <div class="fin-row-amt" :class="row.type">
                  {{ row.type === 'income' ? '+' : (row.type === 'transfer' ? '⇄' : '−') }} ¥ {{ money(row.amount) }}
                </div>
                <div class="fin-row-ops">
                  <button class="fin-op" title="编辑" @click="openEdit(row)">✎</button>
                </div>
              </div>
            </div>
            <div v-else class="fin-chart-empty">该池还没有流水</div>
          </div>
        </section>
      </template>

      <!-- ===== 个人零花 Tab：按人拆开 ===== -->
      <template v-if="activeTab === 'personal'">
        <section class="fin-panel">
          <div class="fin-pcards">
            <div v-for="p in funds.personal_by_member || []" :key="p.user_id" class="fin-pcard glass">
              <span class="fin-pcard-avatar">{{ p.avatar }}</span>
              <span class="fin-pcard-name">{{ p.name }}</span>
              <span class="fin-pcard-val" :class="{ neg: p.balance < 0 }">¥ {{ money(p.balance) }}</span>
              <span v-if="p.balance < 0" class="fin-pool-over">已透支</span>
              <span class="fin-pcard-sub">累计转入 ¥ {{ money(p.inflow) }} · 已花 ¥ {{ money(p.outflow) }}</span>
            </div>
            <div v-if="!(funds.personal_by_member || []).length" class="fin-chart-empty">还没有个人零花记录</div>
          </div>

          <div class="fin-chart glass">
            <h2 class="fin-chart-title">各人各月转入</h2>
            <FundMatrix v-if="matrixRows.length" :rows="matrixRows" :members="matrixMembers" />
            <div v-else class="fin-chart-empty">还没有转入记录</div>
          </div>
        </section>
      </template>

      <!-- ===== 流水 Tab ===== -->
      <section v-if="activeTab === 'ledger'" class="fin-ledger glass">
        <div class="fin-ledger-head">
          <h2 class="fin-chart-title">流水明细</h2>
          <div class="fin-filters">
            <span v-if="memberFilter" class="fin-filter-chip">
              仅看 {{ activeMemberName }}
              <button class="fin-filter-chip-x" @click="pickMember('')">✕</button>
            </span>
            <el-select v-model="filters.type" placeholder="全部类型" clearable class="fin-filter" @change="onFilterChange">
              <el-option label="支出" value="expense" />
              <el-option label="收入" value="income" />
              <el-option label="调拨" value="transfer" />
            </el-select>
            <el-select v-model="filters.fund" placeholder="全部资金池" clearable class="fin-filter" @change="onFilterChange">
              <el-option label="个人零花" value="personal" />
              <el-option label="公款" value="public" />
              <el-option label="存款" value="savings" />
            </el-select>
            <input v-model="filters.q" class="fin-filter-input" placeholder="搜索备注/分类…" @keyup.enter="onFilterChange" />
            <button class="fin-btn ghost small" @click="onFilterChange">查询</button>
          </div>
        </div>

        <!-- 「只看未归类」时的复位入口 -->
        <div v-if="unclassifiedOnly" class="fin-batch glass">
          <span class="fin-batch-text">正在只看 <b>未归类</b> 的流水（起算日之后）</span>
          <button class="fin-batch-clear" @click="onFilterChange">显示全部</button>
        </div>

        <!-- 批量改归属条：勾选多行后出现 -->
        <div v-if="checkedIds.length" class="fin-batch glass">
          <span class="fin-batch-text">已选 <b>{{ checkedIds.length }}</b> 笔，批量改归属：</span>
          <button v-for="f in FUND_ORDER" :key="f" class="fin-btn ghost small" @click="applyBatchFund(f)">{{ FUND_META[f].label }}</button>
          <button class="fin-btn ghost small" @click="applyBatchFund('none')">未归类</button>
          <button class="fin-batch-clear" @click="checkedIds = []">取消选择</button>
        </div>

        <div class="fin-list">
          <div v-if="!list.length" class="fin-list-empty">还没有符合条件的流水</div>
          <div v-else>
            <div v-for="row in list" :key="row.id" class="fin-row" :class="{ editing: form.editing && form.editingId === row.id }">
              <label class="fin-row-check">
                <input type="checkbox" :checked="checkedIds.includes(row.id)" @change="toggleCheck(row.id)" />
              </label>
              <div class="fin-row-icon">{{ row.category_icon }}</div>
              <div class="fin-row-main">
                <div class="fin-row-top">
                  <span class="fin-row-cat">{{ row.category }}</span>
                  <!-- 资金池徽标：点击直接进编辑表单改归属（不新增弹窗） -->
                  <button
                    class="fin-fund-badge"
                    :class="[row.fund, { todo: row.fund === 'none' && row.type !== 'transfer' }]"
                    :title="row.type === 'transfer' ? '点击编辑' : '点击修改归属'"
                    @click="openEdit(row)"
                  >
                    <template v-if="row.type === 'transfer'">{{ row.fund_label }} → {{ row.fund_to_label }}</template>
                    <template v-else>{{ row.fund === 'none' ? '未归类' : row.fund_label }}</template>
                  </button>
                  <span class="fin-row-note">{{ row.note }}</span>
                </div>
                <div class="fin-row-date">
                  <span v-if="row.member" class="fin-row-member">{{ row.member.avatar }} {{ row.member.name }}</span>
                  {{ fmtDay(row.occurred_at) }}
                </div>
              </div>
              <div class="fin-row-amt" :class="row.type">
                {{ row.type === 'income' ? '+' : (row.type === 'transfer' ? '⇄' : '−') }} ¥ {{ money(row.amount) }}
              </div>
              <div class="fin-row-ops">
                <button class="fin-op" title="编辑" @click="openEdit(row)">✎</button>
                <el-popconfirm
                  title="确认删除这条流水？"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  width="220"
                  @confirm="del(row)"
                >
                  <template #reference>
                    <button class="fin-op danger" title="删除">🗑</button>
                  </template>
                </el-popconfirm>
              </div>
            </div>

            <div class="fin-pager">
              <span class="fin-pager-info">共 {{ total }} 笔</span>
              <el-pagination
                layout="prev, pager, next"
                :total="total"
                :page-size="pageSize"
                :current-page="page"
                background
                size="small"
                @current-change="onPage"
              />
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- ============ 分类管理弹窗 ============ -->
    <div class="fin-cat-dialog">
      <el-dialog
        v-model="catDialog"
        :title="catDialogTitle"
        width="520px"
        :close-on-click-modal="false"
      >
        <!-- 自定义分类 -->
        <div class="fin-cd-section">
          <div class="fin-cd-head">
            <span class="fin-cd-title">自定义分类</span>
            <span class="fin-cd-note">改名会同步更新已记账的流水，不会留下「孤儿分类」</span>
          </div>

          <div v-if="customCats.length" class="fin-cd-list">
            <div v-for="c in customCats" :key="c.id" class="fin-cd-row">
              <el-select v-model="c.icon" class="fin-cd-icon" @change="(v) => saveCat(c, c.key, v)">
                <el-option v-for="e in ICON_PRESETS" :key="e" :label="e" :value="e" />
              </el-select>
              <el-input
                :model-value="c.key"
                class="fin-cd-name"
                maxlength="12"
                show-word-limit
                @change="(v) => saveCat(c, v, c.icon)"
              />
              <el-popconfirm
                title="删除后不再出现在选择列表；已记账的流水仍保留这个分类名"
                confirm-button-text="删除"
                cancel-button-text="取消"
                width="240"
                @confirm="removeCat(c)"
              >
                <template #reference>
                  <el-button link type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <p v-else class="fin-cd-empty">还没有自定义分类，用下面的输入框加一个。</p>

          <div class="fin-cd-add">
            <el-select v-model="newCat.icon" class="fin-cd-icon">
              <el-option v-for="e in ICON_PRESETS" :key="e" :label="e" :value="e" />
            </el-select>
            <el-input
              v-model="newCat.name"
              class="fin-cd-name"
              maxlength="12"
              placeholder="如：宠物、通勤、房贷"
              @keyup.enter="addCat"
            />
            <el-button type="primary" :loading="catSaving" @click="addCat">添加</el-button>
          </div>
        </div>

        <!-- 内置分类（只读） -->
        <div class="fin-cd-section">
          <div class="fin-cd-head">
            <span class="fin-cd-title">内置分类</span>
            <span class="fin-cd-note">系统自带，不可修改删除</span>
          </div>
          <div class="fin-cd-builtin">
            <span v-for="c in builtinCats" :key="c.key" class="fin-cd-chip">{{ c.icon }} {{ c.key }}</span>
          </div>
        </div>

        <template #footer>
          <el-button @click="catDialog = false">关闭</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import VoiceInputButton from '@/components/VoiceInputButton.vue'
import DonutChart from '@/components/finance/DonutChart.vue'
import TrendChart from '@/components/finance/TrendChart.vue'
import FundMatrix from '@/components/finance/FundMatrix.vue'
import { financeApi, exportFinanceCsv } from '@/api/finance'
import { listMembers } from '@/api/life'
import { useAuthStore } from '@/stores/auth'

function backToTopScroll() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const auth = useAuthStore()

const typeTabs = [
  { key: 'expense', label: '支出' },
  { key: 'income', label: '收入' },
  { key: 'transfer', label: '调拨' },
]

/* ---- v2.42 公私账：资金池 ---- */
const FUND_ORDER = ['savings', 'public', 'personal']
const FUND_META = {
  savings: { label: '存款', icon: '🏦' },
  public: { label: '公款', icon: '🏛️' },
  personal: { label: '个人零花', icon: '👛' },
}
// 调拨常用理由：纯前端常量，点了只是往备注里填字，不落库
const TRANSFER_TAGS = ['公款补充', '月末归集', '临时周转', '个人退款']

const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'savings', label: '存款' },
  { key: 'public', label: '公款' },
  { key: 'personal', label: '个人' },
  { key: 'ledger', label: '流水' },
]
const activeTab = ref('overview')

const funds = ref({ pools: [], monthly_by_member: [], personal_by_member: [], unclassified: 0 })
const poolTxns = ref([])
const checkedIds = ref([])

const poolCards = computed(() => {
  const byFund = new Map((funds.value.pools || []).map((p) => [p.fund, p]))
  return FUND_ORDER.map((f) => byFund.get(f) || {
    fund: f, label: FUND_META[f].label, inflow: 0, outflow: 0, balance: 0,
  })
})

function poolOf(fund) {
  return (funds.value.pools || []).find((p) => p.fund === fund) || {
    fund, label: FUND_META[fund]?.label || '', inflow: 0, outflow: 0, balance: 0,
  }
}
const activePool = computed(() => poolOf(activeTab.value))

// 矩阵：行=月份（新的在上），列=家庭成员并集
const matrixRows = computed(() => {
  const fund = activeTab.value === 'personal' ? 'personal' : activeTab.value
  return (funds.value.monthly_by_member || [])
    .filter((r) => r.fund === fund)
    .slice()
    .sort((a, b) => (a.month < b.month ? 1 : -1))
})
const matrixMembers = computed(() => {
  const seen = new Map()
  for (const r of funds.value.monthly_by_member || []) {
    for (const m of r.members || []) if (!seen.has(m.user_id)) seen.set(m.user_id, m)
  }
  return [...seen.values()]
})

async function loadFunds() {
  try {
    const res = await financeApi.funds()
    funds.value = res.data || { pools: [], monthly_by_member: [], personal_by_member: [], unclassified: 0 }
  } catch {
    // 池子总览拉不到不该影响记账主流程，静默降级为空池
  }
}

async function loadPoolTxns() {
  if (activeTab.value !== 'savings' && activeTab.value !== 'public') { poolTxns.value = []; return }
  try {
    const res = await financeApi.list({ fund: activeTab.value, size: 50, page: 1 })
    poolTxns.value = res.data?.list || []
  } catch {
    poolTxns.value = []
  }
}

function openPool(fund) {
  activeTab.value = activeTab.value === fund ? 'overview' : fund
}

function showUnclassified() {
  activeTab.value = 'ledger'
  filters.type = ''
  filters.fund = ''
  filters.q = ''
  unclassifiedOnly.value = true
  checkedIds.value = []
  page.value = 1
  loadList()
}

function toggleCheck(id) {
  const i = checkedIds.value.indexOf(id)
  if (i >= 0) checkedIds.value.splice(i, 1)
  else checkedIds.value.push(id)
}

async function applyBatchFund(fund) {
  if (!checkedIds.value.length) return
  try {
    const res = await financeApi.batchFund({ ids: checkedIds.value, fund })
    ElMessage.success(res.msg || '已更新归属')
    checkedIds.value = []
    await Promise.all([loadFunds(), loadList(), loadPeriodStats()])
  } catch { /* 错误已由 api 拦截器提示 */ }
}

const PALETTE = ['#7FA8A3', '#C7A96B', '#6E8BA6', '#B98BA6', '#8BB07A', '#C98B6B', '#6FA6C9', '#A98BC9', '#7F8FA3']

const now = new Date()
const pad = (n) => String(n).padStart(2, '0')
const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
const dim = ref('month')
const day = ref(today)
const month = ref(`${now.getFullYear()}-${pad(now.getMonth() + 1)}`)
const year = ref(String(now.getFullYear()))
const summary = ref({ categories: [], trends: [], balance: 0 })
const categoriesMeta = ref({ expense: [], income: [] })
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const saving = ref(false)

const filters = reactive({ type: '', q: '', fund: '' })
// 「去归类」进来的只看未归类流水；后端按起算日过滤，历史数据不算「待归类」
const unclassifiedOnly = ref(false)

/* ---- 人员标签 + 家人汇总 ---- */
// '' = 全部家人；否则是创建者 user_id（后端 member_user_id 过滤）
const memberFilter = ref('')
const members = ref([])
const breakdown = ref({ members: [], total: {} })

// 标签来源：家庭成员档案 ∪ 汇总里出现过的创建者（含已注销账号的历史流水）
const memberTags = computed(() => {
  const bmap = new Map((breakdown.value.members || []).map((m) => [m.user_id, m]))
  const seen = new Set()
  const out = []
  for (const m of members.value) {
    const b = bmap.get(m.user_id)
    out.push({
      user_id: m.user_id,
      name: m.display_name || `成员${m.user_id}`,
      avatar: m.avatar || '🌿',
      expense: b?.expense || 0,
    })
    seen.add(m.user_id)
  }
  for (const b of breakdown.value.members || []) {
    if (seen.has(b.user_id)) continue
    out.push({ user_id: b.user_id, name: b.name, avatar: b.avatar || '👤', expense: b.expense || 0 })
  }
  return out
})

const activeMemberName = computed(() => {
  const hit = memberTags.value.find((m) => String(m.user_id) === String(memberFilter.value))
  return hit ? hit.name : '家人'
})

function pickMember(uid) {
  const next = uid === '' || uid == null ? '' : uid
  memberFilter.value = String(memberFilter.value) === String(next) ? '' : next
  page.value = 1
  loadSummary()
  loadList()
}

async function loadMembers() {
  try {
    const res = await listMembers()
    members.value = res?.data?.list || []
  } catch {
    members.value = []
  }
}

async function loadBreakdown() {
  const params = { dim: dim.value }
  if (dim.value === 'day') params.day = day.value
  else if (dim.value === 'year') params.year = year.value
  else params.month = month.value
  const res = await financeApi.memberBreakdown(params)
  breakdown.value = res.data || { members: [], total: {} }
}

// 周期内的三个口径一起刷：KPI/图表、家人汇总、流水列表
function loadPeriodStats() {
  return Promise.all([loadSummary(), loadBreakdown()])
}

const form = reactive({
  show: false,
  editing: false,
  editingId: null,
  type: 'expense',
  amount: null,
  date: fmtDate(now),
  category: '餐饮',
  note: '',
  // v2.42 公私账：资金池归属
  //   income → 钱进入的池 / expense → 钱花出的池 / transfer → fundFrom 转出、fundTo 转入
  fund: 'none',
  fundFrom: 'personal',
  fundTo: 'public',
  // 归属人：只有涉及「个人零花」时才需要指定这是谁的零花
  member: null,
})

/* ---- 归属人（谁的零花） ---- */
// 涉及个人零花才问「是谁的」：公款/存款是全家共用的，问归属人没有意义
const needOwner = computed(() => {
  if (form.type === 'transfer') return form.fundFrom === 'personal' || form.fundTo === 'personal'
  return form.fund === 'personal'
})
// 优先用家庭档案（有头像与昵称），档案还没加载出来时退回当前登录人
const ownerOptions = computed(() => {
  if (members.value.length) {
    return members.value.map((m) => ({
      user_id: m.user_id,
      name: m.display_name || `成员${m.user_id}`,
      avatar: m.avatar || '🌿',
    }))
  }
  return [{ user_id: Number(auth.user?.id) || 0, name: auth.user?.nickname || '我', avatar: '👤' }]
})

// 切换资金池时，顺手把归属人补成当前登录人（个人零花最常用自己）
function pickFund(f) {
  form.fund = f
  if (f === 'personal' && form.member == null) form.member = Number(auth.user?.id) || null
}

const periodLabel = computed(() => {
  if (dim.value === 'day') {
    const [y, m, d] = day.value.split('-')
    return `${y}年${Number(m)}月${Number(d)}日`
  }
  if (dim.value === 'year') return `${year.value}年`
  const [y, m] = month.value.split('-')
  return `${y}年${Number(m)}月`
})
const isNowPeriod = computed(() => {
  if (dim.value === 'day') return day.value === today
  if (dim.value === 'year') return year.value === String(now.getFullYear())
  return month.value === `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
})
const unitLabel = computed(() => (dim.value === 'day' ? '今日' : (dim.value === 'year' ? '本年' : '本月')))

const ddOpen = ref(false)
const ddYear = ref(now.getFullYear())
const ddMonth = ref(now.getMonth() + 1)
const ddYearList = ref(null)
const yearOptions = computed(() => {
  const max = now.getFullYear()
  const min = Math.min(summary.value.min_year || max, max)
  const arr = []
  for (let y = max; y >= min; y--) arr.push(y)
  return arr
})
const ddDays = computed(() => new Date(ddYear.value, ddMonth.value, 0).getDate())
const ddSelDay = computed(() => {
  if (dim.value !== 'day') return 0
  const [y, m, d] = day.value.split('-').map(Number)
  return (y === ddYear.value && m === ddMonth.value) ? d : 0
})
function toggleDd() {
  if (ddOpen.value) { ddOpen.value = false; return }
  if (dim.value === 'year') {
    ddYear.value = parseInt(year.value) || now.getFullYear()
    ddMonth.value = 1
  } else if (dim.value === 'day') {
    const [y, m] = day.value.split('-').map(Number)
    ddYear.value = y; ddMonth.value = m
  } else {
    const [y, m] = month.value.split('-').map(Number)
    ddYear.value = y; ddMonth.value = m
  }
  ddOpen.value = true
  nextTick(() => {
    const el = ddYearList.value
    if (!el) return
    const active = el.querySelector('.fin-dd-item.on')
    if (active) active.scrollIntoView({ block: 'center' })
  })
}
function pickYear(y) {
  ddYear.value = y
  if (dim.value !== 'year') return
  year.value = String(y)
  closeDd()
}
function pickMonth(m) {
  if (dim.value === 'year') return
  ddMonth.value = m
  if (dim.value === 'month') {
    month.value = `${ddYear.value}-${pad(m)}`
    closeDd()
  }
}
function pickDay(d) {
  if (dim.value !== 'day') return
  day.value = `${ddYear.value}-${pad(ddMonth.value)}-${pad(d)}`
  closeDd()
}
function closeDd() {
  ddOpen.value = false
  page.value = 1
  loadPeriodStats()
  loadList()
}
function onDocClick() { if (ddOpen.value) ddOpen.value = false }
const currentCats = computed(() => {
  const pool = form.type === 'income' ? categoriesMeta.value.income : categoriesMeta.value.expense
  return pool.length ? pool : [{ key: '其他', icon: '🧾' }]
})
const hasAnyTrend = computed(() => (summary.value.trends || []).some(d => d.income || d.expense))

function money(v) { return Number(v || 0).toFixed(2) }
function pct(v) {
  const t = summary.value.categories.reduce((s, c) => s + (c.amount || 0), 0)
  if (!t) return '0'
  return ((v || 0) / t * 100).toFixed(1)
}
function fmtDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function fmtDay(iso) {
  if (!iso) return ''
  return iso.slice(0, 10)
}

async function loadCategories() {
  const res = await financeApi.categories()
  categoriesMeta.value = res.data
}

/* ---- 自定义分类管理 ---- */
// 常见图标预设：给个够用的小抄，省得用户为了一个 emoji 去翻输入法
const ICON_PRESETS = [
  '🍜', '🍚', '☕', '🛒', '🛍️', '🚇', '🚗', '✈️', '🏠', '💡',
  '🎮', '🎬', '🎵', '📚', '🎓', '💊', '🏥', '🏋️', '🐱', '🐾',
  '👶', '🎁', '🧧', '💐', '🧴', '🛠️', '📱', '💰', '📈', '🧾',
]
const catDialog = ref(false)
const catSaving = ref(false)
const newCat = ref({ icon: ICON_PRESETS[0], name: '' })

// 管理面板跟随当前收支方向：在「支出」下打开就管支出分类
const currentPool = computed(() => (
  form.type === 'income' ? categoriesMeta.value.income : categoriesMeta.value.expense
))
const customCats = computed(() => currentPool.value.filter(c => c.is_custom))
const builtinCats = computed(() => currentPool.value.filter(c => !c.is_custom))
const catDialogTitle = computed(() => (form.type === 'income' ? '管理收入分类' : '管理支出分类'))

function openCatDialog() {
  newCat.value = { icon: ICON_PRESETS[0], name: '' }
  catDialog.value = true
}

async function addCat() {
  const name = (newCat.value.name || '').trim()
  if (!name) {
    ElMessage.warning('请输入分类名')
    return
  }
  catSaving.value = true
  try {
    await financeApi.createCategory({ type: form.type, name, icon: newCat.value.icon })
    ElMessage.success(`已添加「${name}」`)
    newCat.value = { icon: newCat.value.icon, name: '' }
    await loadCategories()
  } catch { /* 错误已由 api 拦截器提示 */ } finally {
    catSaving.value = false
  }
}

async function saveCat(cat, name, icon) {
  const next = (name || '').trim()
  if (!next) {
    ElMessage.warning('分类名不能为空')
    await loadCategories()
    return
  }
  if (next === cat.key && icon === cat.icon) return
  try {
    await financeApi.updateCategory(cat.id, { type: form.type, name: next, icon })
    ElMessage.success('已更新')
    // 正在记的这笔如果选的就是它，跟着改名，否则保存时会被归成「其他」
    if (form.category === cat.key) form.category = next
    await loadCategories()
  } catch {
    await loadCategories()   // 回滚界面上的乐观改动
  }
}

async function removeCat(cat) {
  try {
    const res = await financeApi.deleteCategory(cat.id)
    ElMessage.success(res.msg || '已删除')
    if (form.category === cat.key) form.category = '其他'
    await loadCategories()
    await loadSummary()
  } catch { /* 错误已由 api 拦截器提示 */ }
}
async function loadSummary() {
  const params = { dim: dim.value }
  if (dim.value === 'day') params.day = day.value
  else if (dim.value === 'year') params.year = year.value
  else params.month = month.value
  if (memberFilter.value) params.member_user_id = memberFilter.value
  const res = await financeApi.summary(params)
  summary.value = { ...res.data, categories: (res.data.categories || []).map((c, i) => ({ ...c, color: PALETTE[i % PALETTE.length] })) }
}
function onPage(p) {
  page.value = p
  loadList()
}

async function loadList() {
  const params = { page: page.value, size: pageSize }
  if (filters.type) params.type = filters.type
  if (filters.fund) params.fund = filters.fund
  if (filters.q) params.q = filters.q
  if (memberFilter.value) params.member_user_id = memberFilter.value
  if (unclassifiedOnly.value) params.unclassified = true
  const res = await financeApi.list(params)
  list.value = res.data.list
  total.value = res.data.total
}
// 手动改筛选就退出「只看未归类」，否则用户以为自己筛了公款、其实还在未归类视图里
function onFilterChange() {
  unclassifiedOnly.value = false
  return reload(1)
}
const showImportHelp = ref(false)
async function exportCsv() {
  let start, end
  if (dim.value === 'day') {
    start = day.value
    end = day.value
  } else if (dim.value === 'year') {
    start = `${year.value}-01-01`
    end = `${year.value}-12-31`
  } else {
    const [y, m] = month.value.split('-').map(Number)
    start = `${month.value}-01`
    end = `${month.value}-${pad(new Date(y, m, 0).getDate())}`
  }
  try {
    await exportFinanceCsv({ start, end })
    ElMessage.success('CSV 已导出')
  } catch (e) {
    ElMessage.error('导出失败，请重试')
  }
}
const importing = reactive({
  analyzing: false,
  confirming: false,
  rows: [],
  skipped: 0,
  errors: [],
  summary: '',
  is_fake: false,
})

async function onImportFile(e) {
  const file = e.target.files && e.target.files[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file) return
  try {
    importing.analyzing = true
    importing.rows = []
    importing.skipped = 0
    importing.errors = []
    importing.summary = ''
    importing.is_fake = false
    const ext = (file.name.split('.').pop() || '').toLowerCase()
    const res = /^(xlsx|xlsm|xls)$/.test(ext)
      ? await financeApi.analyzeImportFile(file)
      : await financeApi.analyzeImport(await file.text())
    const d = res.data || {}
    importing.rows = d.rows || []
    importing.skipped = d.skipped || 0
    importing.errors = d.errors || []
    importing.summary = d.summary || ''
    importing.is_fake = !!d.is_fake
    if (!importing.rows.length && !importing.errors.length) ElMessage.warning('未识别到有效流水，请检查文件内容')
  } catch (err) {
    const d = err?.response?.data?.detail
    const msg = typeof d === 'string' ? d : (d?.msg || err?.message || '识别失败，请重试')
    ElMessage.error(`识别失败：${msg}`)
  } finally {
    importing.analyzing = false
  }
}

function cancelImport() {
  importing.rows = []
  importing.skipped = 0
  importing.errors = []
  importing.summary = ''
  importing.is_fake = false
  importing.analyzing = false
  importing.confirming = false
}

async function doConfirmImport() {
  if (!importing.rows.length) return
  importing.confirming = true
  try {
    const res = await financeApi.confirmImport(importing.rows)
    const d = res.data || {}
    ElMessage.success(`导入成功 ${d.imported} 条`)
    cancelImport()
    reloadAndScroll()
  } catch (err) {
    ElMessage.error('导入失败，请重试')
  } finally {
    importing.confirming = false
  }
}

function reload(p) {
  if (p) page.value = p
  return loadList()
}
function setDim(d) {
  if (dim.value === d || !['day', 'month', 'year'].includes(d)) return
  dim.value = d
  page.value = 1
  loadPeriodStats()
  loadList()
}
function shift(step) {
  if (dim.value === 'day') {
    const nv = new Date(`${day.value}T12:00:00`)
    nv.setDate(nv.getDate() + step)
    day.value = fmtDate(nv)
  } else if (dim.value === 'year') {
    year.value = String(Number(year.value) + step)
  } else {
    const [y, m] = month.value.split('-').map(Number)
    const totalM = y * 12 + (m - 1) + step
    month.value = `${Math.floor(totalM / 12)}-${pad((totalM % 12) + 1)}`
  }
  page.value = 1
  loadPeriodStats()
  loadList()
}
function goNow() {
  if (dim.value === 'day') day.value = today
  else if (dim.value === 'year') year.value = String(now.getFullYear())
  else month.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
  page.value = 1
  loadPeriodStats()
  loadList()
}
async function reloadAndScroll() {
  await Promise.all([loadPeriodStats(), reload(1)])
  backToTopScroll()
}

function resetForm() {
  form.type = 'expense'
  form.amount = null
  form.date = fmtDate(new Date())
  form.category = '餐饮'
  form.note = ''
  // 默认「未归类」而不是猜一个池子：池子归属是钱的方向，猜错会让看板数字失真，
  // 让用户明确点一下更安全（待归类的笔数会在首页提醒条里露出来）
  form.fund = 'none'
  form.fundFrom = 'personal'
  form.fundTo = 'public'
  form.member = Number(auth.user?.id) || null
}
function openNew() {
  resetForm()
  form.editing = false
  form.editingId = null
  form.show = true
  backToTopScroll()
}
function pickType(t) {
  form.type = t
  form.category = t === 'income' ? '工资' : '餐饮'
  // 调拨没有分类；切回来时补一个合法默认，避免带着「调拨」占位名去存
  if (t === 'transfer') form.note = form.note || ''
}
function openEdit(row) {
  form.show = true
  form.editing = true
  form.editingId = row.id
  form.type = row.type
  form.amount = row.amount
  form.date = fmtDay(row.occurred_at)
  form.category = row.category
  form.note = row.note
  form.fund = row.fund || 'none'
  form.fundFrom = row.type === 'transfer' ? (row.fund || 'personal') : 'personal'
  form.fundTo = row.type === 'transfer' ? (row.fund_to || 'public') : 'public'
  form.member = row.member?.user_id ?? (Number(auth.user?.id) || null)
  backToTopScroll()
}
function onVoiceNote(text) {
  form.note = form.note.trim() ? `${form.note.trim()} ${text}` : text
}
async function save() {
  if (!form.amount || form.amount <= 0) {
    ElMessage.warning('请先填写金额')
    return
  }
  const isTransfer = form.type === 'transfer'
  if (isTransfer && form.fundFrom === form.fundTo) {
    ElMessage.warning('转出和转入不能是同一个池')
    return
  }
  saving.value = true
  const payload = {
    type: form.type,
    amount: form.amount,
    category: isTransfer ? '调拨' : form.category,
    note: form.note,
    occurred_at: `${form.date || fmtDate(new Date())}T12:00:00`,
    fund: isTransfer ? form.fundFrom : form.fund,
    fund_to: isTransfer ? form.fundTo : null,
  }
  if (needOwner.value && form.member != null) payload.member_user_id = form.member
  try {
    if (form.editing) {
      await financeApi.update(form.editingId, payload)
    } else {
      await financeApi.create(payload)
    }
    form.show = false
    form.editing = false
    form.editingId = null
    await Promise.all([loadPeriodStats(), reload(1), loadFunds(), loadPoolTxns()])
  } finally {
    saving.value = false
  }
}
async function del(row) {
  await financeApi.remove(row.id)
  await Promise.all([loadPeriodStats(), loadList(), loadFunds(), loadPoolTxns()])
}

// 切 Tab 时按需拉单池流水（只有存款/公款两页需要）
watch(activeTab, () => { loadPoolTxns() })

onMounted(() => {
  loadCategories()
  loadMembers()
  loadPeriodStats()
  loadList()
  loadFunds()
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.fin-page {
  position: relative;
  min-height: 100vh;
  padding: 96px 24px 60px;
  box-sizing: border-box;
  font-family: var(--font-serif);
  color: var(--lj-text);
  overflow-x: hidden;
}
.fin-inner { position: relative; z-index: 1; max-width: 1080px; margin: 0 auto; }

.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 55% 40% at 18% 6%, var(--glow-rain), transparent 60%),
    radial-gradient(ellipse 45% 40% at 85% 26%, var(--glow-gold), transparent 60%),
    var(--lj-bg); }
.lj-paper-texture { position: absolute; inset: 0; opacity: .5;
  background:
    repeating-linear-gradient(0deg, rgba(127,168,163,.02) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(127,168,163,.014) 0 1px, transparent 1px 7px); }
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .4;
  background: radial-gradient(circle, rgba(127,168,163,.14), transparent 70%); animation: fd-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 480px; height: 400px; top: 4%; left: -8%; }
.lj-wash.w2 { width: 420px; height: 360px; bottom: 4%; right: -8%; animation-delay: 9s; }
@keyframes fd-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(32px,-18px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

.glass { background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow); }

/* 页头 */
.fin-head { display: flex; align-items: center; gap: 18px; margin-bottom: 18px; }
.fin-head-left { flex: none; }
.fin-titles { flex: 1; }
.fin-title { margin: 0; font-size: 28px; letter-spacing: .12em; }
.fin-sub { margin: 6px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .18em; }
.fin-head-right { flex: none; }

.fin-btn { border: none; cursor: pointer; border-radius: 10px; font-family: var(--font-serif);
  color: var(--lj-text); background: var(--lj-glass); border: 1px solid var(--lj-line); padding: 9px 16px; transition: all .22s; }
.fin-btn:hover { border-color: var(--lj-line-strong); }
.fin-btn.primary { background: linear-gradient(135deg, rgba(127,168,163,.55), rgba(199,169,107,.4)); color: #fff; }
.fin-btn.primary:hover { filter: brightness(1.05); box-shadow: 0 6px 18px rgba(0,0,0,.25); }
.fin-btn.ghost { background: transparent; }
.fin-btn.small { padding: 6px 12px; font-size: 13px; }

/* 月份 */
.fin-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.fin-period { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.fin-dim { display: flex; align-items: center; gap: 2px; padding: 3px; border-radius: 999px; background: rgba(127,168,163,.08);
  border: 1px solid var(--lj-line); }
.fin-dim-btn { border: 0; background: transparent; color: var(--lj-text-3); font-size: 12px; padding: 5px 14px; border-radius: 999px;
  cursor: pointer; font-family: var(--font-serif); letter-spacing: .08em; transition: all .2s; }
.fin-dim-btn:hover { color: var(--lj-text); }
.fin-dim-btn.on { color: #fff; background: var(--lj-dai); box-shadow: 0 2px 8px rgba(0,0,0,.25); }
.fin-nav { width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--lj-line); background: var(--lj-glass);
  color: var(--lj-text); font-size: 18px; cursor: pointer; transition: all .2s; }
.fin-nav:hover { border-color: var(--lj-line-strong); }
.fin-month-label { border: 1px solid var(--lj-line); background: var(--lj-glass); color: var(--lj-text);
  padding: 7px 16px; border-radius: 999px; font-family: var(--font-serif); letter-spacing: .1em; font-size: 16px;
  cursor: pointer; transition: border-color .2s; white-space: nowrap; }
.fin-month-label:hover { border-color: var(--lj-line-strong); }
.fin-this { margin-left: 8px; font-size: 11px; color: var(--lj-dai); cursor: pointer; }
.fin-dd-caret { margin-left: 8px; font-size: 12px; color: var(--lj-text-3); }
.fin-dd-wrap { position: relative; }
.fin-dd { position: absolute; top: calc(100% + 8px); left: 50%; transform: translateX(-50%); z-index: 60;
  display: flex; gap: 8px; padding: 12px; border-radius: 16px; box-shadow: 0 14px 40px rgba(0,0,0,.28); min-width: 240px; }
.fin-dd-col { display: flex; flex-direction: column; gap: 6px; min-width: 78px; }
.fin-dd-head { font-size: 11px; color: var(--lj-text-3); text-align: center; letter-spacing: .2em; padding: 2px 0; }
.fin-dd-list { max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px;
  scrollbar-width: thin; scrollbar-color: var(--lj-line-strong) transparent; padding-right: 2px; }
.fin-dd-list::-webkit-scrollbar { width: 6px; }
.fin-dd-list::-webkit-scrollbar-thumb { background: var(--lj-line-strong); border-radius: 3px; }
.fin-dd-item { border: 0; background: transparent; color: var(--lj-text-2); font-size: 13px; padding: 6px 10px;
  border-radius: 8px; cursor: pointer; font-family: var(--font-serif); transition: all .15s; text-align: center; }
.fin-dd-item:hover { background: rgba(127,168,163,.12); color: var(--lj-text); }
.fin-dd-item.on { color: #fff; background: var(--lj-dai); font-weight: 600; }

/* 导入/导出 */
.fin-io { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fin-import { position: relative; display: inline-block; margin: 0; }
.fin-import-file { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.fin-help { font-size: 12px; color: var(--lj-text-3); text-decoration: none; letter-spacing: .04em; }
.fin-help:hover { color: var(--lj-dai); }
.fin-io-help { padding: 14px 18px; border-radius: 14px; margin-bottom: 14px; }
.fin-io-help-title { margin: 0 0 8px; font-size: 14px; letter-spacing: .06em; }
.fin-io-help-line { margin: 4px 0; font-size: 12.5px; color: var(--lj-text-2); }
.fin-io-help-line code { background: rgba(127,168,163,.14); padding: 1px 6px; border-radius: 5px; color: var(--lj-seal); }

/* 智能导入预览 */
.fin-import-panel { padding: 16px 18px; border-radius: 16px; margin-bottom: 16px; }
.fin-import-panel-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.fin-import-panel-title { font-size: 15px; font-weight: 600; letter-spacing: .04em; color: var(--lj-seal); }
.fin-import-loading { font-size: 12.5px; color: var(--lj-text-2); animation: fin-pulse 1.2s ease-in-out infinite; }
.fin-import-done { font-size: 12px; padding: 2px 10px; border-radius: 999px; background: rgba(127,168,163,.16); color: var(--lj-seal); }
@keyframes fin-pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
.fin-import-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; font-size: 13px; margin-bottom: 10px; color: var(--lj-text); }
.fin-import-summary b { color: var(--lj-seal); }
.fin-import-summary b.warn { color: var(--lj-cinnabar, #c27053); }
.fin-import-ai { flex: 1 1 100%; font-size: 12.5px; color: var(--lj-text-2); font-style: italic; }
.fin-import-fake { font-size: 11.5px; padding: 2px 10px; border-radius: 999px; background: rgba(199,169,107,.18); color: var(--lj-gold, #b18a4a); }
.fin-import-errors { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-bottom: 10px; font-size: 12px; color: var(--lj-cinnabar, #c27053); }
.fin-import-empty { padding: 18px 0; text-align: center; font-size: 13px; color: var(--lj-text-2); }
.fin-import-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.fin-import-table th { text-align: left; padding: 7px 10px; font-weight: 600; font-size: 12px; color: var(--lj-text-2); border-bottom: 1px solid var(--lj-line);
  background: rgba(127,168,163,.08); }
.fin-import-table td { padding: 8px 10px; border-bottom: 1px dashed var(--lj-line); vertical-align: middle; }
.fin-import-type { display: inline-block; min-width: 24px; text-align: center; padding: 1px 8px; border-radius: 999px; font-size: 12px; }
.fin-import-type.income { background: rgba(127,168,163,.16); color: var(--lj-seal); }
.fin-import-type.expense { background: rgba(194,150,120,.18); color: var(--lj-cinnabar, #c27053); }
.fin-import-amt { white-space: nowrap; font-variant-numeric: tabular-nums; }
.fin-import-amt.income { color: var(--lj-seal); }
.fin-import-amt.expense { color: var(--lj-cinnabar, #c27053); }
.fin-import-note { color: var(--lj-text-2); max-width: 260px; }
.fin-import-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 14px; }

/* 记一笔面板 */
.fin-form { border-radius: 16px; padding: 18px 20px; margin-bottom: 18px; }
.fin-form-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.fin-form-title { font-size: 16px; letter-spacing: .08em; }
.fin-form-edit-tag { font-size: 12px; color: var(--lj-ochre); }
.fin-form-close { margin-left: auto; border: none; background: transparent; color: var(--lj-text-2); font-size: 16px; cursor: pointer; }
.fin-form-body { display: flex; flex-direction: column; gap: 14px; }
.fin-f-type { display: flex; gap: 8px; }
.fin-tab { flex: 1; padding: 9px; border-radius: 10px; border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .22s; font-family: var(--font-serif); }
.fin-tab.active { border-color: var(--lj-seal); color: var(--lj-seal); background: rgba(127,168,163,.12); }
.fin-f-row { display: flex; gap: 16px; flex-wrap: wrap; }
.fin-f-field { flex: 1; min-width: 220px; }
.fin-f-field.grow { flex: 1.4; }
.fin-f-label { display: block; font-size: 12px; color: var(--lj-text-2); margin-bottom: 6px; letter-spacing: .06em; }
.fin-amount { width: 100%; }
.fin-date { width: 100%; }
.fin-cats { display: flex; flex-wrap: wrap; gap: 8px; }
.fin-cat { padding: 6px 12px; border-radius: 999px; border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .2s; font-family: var(--font-serif); font-size: 13px; }
.fin-cat.active { border-color: var(--lj-ochre); color: var(--lj-ochre); background: rgba(199,169,107,.14); }
.fin-f-label-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.fin-cat-manage { background: none; border: none; padding: 0; cursor: pointer; font-size: 12px; color: var(--lj-ochre); font-family: var(--font-serif); letter-spacing: .04em; }
.fin-cat-manage:hover { text-decoration: underline; }

/* 分类管理弹窗 */
.fin-cd-section { margin-bottom: 20px; }
.fin-cd-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.fin-cd-title { font-size: 14px; color: var(--lj-text); letter-spacing: .06em; }
.fin-cd-note { font-size: 12px; color: var(--lj-text-3); }
.fin-cd-list { display: flex; flex-direction: column; gap: 8px; }
.fin-cd-row, .fin-cd-add { display: flex; align-items: center; gap: 8px; }
.fin-cd-icon { width: 76px; flex: none; }
.fin-cd-name { flex: 1; }
.fin-cd-empty { font-size: 13px; color: var(--lj-text-3); margin: 0 0 10px; }
.fin-cd-add { margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--lj-line); }
.fin-cd-builtin { display: flex; flex-wrap: wrap; gap: 8px; }
.fin-cd-chip { padding: 4px 10px; border-radius: 999px; border: 1px solid var(--lj-line); font-size: 12px; color: var(--lj-text-3); }
.fin-note-row { display: flex; align-items: center; gap: 8px; }
.fin-note-input { flex: 1; padding: 9px 12px; border-radius: 10px; border: 1px solid var(--lj-line); background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); outline: none; }
.fin-note-input:focus { border-color: var(--lj-seal); }
.fin-form-actions { display: flex; justify-content: flex-end; gap: 10px; }
.fd-enter-active,.fd-leave-active { transition: all .28s ease; }
.fd-enter-from,.fd-leave-to { opacity: 0; transform: translateY(-10px); }

/* KPI */
.fin-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 18px; }
.fin-kpi { display: flex; flex-direction: column; gap: 6px; padding: 18px; border-radius: 16px; position: relative; overflow: hidden; }
.fin-kpi::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--lj-dai), transparent); opacity: .45; }
.fin-kpi-label { font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.fin-kpi-val { font-size: 22px; font-weight: 600; letter-spacing: .02em; }
.fin-kpi-val.income { color: var(--lj-ochre); }
.fin-kpi-val.expense { color: var(--lj-vermilion); }
.fin-kpi-sub { font-size: 11px; color: var(--lj-text-3); }

/* ===== 公私账：三个资金池卡片（核心视觉锚点） =====
   池子配色各成一系，与「收入/支出」的红金语义区分开：
   存款→鎏金、公款→雨青、个人零花→青莲。全部走 --pool-accent 一个变量，
   描边、顶部微光条、选中态共用，改色只改一行。 */
.fin-pools { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
.fin-pool { --pool-accent: var(--lj-line-strong); position: relative; display: flex; flex-direction: column;
  align-items: flex-start; gap: 6px; padding: 18px; border-radius: 16px; overflow: hidden;
  cursor: pointer; text-align: left; font-family: var(--font-serif); color: var(--lj-text);
  transition: transform .22s, border-color .22s, box-shadow .22s; }
.fin-pool::after { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--pool-accent), transparent); opacity: .5; }
.fin-pool:hover { transform: translateY(-2px); border-color: var(--lj-line-strong); }
.fin-pool.on { border-color: var(--pool-accent); box-shadow: inset 0 0 0 1px var(--pool-accent); }
.fin-pool.savings { --pool-accent: var(--yq-gold); }
.fin-pool.public { --pool-accent: var(--yq-rain); }
.fin-pool.personal { --pool-accent: #8d7fa8; }
.fin-pool-top { display: flex; align-items: center; gap: 8px; }
.fin-pool-icon { font-size: 17px; line-height: 1; }
.fin-pool-name { font-size: 13px; color: var(--lj-text-2); letter-spacing: .1em; }
.fin-pool-val { font-size: clamp(21px, 2.6vw, 27px); font-weight: 700; letter-spacing: -.01em;
  font-variant-numeric: tabular-nums; }
.fin-pool-val.neg { color: var(--lj-vermilion); }
.fin-pool-flags { font-size: 11px; }
.fin-pool-ok { color: var(--lj-text-3); }
.fin-pool-sub { font-size: 11.5px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.fin-pool-over { display: inline-block; padding: 1px 8px; border-radius: 999px;
  background: var(--lj-seal-soft); color: var(--lj-seal); }

/* 待归类提醒条：只统计起算日之后的流水 */
.fin-todo { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  padding: 12px 16px; border-radius: 14px; margin-bottom: 14px; border-color: rgba(199,169,107,.42); }
.fin-todo-text { font-size: 13px; color: var(--lj-text-2); }
.fin-todo-text b { color: var(--lj-ochre); }

/* 分栏 Tab（总览/存款/公款/个人/流水） */
.fin-tabs { display: flex; gap: 4px; padding: 4px; border-radius: 999px; margin-bottom: 18px;
  background: rgba(127,168,163,.08); border: 1px solid var(--lj-line);
  overflow-x: auto; scrollbar-width: none; }
.fin-tabs::-webkit-scrollbar { display: none; }
.fin-tab-item { flex: 1; min-width: 66px; border: 0; background: transparent; color: var(--lj-text-3);
  font-family: var(--font-serif); font-size: 13px; letter-spacing: .08em; padding: 8px 16px;
  border-radius: 999px; cursor: pointer; white-space: nowrap; transition: all .2s; }
.fin-tab-item:hover { color: var(--lj-text); }
.fin-tab-item.on { color: #fff; background: var(--lj-dai); box-shadow: 0 2px 8px rgba(0,0,0,.22); }

/* 单池看板（存款 / 公款） */
.fin-panel { display: flex; flex-direction: column; gap: 16px; margin-bottom: 18px; }
.fin-pool-hero { display: flex; align-items: center; justify-content: space-between; gap: 18px;
  flex-wrap: wrap; padding: 20px; border-radius: 16px; }
.fin-pool-hero-left { display: flex; align-items: center; gap: 14px; min-width: 0; }
.fin-pool-hero-icon { font-size: 34px; line-height: 1; flex: none; }
.fin-panel-title { margin: 0; font-size: 20px; letter-spacing: .1em; }
.fin-panel-sub { margin: 6px 0 0; font-size: 12.5px; color: var(--lj-text-2); }
.fin-pool-hero-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.fin-pool-hero-label { font-size: 11.5px; color: var(--lj-text-3); letter-spacing: .1em; }
.fin-pool-hero-val { font-size: clamp(25px, 3.6vw, 33px); font-weight: 700; font-variant-numeric: tabular-nums; }
.fin-pool-hero.savings .fin-pool-hero-val { color: var(--yq-gold); }
.fin-pool-hero.public .fin-pool-hero-val { color: var(--yq-rain); }
/* 放在着色规则之后，透支时盖过池子主色（同特异性、靠后生效） */
.fin-pool-hero .fin-pool-hero-val.neg { color: var(--lj-vermilion); }

/* 个人零花：每人一张卡 */
.fin-pcards { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 14px; }
.fin-pcard { display: flex; flex-direction: column; align-items: flex-start; gap: 6px;
  padding: 18px; border-radius: 16px; }
.fin-pcard-avatar { font-size: 20px; line-height: 1; }
.fin-pcard-name { font-size: 13px; color: var(--lj-text-2); letter-spacing: .08em; }
.fin-pcard-val { font-size: 25px; font-weight: 700; font-variant-numeric: tabular-nums; }
.fin-pcard-val.neg { color: var(--lj-vermilion); }
.fin-pcard-sub { font-size: 11.5px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }

/* 批量改归属条 */
.fin-batch { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px 14px;
  border-radius: 12px; margin-bottom: 10px; border-color: rgba(127,168,163,.35); }
.fin-batch-text { font-size: 13px; color: var(--lj-text-2); }
.fin-batch-text b { color: var(--lj-seal); }
.fin-batch-clear { margin-left: auto; border: none; background: transparent; color: var(--lj-text-3);
  font-size: 12px; cursor: pointer; font-family: var(--font-serif); }
.fin-batch-clear:hover { color: var(--lj-text); }

/* 流水行：勾选框 + 资金池徽标 */
.fin-row-check { display: flex; align-items: center; flex: none; cursor: pointer; }
.fin-row-check input { width: 15px; height: 15px; accent-color: var(--lj-dai); cursor: pointer; }
.fin-fund-badge { border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-3);
  font-family: var(--font-serif); font-size: 11.5px; padding: 2px 9px; border-radius: 999px;
  cursor: pointer; white-space: nowrap; transition: all .2s; }
.fin-fund-badge:hover { border-color: var(--lj-line-strong); color: var(--lj-text); }
.fin-fund-badge.savings { color: var(--yq-gold); border-color: rgba(199,169,107,.45); }
.fin-fund-badge.public { color: var(--yq-rain); border-color: rgba(127,168,163,.45); }
.fin-fund-badge.personal { color: #8d7fa8; border-color: rgba(141,127,168,.45); }
.fin-fund-badge.todo { border-style: dashed; }

/* 记一笔：资金池选择器 + 调拨方向 */
.fin-f-hint { font-size: 11.5px; color: var(--lj-text-3); letter-spacing: .06em; }
.fin-transfer-row { display: flex; align-items: center; gap: 10px; }
.fin-transfer-sel { flex: 1; min-width: 0; }
.fin-transfer-arrow { flex: none; color: var(--lj-seal); font-size: 16px; }
.fin-quick-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.fin-quick-label { font-size: 11.5px; color: var(--lj-text-3); letter-spacing: .06em; }
.fin-quick-tag { padding: 5px 12px; border-radius: 999px; border: 1px solid var(--lj-line);
  background: transparent; color: var(--lj-text-2); font-family: var(--font-serif); font-size: 12.5px;
  cursor: pointer; transition: all .2s; }
.fin-quick-tag:hover { border-color: var(--lj-line-strong); color: var(--lj-text); }
.fin-quick-tag.on { border-color: var(--lj-ochre); color: var(--lj-ochre); background: rgba(199,169,107,.14); }
.fin-funds { display: flex; flex-wrap: wrap; gap: 8px; }
.fin-fund { padding: 6px 12px; border-radius: 999px; border: 1px solid var(--lj-line);
  background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .2s;
  font-family: var(--font-serif); font-size: 13px; }
.fin-fund:hover { border-color: var(--lj-line-strong); color: var(--lj-text); }
.fin-fund.active { border-color: var(--lj-seal); color: var(--lj-seal); background: rgba(127,168,163,.12); }
.fin-fund.active.savings { border-color: var(--yq-gold); color: var(--yq-gold); background: rgba(199,169,107,.14); }
.fin-fund.active.public { border-color: var(--yq-rain); color: var(--yq-rain); background: rgba(127,168,163,.16); }
.fin-fund.active.personal { border-color: #8d7fa8; color: #8d7fa8; background: rgba(141,127,168,.14); }

/* 家人账目：人员标签 + 汇总表 */
.fin-members { border-radius: 16px; padding: 18px; margin-bottom: 18px; }
.fin-members-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.fin-members-head .fin-chart-title { margin: 0; }
.fin-members-hint { font-size: 12px; color: var(--lj-text-3); }
.fin-mtags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.fin-mtag { display: inline-flex; align-items: center; gap: 7px; padding: 6px 13px; border-radius: 999px;
  border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer;
  font-family: var(--font-serif); font-size: 13px; transition: all .2s; }
.fin-mtag:hover { border-color: var(--lj-line-strong); color: var(--lj-text); }
.fin-mtag.on { border-color: var(--lj-seal); color: var(--lj-seal); background: rgba(127,168,163,.14); }
.fin-mtag-avatar { font-size: 15px; line-height: 1; }
.fin-mtag-amt { font-size: 12px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.fin-mtag.on .fin-mtag-amt { color: var(--lj-seal); }
.fin-mtable-wrap { overflow-x: auto; }
.fin-mtable { width: 100%; border-collapse: collapse; font-size: 13px; }
.fin-mtable th { text-align: right; padding: 8px 10px; font-size: 12px; font-weight: 600; color: var(--lj-text-2);
  border-bottom: 1px solid var(--lj-line); white-space: nowrap; }
.fin-mtable th.c-name, .fin-mtable td.c-name { text-align: left; }
.fin-mtable td { padding: 9px 10px; border-bottom: 1px dashed var(--lj-line); text-align: right;
  white-space: nowrap; font-variant-numeric: tabular-nums; }
.fin-mtable td.income { color: var(--lj-ochre); }
.fin-mtable td.expense { color: var(--lj-vermilion); }
.fin-mtr { cursor: pointer; transition: background .2s; }
.fin-mtr:hover { background: rgba(127,168,163,.06); }
.fin-mtr.on { background: rgba(127,168,163,.12); }
.fin-mtr.total { font-weight: 600; background: rgba(199,169,107,.08); cursor: default; }
.fin-mtr.total td { border-bottom: none; }
.fin-mtd-avatar { margin-right: 6px; }
.fin-members-empty { padding: 22px 6px; text-align: center; font-size: 13px; color: var(--lj-text-3); }
.fin-filter-chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px;
  font-size: 12px; color: var(--lj-seal); background: rgba(127,168,163,.14); border: 1px solid var(--lj-line); }
.fin-filter-chip-x { border: none; background: transparent; color: inherit; cursor: pointer; font-size: 12px; padding: 0; }
.fin-row-member { color: var(--lj-seal); margin-right: 6px; }

/* 图表 */
.fin-charts { display: grid; grid-template-columns: 1fr 1.4fr; gap: 16px; margin-bottom: 18px; }
.fin-chart { border-radius: 16px; padding: 18px; }
.fin-chart-title { margin: 0 0 14px; font-size: 15px; letter-spacing: .08em; }
.fin-chart-body { display: flex; gap: 18px; align-items: center; }
.fin-chart-empty { padding: 30px 6px; font-size: 13px; color: var(--lj-text-3); text-align: center; }
.fin-legend { list-style: none; margin: 0; padding: 0; flex: 1; display: flex; flex-direction: column; gap: 8px; max-height: 220px; overflow: auto; }
.fin-legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.fin-dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
.fin-legend-name { flex: 1; color: var(--lj-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fin-legend-pct { flex: none; font-size: 12px; color: var(--lj-seal); font-weight: 600; font-variant-numeric: tabular-nums; width: 46px; text-align: right; }
.fin-legend-amt { color: var(--lj-text); font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }

/* 流水 */
.fin-ledger { border-radius: 16px; padding: 18px; }
.fin-ledger-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 12px; flex-wrap: wrap; }
.fin-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fin-filter { width: 130px; }
.fin-filter-input { padding: 7px 11px; border-radius: 9px; border: 1px solid var(--lj-line); background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); outline: none; width: 180px; }
.fin-filter-input:focus { border-color: var(--lj-seal); }
.fin-list-empty { padding: 40px 6px; text-align: center; color: var(--lj-text-3); font-size: 13px; }
.fin-row { display: flex; align-items: center; gap: 12px; padding: 11px 8px; border-radius: 12px; transition: background .2s; }
.fin-row:hover { background: rgba(127,168,163,.06); }
.fin-row.editing { background: rgba(199,169,107,.10); box-shadow: inset 0 0 0 1px var(--lj-line); }
.fin-row + .fin-row { border-top: 1px solid rgba(127,168,163,.07); }
.fin-row-icon { width: 40px; height: 40px; flex: none; display: grid; place-items: center; font-size: 20px; border-radius: 12px; background: rgba(127,168,163,.12); }
.fin-row-main { flex: 1; min-width: 0; }
.fin-row-top { display: flex; align-items: center; gap: 8px; }
.fin-row-cat { font-size: 14px; font-weight: 600; }
.fin-row-note { font-size: 13px; color: var(--lj-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fin-row-date { font-size: 11px; color: var(--lj-text-3); margin-top: 3px; }
.fin-row-amt { font-size: 16px; font-weight: 600; white-space: nowrap; }
.fin-row-amt.income { color: var(--lj-ochre); }
.fin-row-amt.expense { color: var(--lj-vermilion); }
.fin-row-ops { display: flex; gap: 6px; }
.fin-op { width: 32px; height: 32px; border-radius: 9px; border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .2s; }
.fin-op:hover { border-color: var(--lj-seal); color: var(--lj-seal); }
.fin-op.danger:hover { border-color: var(--lj-vermilion); color: var(--lj-vermilion); }
.fin-pager { display: flex; align-items: center; justify-content: flex-end; gap: 14px; margin-top: 14px; }
.fin-pager-info { font-size: 12px; color: var(--lj-text-3); }

@media (max-width: 900px) {
  .fin-kpis { grid-template-columns: repeat(2, 1fr); }
  .fin-charts { grid-template-columns: 1fr; }
  .fin-pool-val { font-size: 20px; }
  .fin-pool { padding: 14px; }
}
@media (max-width: 560px) {
  .fin-page { padding: 88px 14px 50px; }
  .fin-kpis { grid-template-columns: 1fr 1fr; }
  .fin-title { font-size: 22px; }
  .fin-members { padding: 14px; }
  .fin-mtag { padding: 5px 11px; font-size: 12px; }
  .fin-mtable { font-size: 12px; }
  .fin-mtable th, .fin-mtable td { padding: 7px 8px; }
  /* 三张池子卡挤在一行会看不清金额：改成可横滑的一行，卡宽固定 */
  .fin-pools { grid-template-columns: repeat(3, minmax(158px, 1fr)); gap: 10px;
    overflow-x: auto; padding-bottom: 4px; scrollbar-width: none; }
  .fin-pools::-webkit-scrollbar { display: none; }
  .fin-pool { padding: 13px; }
  .fin-pool-sub { font-size: 11px; }
  .fin-pool-hero { padding: 16px; }
  .fin-pool-hero-val { font-size: 26px; }
  .fin-pcard { padding: 15px; }
  .fin-tab-item { padding: 8px 13px; font-size: 12.5px; }
  .fin-transfer-row { gap: 6px; }
  .fin-batch-clear { margin-left: 0; }
}
</style>
