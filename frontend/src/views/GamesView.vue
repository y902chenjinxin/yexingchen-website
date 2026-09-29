<template>
  <IslandInnerBase type="tool" title="棋类游戏" subtitle="五子棋 · 围棋 · 象棋 · 军棋 · 飞行棋 · 数独 · 扫雷 · 贪吃蛇">
    <div class="gm-root" :class="{ 'is-big': isBig, 'is-fill': !!cur.fill }">
      <!-- ===== 左：游戏类型 ===== -->
      <aside v-show="!isBig" class="gm-rail">
        <div v-for="grp in groups" :key="grp.name" class="gm-grp">
          <div class="gm-grp-name">{{ grp.name }}</div>
          <button
            v-for="g in grp.items"
            :key="g.key"
            class="gm-item"
            :class="{ on: tab === g.key, dim: itemLocked(g) }"
            :disabled="itemLocked(g)"
            :title="itemLocked(g) ? '对局进行中 —— 退出对局后才能切换' : ''"
            @click="pick(g.key)"
          >
            <!-- eslint-disable-next-line vue/no-v-html -- 图标为本地常量字符串，无外部输入 -->
            <span class="gm-item-ic" v-html="g.icon"></span>
            <span class="gm-item-tx">
              <b>{{ g.label }}</b>
              <i>{{ g.tag }}</i>
            </span>
            <span v-if="saves[g.key]" class="gm-item-dot" title="有未完成的存档"></span>
          </button>
        </div>
      </aside>

      <!-- ===== 右：游戏空间 ===== -->
      <section ref="stageRef" class="gm-stage">
        <!-- 空态：默认什么都不摆，避免一屏平铺 -->
        <div v-if="!tab" class="gm-empty">
          <div class="gm-empty-ic">♟</div>
          <b>从左边挑一个游戏</b>
          <p>选中后先选模式，再进对局。想看得舒服一点，进去后可点「放大」全屏玩，随时能退出或续上进度。</p>
        </div>

        <template v-else>
          <header class="gm-head">
            <div class="gm-head-tx">
              <b>{{ cur.label }}</b>
              <i>{{ cur.desc }}</i>
            </div>
            <div class="gm-head-ops">
              <span v-if="roomLocked" class="gm-locktip">🔒 对局进行中</span>
              <button v-if="phase === 'play' && cur.rules?.length" class="gm-op" @click="showRules = !showRules">
                {{ showRules ? '收起说明' : '游戏说明' }}
              </button>
              <button class="gm-op" @click="toggleBig">{{ isBig ? '退出全屏' : '放大' }}</button>
              <button class="gm-op ghost" @click="backToList">返回列表</button>
            </div>
          </header>

          <!-- 第一步：先选模式 -->
          <div v-if="phase === 'setup'" class="gm-setup">
            <div class="gm-setup-bar">
              <div class="gm-setup-title">选择模式</div>
              <button v-if="cur.rules?.length" class="gm-rulesbtn" @click="showRules = !showRules">
                <span class="gm-rulesbtn-ic">{{ showRules ? '−' : '?' }}</span>
                {{ showRules ? '收起说明' : '游戏说明' }}
              </button>
            </div>
            <div v-if="showRules && cur.rules?.length" class="gm-rules">
              <div v-for="(r, ri) in cur.rules" :key="ri" class="gm-rule">
                <i class="gm-rule-dot"></i>{{ r }}
              </div>
            </div>
            <div class="gm-modecards">
              <button
                v-for="m in cur.modes"
                :key="m.key"
                class="gm-modecard"
                @click="startGame(m.key)"
              >
                <b>{{ m.label }}</b>
                <i>{{ m.hint }}</i>
              </button>
            </div>
            <div v-if="cur.boardSizes" class="gm-size">
              <span class="gm-size-label">棋盘大小</span>
              <button
                v-for="s in cur.boardSizes"
                :key="s"
                class="gm-sizebtn"
                :class="{ on: chosenBoard === s }"
                @click="chosenBoard = s"
              >{{ s }}×{{ s }}</button>
              <span class="gm-size-hint">开局定好就不再变（在线对战固定 15×15）</span>
            </div>
            <button v-if="saves[tab]" class="gm-resume" @click="resumeGame">
              ▶ 继续上一局 · {{ saves[tab].summary }}
              <em>{{ age(saves[tab].ts) }}</em>
            </button>
          </div>

          <!-- 第二步：对局 -->
          <div v-else class="gm-play">
            <div v-if="showRules && cur.rules?.length" class="gm-rules gm-rules--play">
              <div v-for="(r, ri) in cur.rules" :key="ri" class="gm-rule">
                <i class="gm-rule-dot"></i>{{ r }}
              </div>
            </div>
            <component
              :is="cur.component"
              :key="runKey"
              :game-key="cur.key"
              :initial-mode="chosenMode"
              :board-size="chosenBoard"
              :resume="resumeFlag"
              :bare="true"
              :big="isBig"
              :join-room-id="pendingRoom.game === cur.key ? pendingRoom.id : 0"
              @room-lock="roomLocked = true"
              @room-unlock="roomLocked = false"
              @exit="backToList"
            />
          </div>
        </template>
      </section>
    </div>
  </IslandInnerBase>
</template>

<script setup>
/** 棋类游戏（v2.40.29 交互重构）。
 *
 * 布局：左「游戏类型」栏 + 右「游戏空间」，默认空态（不预渲染任何棋盘）；
 * 分步：选类型 → 选模式 → 进对局，避免一屏平铺；
 * 大屏：舞台容器全屏化（fixed），组件**不重新挂载**，因此对局与进度天然保留；
 * 进度：自研游戏写 localStorage 存档（utils/gameSave），回列表后可「继续上一局」。
 * 加新游戏 = 写一个自包含组件 + 在 gamelist 加一行（modes/boardSizes/big 声明能力）。
 * v2.40.33：按夜星要求**黑白棋下架**（不是他要的），换成**围棋**（新组件 GoBoard.vue，中国规则数子法）。
 * v2.40.40：确认删除已下架的 OthelloBoard.vue（组件与图标一并移除，归档 artifacts/_deleted_deadcode/）。
 * v2.40.34：飞行棋由 iframe 嵌第三方静态页（LudoEmbed.vue）改为**自写 LudoBoard.vue** ——
 *           原方案的「选择人数」弹层被 iframe 高度裁切，点了人数看不到「开始游戏」按钮（表现为点了没反应），
 *           且第三方是同屏多人、无联机能力，无法「邀请家人」。现在支持 2/3/4 人同屏 + 在线邀请。
 */
import { ref, reactive, computed, watch, nextTick, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { loadGame, clearGame, saveAge } from '@/utils/gameSave'

const ICON = {
  gomoku: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/><circle cx="9" cy="9" r="2" fill="currentColor" stroke="none"/></svg>',
  ludo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 4v16M4 12h16"/><circle cx="8.2" cy="8.2" r="1.4" fill="currentColor" stroke="none"/><circle cx="15.8" cy="15.8" r="1.4" fill="currentColor" stroke="none"/></svg>',
  sudoku: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M9.2 3.5v17M14.8 3.5v17M3.5 9.2h17M3.5 14.8h17"/></svg>',
  mine: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="13" r="6"/><path d="M12 7V3M4.6 10.6 2 8M19.4 10.6 22 8M7 19l-2 2M17 19l2 2"/></svg>',
  go: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3.5" y="3.5" width="17" height="17" rx="2"/><path d="M9.2 3.5v17M14.8 3.5v17M3.5 9.2h17M3.5 14.8h17"/><circle cx="9.2" cy="9.2" r="2" fill="currentColor" stroke="none"/><circle cx="14.8" cy="14.8" r="2" fill="currentColor" stroke="none"/></svg>',
  snake: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 17h7a3 3 0 0 0 3-3V8a3 3 0 0 1 3-3h2"/><rect x="2" y="15.5" width="2.6" height="2.6" rx="1" fill="currentColor" stroke="none"/><circle cx="18.6" cy="4.6" r="1.5" fill="currentColor" stroke="none"/></svg>',
  xiangqi: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M3.6 6.6h16.8M3.6 17.4h16.8M6.6 3.6v16.8M17.4 3.6v16.8"/><circle cx="12" cy="12" r="4.4"/><path d="M9.9 12h4.2M12 9.9v4.2"/></svg>',
  xiangqi_flip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3.4" y="4.4" width="8.4" height="15.2" rx="2"/><path d="M6.4 9.4h2.4M6.4 12h2.4M6.4 14.6h2.4"/><path d="M15.4 9a4.4 4.4 0 0 1 0 6"/><path d="M15.2 7.2l.5 2-2 .4"/></svg>',
  junqi: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6.2 21V3.4"/><path d="M6.2 4.4h11.2l-2.5 3.3 2.5 3.3H6.2"/></svg>',
  junqi_flip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3.2" y="4.6" width="8" height="14.8" rx="2"/><path d="M5.9 9.2h2.6M5.9 12h2.6M5.9 14.8h2.6"/><path d="M15.4 9a4.4 4.4 0 0 1 0 6"/><path d="M15.2 7.2l.5 2-2 .4"/></svg>',
}

const gamelist = [
  {
    key: 'gomoku', label: '五子棋', tag: '15×15 · AI 三档', group: '棋类',
    desc: '五子连珠取胜；同屏双人、单机陪练，或在线邀请家人。',
    icon: ICON.gomoku,
    fill: true,                 // 放大时用「定高两栏」布局：棋盘占左侧主位、其余移右侧辅栏
    component: defineAsyncComponent(() => import('@/components/games/GomokuBoard.vue')),
    boardSizes: [15, 19, 23],   // 开局可选棋盘大小（对局中固定，不自动变化）
    rules: [
      '目标：黑先白后轮流落子，先在横、竖、斜任一方向连成 5 子者获胜。',
      '操作：点棋盘交叉点落子；开局前可切换棋盘大小（15/19/23 路），开局后固定。',
      '单机：简单＝AI 只看一步，适合陪练；困难＝AI 三层搜索，会堵会攻。',
      '在线：建房邀请家人，跨设备同步，对方落子约 2 秒内自动出现。',
      '悔棋：每方每局 3 次（仅在线对局提供）。',
    ],
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着下' },
      { key: 'easy', label: '单机 · 简单', hint: 'AI 只看一步，适合陪练' },
      { key: 'hard', label: '单机 · 困难', hint: 'AI 三层搜索，会堵会攻' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，跨设备同步' },
    ],
  },
  {
    key: 'go', label: '围棋', tag: '9/13/19 路 · 入门 AI', group: '棋类',
    desc: '气与提子、禁自杀、打劫；双方各停一手后自动数子（中国规则，黑贴 7.5 目）。',
    icon: ICON.go,
    fill: true,                 // 放大时用「定高两栏」布局：棋盘占左侧主位、其余移右侧辅栏
    component: defineAsyncComponent(() => import('@/components/games/GoBoard.vue')),
    boardSizes: [9, 13, 19],
    rules: [
      '目标：中国规则数子，黑贴 7.5 目，占地（子＋空）多者胜。',
      '提子：一块棋没有「气」（上下左右紧邻的空点）就会被提掉。',
      '禁着：不能自杀（落子后自己无气且提不到对方）；打劫不能立即提回，需隔一手。',
      '操作：点交叉点落子；不下了就点「停一手」，双方各停一手后自动数子判胜负。',
      '棋盘：可选 9 / 13 / 19 路，开局后固定。',
    ],
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着下' },
      { key: 'easy', label: '单机 · 入门', hint: 'AI 会吃子、会逃跑，但不强' },
      { key: 'hard', label: '单机 · 稍强', hint: '多看一层；仍是入门水平' },
    ],
  },
  {
    key: 'xiangqi', label: '象棋', tag: '明棋 · AI 三档', group: '棋类',
    desc: '标准象棋规则：马蹩腿、象塞眼不过河、炮隔子吃、将帅不可照面；无子可动即负。',
    icon: ICON.xiangqi,
    fill: true,
    component: defineAsyncComponent(() => import('@/components/games/XiangqiBoard.vue')),
    rules: [
      '目标：将死或困毙（无子可动）对方的将/帅即胜。',
      '车：直线任意格；马：走「日」字，蹩马腿时不能走；象/相：走「田」字，塞象眼时不能走，且不能过河。',
      '士/仕：九宫内走斜线；将/帅：九宫内走一步，双方将帅不能在同一直线上照面。',
      '炮：不吃子时同车走直线；吃子时必须隔一个棋子（炮架）。',
      '兵/卒：只能向前一步，过河后可以横走，永不后退。',
      '操作：点自己的棋子选中，再点目标格落子；可走位置会有高亮提示。',
    ],
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着走' },
      { key: 'easy', label: '单机 · 简单', hint: 'AI 只看一步，适合陪练' },
      { key: 'hard', label: '单机 · 困难', hint: 'AI 三层搜索，会攻会守' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，跨设备同步' },
    ],
  },
  {
    key: 'xiangqi_flip', label: '象棋翻棋', tag: '暗棋 · 随机撒子', group: '棋类',
    desc: '标准 9×10 棋盘，32 子背面随机撒盘，先翻定色；翻开后按棋子自身的真实走法行动（车直行、马蹩腿、炮隔子吃、兵过河横走），吃将即胜。',
    icon: ICON.xiangqi_flip,
    fill: true,
    component: defineAsyncComponent(() => import('@/components/games/XiangqiFlipBoard.vue')),
    rules: [
      '开局：32 枚棋子背面朝上随机撒在标准 9×10 棋盘上，双方轮流行动。',
      '定色：先手翻出的第一枚棋子颜色决定归属 —— 翻出红子即执红，另一方执黑。',
      '行动：每次可以翻一枚暗子，或走一枚己方明子。',
      '走法：明子严格按棋子自身走法行动 —— 车走直线、马走「日」蹩腿、炮隔子吃、兵向前一步（过河可横走）、士斜走一格、象走田且塞象眼、将走一格。',
      '说明：因棋子随机撒盘，士/象/将不再受九宫与河界限制，否则被撒到界外就永远动不了。',
      '限制：未翻开的暗子不能移动、也不能被吃，但会挡路、可当炮架。',
      '胜负：吃掉对方的将/帅即胜；一方无子可动（无暗子可翻且无明子可走）即负。',
      '在线：牌面按房间号播种生成，两端完全一致。',
    ],
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着翻' },
      { key: 'easy', label: '单机 · 电脑', hint: 'AI 会翻子、会吃子' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，牌面按房号同步' },
    ],
  },
  {
    key: 'junqi', label: '军棋', tag: '明棋 · 铁路行营', group: '棋类',
    desc: '12×5 棋盘，铁路快行、行营免攻、大本营驻子不动；军衔吃子，同级同归于尽。',
    icon: ICON.junqi,
    fill: true,
    component: defineAsyncComponent(() => import('@/components/games/JunqiBoard.vue')),
    rules: [
      '目标：夺下对方的军旗即胜。',
      '大小：司令＞军长＞师长＞旅长＞团长＞营长＞连长＞排长＞工兵；同级相遇同归于尽。',
      '炸弹：与任何棋子相遇（含司令）都同归于尽；地雷：不能移动，只有工兵能挖，其他子碰雷被吃。',
      '军旗：不可移动；被对方棋子碰到即被夺，对局结束。',
      '铁路：在铁路上可直线走多格；只有工兵能在铁路上拐弯。',
      '行营：行营内的棋子不受攻击（安全岛）；大本营：棋子进入后不可再移动。',
      '操作：点自己的棋子选中，再点目标格移动。',
    ],
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着走' },
      { key: 'easy', label: '单机 · 电脑', hint: 'AI 贪心吃子' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，跨设备同步' },
    ],
  },
  {
    key: 'junqi_flip', label: '军棋翻棋', tag: '暗棋 · 先清雷后拔旗', group: '棋类',
    desc: '50 子随机背面撒盘，先翻定色；工兵可拐弯排雷，吃光对方三颗地雷后才能拔旗。',
    icon: ICON.junqi_flip,
    fill: true,
    component: defineAsyncComponent(() => import('@/components/games/JunqiBoard.vue')),
    rules: [
      '开局：50 枚棋子背面随机撒在 12×5 棋盘的非行营格，双方轮流翻子。',
      '定色：先手翻出的第一枚棋子颜色决定归属，另一方执另一色。',
      '大小：司令＞军长＞师长＞旅长＞团长＞营长＞连长＞排长＞工兵；同级相遇同归于尽。',
      '炸弹：与任何棋子相遇都同归于尽；地雷：不能移动，只有工兵能挖，其他子碰雷被吃。',
      '移动：按铁路（可走多格）或相邻格走一步；只有工兵能在铁路上拐弯。',
      '胜负：必须先吃光对方 3 颗地雷，才能拔掉对方军旗。',
      '限制：未翻开的棋子不能移动，只能翻；翻开后按真实棋子行动。',
    ],
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着翻' },
      { key: 'easy', label: '单机 · 电脑', hint: 'AI 贪心翻吃' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，牌面按房号同步' },
    ],
  },
  {
    key: 'ludo', label: '飞行棋', tag: '中国规则 · 大屏', group: '棋类', big: true,
    desc: '掷 6 起飞、踩同色飞跃、飞行通道直飞；双人/三人/四人同屏，或在线邀请家人。',
    icon: ICON.ludo,
    component: defineAsyncComponent(() => import('@/components/games/LudoBoard.vue')),
    rules: [
      '目标：把自己的 4 架飞机全部送回中心「归航」，先完成者获胜。',
      '起飞：掷出 6 点才能从基地起飞到起点。',
      '再掷：掷出 6 点、或击落对方飞机，都可以再掷一次。',
      '同色格：踩到自己颜色的格子，可以再前进 4 格。',
      '飞行通道：走到第 18 格会触发飞行通道，直接向前飞 12 格。',
      '归航：必须用正好的点数进入终点，超出会弹回相应格数。',
      '击落：落到对方飞机所在格，把它送回基地。',
      '操作：点「掷骰」→ 点要走的飞机；模式支持双人/三人/四人同屏，或在线邀请家人（2 人）。',
    ],
    modes: [
      { key: 'pvp2', label: '双人同屏', hint: '红 vs 黄，一台设备轮着掷' },
      { key: 'pvp3', label: '三人同屏', hint: '红绿黄混战，谁先归航' },
      { key: 'pvp4', label: '四人同屏', hint: '四色全上，最热闹' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，跨设备同步' },
    ],
  },
  {
    key: 'sudoku', label: '数独', tag: '唯一解 · 三档', group: '益智',
    desc: '挖洞带唯一解校验；填错标红，卡住可提示一格。',
    icon: ICON.sudoku,
    component: defineAsyncComponent(() => import('@/components/games/SudokuBoard.vue')),
    rules: [
      '目标：在 9×9 格中填入 1–9，使每行、每列、每个 3×3 宫内的数字都不重复。',
      '操作：先点一个空格选中，再点下方数字键填入；点 ⌫ 清除已填的数字。',
      '提示：填错（同行/列/宫重复）会标红；同一数字会淡色联动高亮，方便定位。',
      '卡住：点「提示一格」帮你填一个正确的格子（该格会永久固定）。',
      '难度：入门挖 38 洞、进阶 45 洞、困难 52 洞，每局都保证唯一解。',
    ],
    modes: [
      { key: 'easy', label: '入门', hint: '挖 38 洞，轻松热手' },
      { key: 'mid', label: '进阶', hint: '挖 45 洞，需要点耐心' },
      { key: 'hard', label: '困难', hint: '挖 52 洞，慢慢来' },
    ],
  },
  {
    key: 'mine', label: '扫雷', tag: '10×10 · 15 雷', group: '益智',
    desc: '经典扫雷，手机上可开「旗子模式」代替右键。',
    icon: ICON.mine,
    component: defineAsyncComponent(() => import('@/components/games/MineGame.vue')),
    rules: [
      '目标：10×10 棋盘上藏有 15 颗雷，把所有雷标出来且不踩雷即通关。',
      '开始：进页面先点「开始游戏」，之后才能翻开格子。',
      '翻开：点格子翻开；数字表示它周围 8 格里的雷数；翻到空白格会自动展开一片。',
      '插旗：电脑端右键标雷；手机端勾选「旗子模式（手机用）」后，点格子即为插旗。',
      '胜负：踩到雷即失败（雷区全亮）；把所有雷正确标出即通关。',
    ],
    modes: null,
  },
  {
    key: 'snake', label: '贪吃蛇', tag: '最高分记录', group: '休闲',
    desc: '经典贪吃蛇，记录本机最高分。',
    icon: ICON.snake,
    component: defineAsyncComponent(() => import('@/components/games/SnakeGame.vue')),
    rules: [
      '目标：操控小蛇吃红色食物，每吃一个得 10 分，蛇身随之变长。',
      '开始：点「开始游戏」，或直接按任意方向键开局。',
      '操作：用键盘方向键转向；电脑端无需先点棋盘，按方向键即可控制。',
      '结束：撞到自己的身体即结束（走到边缘会从另一侧穿出，不会撞墙）。',
      '记录：本机最高分会自动保存，下次进入仍会显示。',
    ],
    modes: null,
  },
]
const ALL = Object.fromEntries(gamelist.map(g => [g.key, g]))
const groups = ['棋类', '益智', '休闲']
  .map(name => ({ name, items: gamelist.filter(g => g.group === name) }))
  .filter(g => g.items.length)

/* ---------- 状态 ---------- */
const tab = ref('')            // '' = 空态（默认什么都不摆）
const phase = ref('setup')     // setup=选模式 / play=对局
const chosenMode = ref('')
const chosenBoard = ref(15)   // 开局棋盘边长（五子棋可选 15/19/23）
const resumeFlag = ref(false)
const runId = ref(0)           // 变更即强制重新挂载组件（开新局）
const isBig = ref(false)       // 舞台全屏
const roomLocked = ref(false)  // 在线对局进行中 → 锁左栏
const pendingRoom = ref({ id: 0, game: '' })
const showRules = ref(false)   // 「游戏说明」内联展开（无弹窗）

const cur = computed(() => ALL[tab.value] || {})
const runKey = computed(() => `${tab.value}-${runId.value}`)

const saves = reactive({})
function refreshSaves() {
  for (const g of gamelist) saves[g.key] = loadGame(g.key)
}
refreshSaves()
const age = saveAge

function itemLocked(g) {
  return roomLocked.value && tab.value && g.key !== tab.value
}

/* ---------- 分步流程 ---------- */
function pick(key) {
  const g = ALL[key]
  if (!g) return
  if (itemLocked(g)) { ElMessage.warning('对局进行中 —— 先点「退出对局」再切换'); return }
  tab.value = key
  chosenMode.value = ''
  chosenBoard.value = g.boardSizes ? g.boardSizes[0] : 15
  resumeFlag.value = false
  isBig.value = !!g.big
  phase.value = g.modes ? 'setup' : 'play'
  showRules.value = false
  runId.value += 1
  refreshSaves()
}

function startGame(modeKey) {
  clearGame(tab.value)         // 开新局 → 旧存档作废
  refreshSaves()
  chosenMode.value = modeKey
  resumeFlag.value = false
  phase.value = 'play'
  runId.value += 1
}

function resumeGame() {
  const s = saves[tab.value]
  if (!s) return
  chosenMode.value = s.mode || ''
  resumeFlag.value = true
  phase.value = 'play'
  runId.value += 1
}

function backToList() {
  if (roomLocked.value) { ElMessage.warning('对局进行中 —— 先「退出对局（认输）」再离开'); return }
  isBig.value = false
  refreshSaves()
  tab.value = ''
  phase.value = 'setup'
  chosenMode.value = ''
  showRules.value = false
  runId.value += 1
}

function toggleBig() { isBig.value = !isBig.value }

/* 大屏要把整座岛抬到应用侧栏(90)/顶栏(1000)之上。
 * 坑：.island-inner / .inner-content 自身是 position:relative + z-index:1 —— **自成层叠上下文**，
 * 子树里再大的 z-index 也只能在 z=1 这一层里排，于是 fixed 舞台会被侧栏盖住。
 * 所以必须抬祖先，而不是加大屏自己的 z-index。 */
const stageRef = ref(null)
function raiseHost(on) {
  let p = stageRef.value?.parentElement
  while (p && p !== document.body) {
    if (p.classList?.contains('inner-content') || p.classList?.contains('island-inner')) {
      p.style.zIndex = on ? '1200' : ''
    }
    p = p.parentElement
  }
}
watch(isBig, async (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  await nextTick()
  raiseHost(v)
})
onBeforeUnmount(() => { document.body.style.overflow = ''; raiseHost(false) })

/* ---------- 从全局邀请弹窗跳进来（/tool/games?room=ID&game=gomoku） ----------
 * ⚠️ 清 URL 参数**绝不能**用 router.replace({query:{}})：App.vue 的 RouterView 是
 * `:key="route.fullPath"`，URL 一变整页就销毁重建、刚设好的 tab/phase 全丢 ——
 * 这正是「接受邀请后回到空态、进不去对局」的根因（桌面端同样中招，上一版用 sessionStorage
 * 兜底也只是亡羊补牢）。这里直接改 history，不触发 vue-router 导航，状态原地保留。
 * 保留 history.state（含 router 内部字段），避免前进/后退信息错乱。 */
const route = useRoute()

function enterRoom(id, game) {
  pendingRoom.value = { id, game }
  tab.value = game
  chosenMode.value = 'online'
  resumeFlag.value = false
  phase.value = 'play'          // 受邀方直接进对局，不再走模式选择
  isBig.value = false
  showRules.value = false
  runId.value += 1
}

watch(() => route.query.room, (v) => {
  const id = Number(v) || 0
  const game = String(route.query.game || '')
  if (!id || !ALL[game]) return
  enterRoom(id, game)
  try { window.history.replaceState(window.history.state, '', route.path) } catch { /* 忽略 */ }
}, { immediate: true })
</script>

<style scoped>
/* ===== 布局：左栏 + 舞台 ===== */
.gm-root {
  display: grid; grid-template-columns: 232px minmax(0, 1fr); gap: 18px;
  align-items: start; width: 100%;
}
/* 大屏：压过应用侧栏(90/95)与顶栏，整屏沉浸；头部吸顶，保证「退出全屏/返回列表」随时可点 */
.gm-root.is-big .gm-stage {
  position: fixed; inset: 0; z-index: 400; overflow-y: auto;
  background: var(--dp-bg, #f7f5f0); padding: 14px 24px 36px;
}
.gm-root.is-big .gm-head {
  position: sticky; top: 0; z-index: 3; background: var(--dp-bg, #f7f5f0);
  padding: 8px 0 10px; box-shadow: 0 8px 16px -12px rgba(20, 30, 40, .5);
}
/* 「定高两栏」放大（五子棋）：头部独立成行、棋局区自己滚动。
   此前是「吸顶头部 + 整页滚动」，玩家条会被吸顶头部压住 → 看着像顶部凸出来一块。
   现在头部占 grid 第一行、内容占第二行，两者永不重叠。 */
.gm-root.is-big.is-fill .gm-stage {
  display: grid; grid-template-rows: auto minmax(0, 1fr); gap: 8px;
  overflow: hidden; padding: 12px 20px 16px;
}
.gm-root.is-big.is-fill .gm-head {
  position: static; box-shadow: none; padding: 2px 0 10px;
  border-bottom: 1px solid var(--dp-line, rgba(0, 0, 0, .08));
}
.gm-root.is-big.is-fill .gm-play {
  min-height: 0; height: 100%; width: 100%; max-width: 1320px; margin: 0 auto;
  overflow-y: auto; overflow-x: hidden;
}

/* ===== 左栏 ===== */
.gm-rail { display: flex; flex-direction: column; gap: 16px; }
.gm-grp { display: flex; flex-direction: column; gap: 6px; }
.gm-grp-name {
  font-size: 11.5px; letter-spacing: .08em; color: var(--dp-text3, #8a8f98);
  padding: 0 4px 4px; font-weight: 600;
}
.gm-item {
  display: flex; align-items: center; gap: 10px; width: 100%; text-align: left;
  padding: 9px 11px; border-radius: 13px; cursor: pointer; font-family: inherit;
  border: 1px solid transparent; background: transparent; transition: all .18s;
  position: relative;
}
/* 悬停/选中都走玻璃 + 鎏金，不用 `--dp-surface`：夜间它是 #0d0d18，压在更亮的岛屿底上
   反而比背景更暗，选中项看着像「凹进去」；硬编码的 rgba(255,255,255,.6) 又会糊成灰块。 */
.gm-item:hover {
  background: var(--color-bg-glass, rgba(127,127,127,.06));
  border-color: var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
}
.gm-item.on {
  background: var(--yq-gold-faint, rgba(199,169,107,.16));
  border-color: var(--yq-gold, #c7a96b);
  box-shadow: 0 6px 18px var(--yq-gold-glow, rgba(199,169,107,.16));
}
/* 左侧鎏金竖条：比整块底色更醒目，且不依赖主题亮度 */
.gm-item.on::before {
  content: ''; position: absolute; left: 0; top: 50%; width: 3px; height: 22px;
  margin-top: -11px; border-radius: 0 3px 3px 0; background: var(--yq-gold, #c7a96b);
}
/* 鎏金字：白天用 --yq-gold-deep(#92400e, 7:1)，夜间回落到 --yq-gold-bright(#FDE68A) */
.gm-item.on .gm-item-tx b { color: var(--yq-gold-deep, var(--yq-gold-bright, var(--yq-gold, #c7a96b))); }
.gm-item.on .gm-item-tx i { color: var(--dp-text2, #8a8f98); }
.gm-item.dim { opacity: .38; cursor: not-allowed; }
.gm-item-ic { width: 22px; height: 22px; flex: none; color: var(--yq-gold, #c7a96b); }
.gm-item-ic :deep(svg) { width: 22px; height: 22px; display: block; }
.gm-item-tx { min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.gm-item-tx b { font-size: 13.5px; color: var(--dp-text, #18202a); font-weight: 600; }
.gm-item-tx i { font-style: normal; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.gm-item-dot {
  position: absolute; right: 10px; top: 50%; margin-top: -3px; width: 6px; height: 6px;
  border-radius: 50%; background: var(--yq-gold, #c7a96b);
}

/* ===== 舞台 ===== */
.gm-stage { min-height: 340px; display: flex; flex-direction: column; gap: 14px; }
/* 空态：毛玻璃面板 + 金色柔光锚点 + 淡棋盘格纹理。
   夜间主题下不能再用半透明白（会和纯黑背景糊成一块灰砖），统一走全站玻璃 token。 */
.gm-empty {
  position: relative; overflow: hidden;
  flex: 1; min-height: 320px; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 12px; text-align: center; padding: 44px 24px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  border-radius: 20px;
  background: var(--color-bg-glass, rgba(255,255,255,.6));
  backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  box-shadow: var(--shadow-glass, 0 8px 24px rgba(20,30,40,.08));
}
.gm-empty::before {
  content: ''; position: absolute; left: 50%; top: 36%; width: 440px; height: 280px;
  transform: translate(-50%, -50%);
  background: radial-gradient(closest-side, var(--yq-gold-faint, rgba(199,169,107,.16)), transparent 72%);
}
.gm-empty::after {
  content: ''; position: absolute; inset: 0; z-index: 0; opacity: .55;
  background-image:
    repeating-linear-gradient(to right, var(--dp-line, rgba(0,0,0,.08)) 0 1px, transparent 1px 34px),
    repeating-linear-gradient(to bottom, var(--dp-line, rgba(0,0,0,.08)) 0 1px, transparent 1px 34px);
  -webkit-mask-image: radial-gradient(62% 62% at 50% 44%, #000, transparent 78%);
  mask-image: radial-gradient(62% 62% at 50% 44%, #000, transparent 78%);
}
.gm-empty > * { position: relative; z-index: 1; }
.gm-empty-ic {
  width: 76px; height: 76px; display: grid; place-items: center;
  border-radius: 24px; font-size: 36px; line-height: 1;
  color: var(--yq-gold, #c7a96b);
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.14)));
  background: var(--color-bg-glass, rgba(255,255,255,.5));
  box-shadow: var(--glass-highlight, inset 0 1px 0 rgba(255,255,255,.6));
}
.gm-empty b { font-size: 15.5px; letter-spacing: .01em; color: var(--dp-text, #18202a); }
.gm-empty p {
  max-width: 400px; font-size: 12.5px; line-height: 1.85; margin: 0;
  color: var(--dp-text2, var(--dp-text3, #8a8f98));
}

.gm-head {
  display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap;
  padding-bottom: 10px; border-bottom: 1px solid var(--dp-line, rgba(0,0,0,.08));
}
/* min-width 由 180px 改 0：标题栏窄一点时右侧「放大 / 返回列表」会被 flex-wrap 挤到第二行，
   看起来像没有返回按钮；让文字先收缩，操作按钮始终留在第一行。 */
.gm-head-tx { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.gm-head-tx b { font-size: 16px; color: var(--dp-text, #18202a); }
.gm-head-tx i { font-style: normal; font-size: 12px; color: var(--dp-text2, #8a8f98); }
.gm-head-ops { display: flex; align-items: center; gap: 8px; flex: none; }
.gm-op {
  padding: 6px 14px; border-radius: 999px; font-size: 12.5px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.gm-op:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.gm-op.ghost { background: transparent; }
.gm-locktip {
  font-size: 11.5px; color: var(--dp-text3, #8a8f98); background: rgba(199,169,107,.14);
  padding: 5px 12px; border-radius: 999px;
}

/* ===== 第一步：选模式 ===== */
.gm-setup { display: flex; flex-direction: column; gap: 12px; max-width: 620px; }
.gm-setup-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.gm-setup-title { font-size: 13px; font-weight: 600; color: var(--dp-text2, #45505b); }

/* ===== 游戏说明（内联展开，不用弹窗） ===== */
.gm-rulesbtn {
  display: inline-flex; align-items: center; gap: 6px; flex: none;
  padding: 5px 12px; border-radius: 999px; cursor: pointer; font-family: inherit;
  font-size: 12px; font-weight: 600;
  border: 1px solid var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199,169,107,.14));
  color: var(--yq-gold-deep, var(--yq-gold-bright, var(--yq-gold, #c7a96b)));
  transition: all .18s;
}
.gm-rulesbtn:hover { background: rgba(199,169,107,.24); transform: translateY(-1px); }
.gm-rulesbtn-ic {
  width: 15px; height: 15px; flex: none; display: grid; place-items: center;
  border-radius: 50%; font-size: 11px; line-height: 1;
  background: var(--yq-gold, #c7a96b); color: #fff;
}
/* 说明面板：玻璃底 + 鎏金细边，昼夜都成立 */
.gm-rules {
  display: flex; flex-direction: column; gap: 7px; padding: 13px 15px; border-radius: 14px;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.12)));
  background: var(--color-bg-glass, rgba(127,127,127,.06));
  backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  box-shadow: var(--glass-highlight, none);
}
.gm-rules--play { width: 100%; max-width: 760px; margin-bottom: 4px; }
.gm-rule {
  display: flex; align-items: flex-start; gap: 8px;
  font-size: 12.5px; line-height: 1.75; color: var(--dp-text2, #45505b);
}
.gm-rule-dot {
  width: 5px; height: 5px; flex: none; margin-top: 8px; border-radius: 50%;
  background: var(--yq-gold, #c7a96b);
}

.gm-modecards { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
/* 模式卡片：原先是硬编码的白色渐变，夜间压在深色岛屿上就是一排灰砖；
   改用全站玻璃 token，昼夜各自成立。 */
.gm-modecard {
  display: flex; flex-direction: column; gap: 4px; text-align: left; cursor: pointer;
  padding: 14px 16px; border-radius: 15px; font-family: inherit;
  border: 1px solid var(--glass-border, var(--dp-line, rgba(0,0,0,.12)));
  background: var(--color-bg-glass, rgba(127,127,127,.06));
  backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  box-shadow: var(--glass-highlight, none);
  transition: all .18s;
}
.gm-modecard:hover {
  border-color: var(--yq-gold, #c7a96b);
  background: var(--yq-gold-faint, rgba(199,169,107,.14));
  transform: translateY(-1px);
  box-shadow: 0 10px 24px var(--yq-gold-glow, rgba(199,169,107,.16));
}
.gm-modecard b { font-size: 14px; color: var(--dp-text, #18202a); }
.gm-modecard i { font-style: normal; font-size: 11.5px; line-height: 1.6; color: var(--dp-text2, #8a8f98); }
.gm-size { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gm-size-label { font-size: 12.5px; color: var(--dp-text2, #45505b); font-weight: 600; }
.gm-sizebtn {
  padding: 6px 14px; border-radius: 999px; cursor: pointer; font-family: inherit; font-size: 12.5px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: transparent; color: var(--dp-text2, #45505b);
  transition: all .18s;
}
.gm-sizebtn.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gm-size-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.gm-resume {
  align-self: flex-start; display: flex; align-items: center; gap: 8px;
  padding: 9px 16px; border-radius: 999px; cursor: pointer; font-family: inherit; font-size: 12.5px;
  border: 1px dashed var(--yq-gold, #c7a96b); background: rgba(199,169,107,.08);
  color: var(--yq-gold, #c7a96b); font-weight: 600;
}
.gm-resume em { font-style: normal; font-weight: 400; opacity: .75; }

/* ===== 第二步：对局 ===== */
.gm-play { display: flex; flex-direction: column; align-items: center; width: 100%; }
.gm-root.is-big .gm-play { max-width: 1000px; margin: 0 auto; }

@media (max-width: 860px) {
  .gm-root { grid-template-columns: 1fr; gap: 12px; }
  .gm-rail {
    flex-direction: row; gap: 10px; overflow-x: auto; padding-bottom: 4px;
  }
  .gm-grp { flex-direction: row; align-items: center; gap: 6px; }
  .gm-grp-name { display: none; }
  .gm-item { width: auto; padding: 7px 12px; }
  .gm-item-tx i { display: none; }
  .gm-empty { min-height: 220px; }
}
</style>
