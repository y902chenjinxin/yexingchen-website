<template>
  <div class="rr-wrap">
    <div class="rr-bar">
      <span class="rr-tag">{{ modeLabel }}</span>
      <span v-if="!netOn" class="rr-tag">{{ track.label }}</span>
      <span class="rr-tag">{{ bike.label }}</span>
      <span class="rr-score"><b>{{ st.score }}</b> 分</span>
      <button class="rr-btn tiny" type="button" @click="toggleMute">{{ muted ? '音效关' : '音效开' }}</button>
      <span v-if="!netOn" class="rr-best">本赛道最高 {{ best }}</span>
      <button v-if="phase === 'idle' && !netOn" class="rr-btn primary" @click="start">开始比赛</button>
      <template v-else-if="netOn && phase !== 'idle'">
        <button v-if="phase === 'run'" class="rr-btn" @click="quitRace">退出比赛</button>
        <button v-else class="rr-btn" @click="backToRoom">回到房间</button>
      </template>
      <template v-else-if="!netOn">
        <button class="rr-btn" @click="restart">重开</button>
        <button class="rr-btn" @click="openSetup">换车 / 换赛道</button>
      </template>
    </div>

    <div class="rr-cvt">
      <canvas ref="cvEl" width="1200" height="700" class="rr-cv"></canvas>

      <!-- 赛前设置：赛道 / 车辆（+ 无外源难度时补一个难度选择）。
           原版 Road Rash 就是「选赛道 + 选车」开局，这里把它放回游戏里，
           从游戏大厅和侧栏直达页进来都能选，不必依赖外层的模式选择器。 -->
      <div v-if="phase === 'idle'" class="rr-veil">
        <b>赛前设置</b>

        <div class="rr-vsec">赛道</div>
        <div class="rr-vgrid">
          <button
            v-for="k in TRACK_LIST" :key="k" type="button"
            class="rr-card" :class="{ on: k === trackKey }"
            :disabled="!!room"
            @click="pickTrack(k)"
          >
            <span class="rr-card-t">{{ TRACKS[k].label }}</span>
            <span class="rr-card-s">{{ TRACKS[k].tag }}</span>
          </button>
        </div>

        <div class="rr-vsec">车辆</div>
        <div class="rr-vgrid">
          <button
            v-for="k in BIKE_LIST" :key="k" type="button"
            class="rr-card" :class="{ on: k === bikeKey }"
            @click="pickBike(k)"
          >
            <span class="rr-card-t">{{ BIKES[k].label }}</span>
            <span class="rr-card-s">{{ BIKES[k].tag }} · 伤害 {{ BIKES[k].damage }}</span>
            <span class="rr-stats">
              <span v-for="s in STAT_KEYS" :key="s.key" class="rr-stat">
                <em>{{ s.label }}</em>
                <i v-for="n in 5" :key="n" :class="{ on: n <= statPips(k, s.key) }"></i>
              </span>
            </span>
          </button>
        </div>

        <template v-if="!props.initialMode">
          <div class="rr-vsec">难度预设</div>
          <div class="rr-vgrid">
            <button
              v-for="(m, k) in MODES" :key="k" type="button"
              class="rr-card" :class="{ on: k === mode }"
              @click="pickMode(k)"
            >
              <span class="rr-card-t">{{ m.label }}</span>
              <span class="rr-card-s">{{ meters(m.length) }} 米 · {{ m.rivals }} 名对手 · {{ m.police }} 辆警车</span>
            </button>
          </div>
        </template>

        <div class="rr-vsec">对手人数 / 比赛里程</div>
        <div class="rr-nums">
          <label class="rr-num">
            <span>对手</span>
            <input
              type="number" inputmode="numeric" min="1" :max="RIVALS_MAX" step="1"
              :value="rivals" :disabled="!!room" @change="onRivalsInput"
            />
            <span>人</span>
          </label>
          <label class="rr-num">
            <span>里程</span>
            <input
              type="number" inputmode="numeric" min="1" :max="KM_MAX" step="1"
              :value="km" :disabled="!!room" @change="onKmInput"
            />
            <span>km</span>
          </label>
        </div>
        <div class="rr-chips">
          <button
            v-for="n in RIVALS_QUICK" :key="'rv' + n" type="button"
            class="rr-chip" :class="{ on: rivals === n }"
            :disabled="!!room"
            @click="pickRivals(n)"
          >{{ n }} 人</button>
        </div>
        <div class="rr-chips">
          <button
            v-for="n in KM_LIST" :key="'km' + n" type="button"
            class="rr-chip" :class="{ on: km === n }"
            :disabled="!!room"
            @click="pickKm(n)"
          >{{ n }} km</button>
        </div>

        <div class="rr-vsec">玩法</div>
        <div class="rr-chips">
          <button type="button" class="rr-chip" :class="{ on: playMode === 'solo' }" :disabled="!!room" @click="setPlayMode('solo')">单机</button>
          <button type="button" class="rr-chip" :class="{ on: playMode === 'online' }" :disabled="!!room" @click="setPlayMode('online')">在线一起玩</button>
        </div>

        <div v-if="playMode === 'online'" class="rr-net">
          <template v-if="!room">
            <div class="rr-netrow">
              <button class="rr-btn primary" type="button" :disabled="roomBusy" @click="createRoom">创建房间</button>
              <input
                v-model="joinCode" class="rr-code" maxlength="5" inputmode="numeric"
                placeholder="输入房号" @keydown.enter.prevent="joinRoom"
              />
              <button class="rr-btn" type="button" :disabled="roomBusy || joinCode.trim().length < 4" @click="joinRoom">加入</button>
            </div>
            <p class="rr-neterr" v-if="roomErr">{{ roomErr }}</p>
          </template>
          <template v-else>
            <div class="rr-netrow">
              <span class="rr-roomcode">房号 <b>{{ room.code }}</b></span>
              <button class="rr-btn" type="button" @click="leaveRoom">离开房间</button>
            </div>
            <div class="rr-players">
              <span v-for="p in room.players" :key="p.uid" class="rr-player">
                <i :style="{ background: p.color }"></i>{{ p.name }}<em v-if="p.uid === room.my_uid">（我）</em>
              </span>
            </div>
            <div class="rr-netrow">
              <button v-if="room.is_host" class="rr-btn primary" type="button" :disabled="roomBusy" @click="startOnline">
                开始比赛（{{ room.players.length }} 人）
              </button>
              <span v-else class="rr-nettip">等房主开始 · {{ TRACKS[room.track]?.label || room.track }} · {{ room.km }} km</span>
            </div>
          </template>
          <p class="rr-nettip">把房号报给家人即可加入 · 同一房间每人颜色不同 · 最多 19 人</p>
        </div>

        <p class="rr-tip">W 加速 · S 刹车 · 按住 A / D 或 ← / → 压弯（松手自动回正）· 空格向前挥拳 · Shift 向后挥拳 · 打倒对手会掉落武器，开过去捡</p>
        <button v-if="playMode === 'solo'" class="rr-btn primary" type="button" @click="start">开始比赛</button>
      </div>
    </div>

    <div v-if="isTouch" class="rr-pad">
      <button class="rr-pk" @pointerdown.prevent="hold('left', true)" @pointerup="hold('left', false)" @pointercancel="hold('left', false)" @pointerleave="hold('left', false)">◀ 左倾</button>
      <button class="rr-pk" @pointerdown.prevent="hold('right', true)" @pointerup="hold('right', false)" @pointercancel="hold('right', false)" @pointerleave="hold('right', false)">右倾 ▶</button>
      <button class="rr-pk" @pointerdown.prevent="hold('accel', true)" @pointerup="hold('accel', false)" @pointercancel="hold('accel', false)" @pointerleave="hold('accel', false)">加速</button>
      <button class="rr-pk" @pointerdown.prevent="hold('brake', true)" @pointerup="hold('brake', false)" @pointercancel="hold('brake', false)" @pointerleave="hold('brake', false)">刹车</button>
      <button class="rr-pk wide" @pointerdown.prevent="tap('atkF')">前击</button>
      <button class="rr-pk wide" @pointerdown.prevent="tap('atkB')">后击</button>
    </div>
    <p v-else class="rr-hint">电脑端键盘直接可用（无需先点画面）· 按住 ← / → 压弯，松手自动回正</p>
  </div>
</template>

<script setup>
/** 暴力摩托（Road Rash）· 伪 3D 公路竞速 + 近身格斗
 *
 * 移植来源：github.com/hh996655/RoadRashPygame（Pygame 复刻版 road_rash_final.py，纯几何绘制、无外部素材）。
 * 移植约定：
 *   - 数值基线与原版一一对应（4 车道、加速/刹车/自然回速、换道冷却、攻击冷却 /
 *     命中判定 150 像素 & 相邻 2 车道、命中 +200（警车 +500）、超车 +50、
 *     障碍撞到 -15 耐久、车车相撞双方各 -5 耐久、耐久归零翻车、跑满距离通关）。
 *   - v2.46.153：视角与操控重做 —— 改成车尾后视的真摩托：
 *     按住 ←/→ 车身持续倾倒压弯、松手弹簧回正（带轻微摇晃），路面按曲率生成
 *     真实弯道并给车一个向弯外的离心力，相机跟随玩家横向位置、随速度抖动。
 *     原来的「按一下换一条车道」已废弃（那是俯视换道，看着像贴图平移）。
 *   - v2.46.146：补回原作的「选赛道 + 选车」开局环节 —— 4 张赛道（平原 / 沙地 / 丘谷 / 夜道，
 *     纯景观差异：天空、远山、地面、路肩、路旁景物、天象各不同）+ 4 台车（极速 / 加速 / 灵活 /
 *     耐久 / 伤害 五项差异），选择结果落 localStorage，下次进来沿用；最高分按赛道分别记。
 *   - 画面为自绘（不论哪张赛道都沿用玄黄金点缀），不使用任何 emoji / 外链图片。
 */
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { roadrashApi, beaconRoadrashLeave } from '@/api/roadrash'
import { rrSfx, setMuted, isMuted } from '@/utils/games/roadrash-sfx'

const props = defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
})

/* ---------- 常量（基线同原版） ---------- */
const W = 1200
const H = 700
const FPS = 60
const LANES = 4
const BASE_SPEED = 8
const BRAKE = 0.5
const HORIZON = 292
/** 玩家固定画在路面最下沿：此处透视系数恰为 1，车道中心与车道虚线天然对齐 */
const PLAYER_Y = H
const PLAYER_DRAW_Y = H - 4
const ROAD_X0 = 108
const ROAD_X1 = 1092
const ROAD_W = ROAD_X1 - ROAD_X0      // 路面在下沿的像素宽（横向 0~1 映射到这段）
const CX = W / 2
/** objY 是线性压缩：rel 超过这个值就压到地平线以上，看不到 */
const VIEW_REL = (H - HORIZON) / 0.32

/** 路面起伏：地平线随里程上下浮动，过山头时远景整体抬升、下坡时下沉。
 *  原版公路不是一条水平直线，靠这个才有「翻山越岭」的节奏。 */
function hillAt(pos) {
  return Math.sin(pos * 0.00042) * 13 + Math.sin(pos * 0.00017 + 2.1) * 8
}
/** 当前帧的地平线（游戏坐标），draw 每帧刷新 */
let hzNow = HORIZON

/** 弯道曲率（-1~1）：两级正弦叠加，随里程连续推移。
 *  短波 ≈ 2.5 km、长波 ≈ 7.5 km，50 / 100 km 长图里既能一直有弯，也不会变成连发 S 弯。 */
function curveAt(pos) {
  const s = pos * 0.0005
  return Math.sin(s) * 0.55 + Math.sin(s * 0.33 + 1.1) * 0.3 + Math.sin(s * 2.3 + 0.4) * 0.07
}
/** 前方 rel 像素处的横向弯曲量（单位：路宽）。近处 0、远处按平方增长 —— 透视里的弯道。 */
function bendAt(rel) {
  if (rel <= 0) return 0
  const t = Math.min(1, rel / 1500)
  return curveAt((player ? player.roadPos : 0) + rel) * t * t * 0.9
}
/** 世界坐标 → 屏幕：相机跟着玩家的横向位置走（玩家永远在画面中央），再叠加弯道偏移。
 *  x 取 0~1（0 = 左路肩，1 = 右路肩） */
function wpX(x, y, rel) {
  const k = sc(y)
  return CX + ((x - camX) + bendAt(rel)) * ROAD_W * k
}

/** 难度档：只改「路程 / 对手数 / 警车数」这几项，玩法本身不变
 *  路程用「像素」为单位（原版 6000），显示时按 METERS 换算成米；
 *  原版 6000 像素在全速下只需 4 秒就跑完，太短，故整体拉长到 20~100 秒一局。 */
const MODES = {
  easy: { label: '休闲 · 短途', length: 30000, rivals: 3, police: 1 },
  classic: { label: '经典 · 单程', length: 60000, rivals: 5, police: 2 },
  hard: { label: '硬核 · 长途', length: 90000, rivals: 6, police: 3 },
}
/** 像素 → 米（里程与通关距离的显示换算） */
const METERS = 5
function meters(px) { return Math.round(px / METERS) }

/* ---------- 赛道（像素风场景；海岸对齐原版 Road Rash 的悬崖 + 海面公路） ---------- */
/** peaks = 远山/城市轮廓控制点（[x, 相对地平线的负高]），两层：远层压扁 0.58 倍。
 *  scene 决定中景：coast = 左侧土崖 + 右侧海面；desert = 沙丘；valley = 山林；city = 楼群。 */
const TRACKS = {
  plain: {
    label: '海岸', tag: '海岸公路 · 白昼', scene: 'coast',
    sky: ['#8fb8e0', '#b9d4ea', '#e2edf2'], cloud: '#f6fafc', cloudShade: '#c4d8e6',
    cliff: ['#b08a5e', '#96724a', '#c9a878'],
    sea: ['#2f6aa8', '#4a88c0', '#7fb2d8'], foam: '#eaf6fc',
    peaks: [[0, -40], [200, -96], [420, -52], [640, -110], [900, -60], [1100, -88], [1200, -44]],
    farPeaks: '#8a9c96', nearPeaks: '#5c7360',
    ground: '#5c7a4a', groundShade: '#3f5a36',
    road: '#4c4e54', roadDark: '#35373d', roadLight: '#5e6068', tyre: '#2a2c32',
    shoulder: '#a8723c', shoulderDark: '#8a5a2c',
    dash: '#e2c22f', edge: '#d9d3bd', prop: 'palm', rail: false,
  },
  desert: {
    label: '沙漠', tag: '沙漠公路 · 黄昏', scene: 'desert',
    sky: ['#5a3a6a', '#b06a5a', '#e8b070'], cloud: '#f0c090', cloudShade: '#c08060',
    peaks: [[0, -30], [240, -54], [520, -34], [760, -62], [1000, -38], [1200, -50]],
    farPeaks: '#9a6a62', nearPeaks: '#7a4e4a',
    ground: '#c0925e', groundShade: '#9a6c3c',
    road: '#5c564f', roadDark: '#3f3b35', roadLight: '#736b60', tyre: '#332f2a',
    shoulder: '#c8a070', shoulderDark: '#a07c50',
    dash: '#f0d060', edge: '#e8dcc0',
    prop: 'cactus', rail: false,
    orb: { x: 0.5, y: 0.42, r: 40, color: '#ffe0a0', glow: 'rgba(255,190,120,.35)' },
  },
  valley: {
    label: '山林', tag: '山林公路 · 多云', scene: 'valley',
    sky: ['#7c94a8', '#a8bcc8', '#d6e0e4'], cloud: '#eef2f4', cloudShade: '#b8c8d0',
    peaks: [[0, -70], [180, -170], [380, -96], [560, -190], [760, -120], [960, -176], [1200, -92]],
    farPeaks: '#6c8090', nearPeaks: '#465a4e',
    ground: '#4a6a3a', groundShade: '#334c2a',
    road: '#484a50', roadDark: '#32343a', roadLight: '#5a5c62', tyre: '#272930',
    shoulder: '#8a7a58', shoulderDark: '#6a5c40',
    dash: '#e8d868', edge: '#d8d8c8', prop: 'pine', rail: true,
  },
  night: {
    label: '夜城', tag: '城市夜路 · 深夜', scene: 'city',
    sky: ['#070d1c', '#132441', '#2a3b60'], cloud: '#2c3e5c', cloudShade: '#1a2840',
    peaks: [[0, -90], [140, -150], [260, -110], [400, -190], [520, -130], [660, -170], [800, -120], [940, -185], [1080, -140], [1200, -100]],
    farPeaks: '#16233c', nearPeaks: '#0e1729',
    ground: '#1b2432', groundShade: '#0c1220',
    road: '#25282e', roadDark: '#161920', roadLight: '#32353d', tyre: '#0e1116',
    shoulder: '#3a3a40', shoulderDark: '#2a2a30',
    dash: '#e8e0a0', edge: '#a8b0c0',
    prop: 'lamp', stars: true, rail: false,
  },
}
const TRACK_LIST = ['plain', 'desert', 'valley', 'night']

/* ---------- 车辆（差异真的落到手感上：极速 / 加速 / 换道冷却 / 耐久 / 攻击伤害） ---------- */
const BIKES = {
  light: { label: '轻骑 250', tag: '起步快 · 皮薄', color: '#7fc4a6', maxSpeed: 30, accel: 0.72, laneCd: 10, durability: 80, damage: 7, shape: 'street' },
  street: { label: '街霸 600', tag: '均衡好上手', color: '#e2604a', maxSpeed: 25, accel: 0.5, laneCd: 15, durability: 100, damage: 10, shape: 'street' },
  heavy: { label: '重机 750', tag: '抗撞 · 迟钝', color: '#4d7fd8', maxSpeed: 21, accel: 0.34, laneCd: 20, durability: 135, damage: 13, shape: 'cruiser' },
  custom: { label: '战斧 1000', tag: '极速 · 重击', color: '#d6b45a', maxSpeed: 28, accel: 0.6, laneCd: 12, durability: 105, damage: 16, shape: 'touring' },
}
const BIKE_LIST = ['light', 'street', 'heavy', 'custom']
/** 车辆面板的四条属性：把数值归一到 1~5 格（分母取各自的上限，写死便于一眼比较） */
const STAT_KEYS = [
  { key: 'speed', label: '极速' },
  { key: 'accel', label: '加速' },
  { key: 'handling', label: '灵活' },
  { key: 'durability', label: '耐久' },
]
function statPips(k, key) {
  const b = BIKES[k]
  const r = key === 'speed' ? b.maxSpeed / 30
    : key === 'accel' ? b.accel / 0.72
      : key === 'handling' ? (30 - b.laneCd) / 20
        : b.durability / 135
  return Math.max(1, Math.min(5, Math.round(r * 5)))
}

/** 对手配色：20 支高区分度色相，最多 19 名对手也能各不相同（与后端 PALETTE 对齐）。
 *  警车不再用普通蓝色，改深青灰 + 红蓝爆闪，避免和 2 号蓝对手撞色。 */
const RIVAL_COLORS = [
  '#e05a4a', '#4f9bd8', '#6fbf73', '#d9b23c', '#a97ade',
  '#3fc4c4', '#e08fb5', '#c98b3f', '#8fbf4f', '#5f7fe0',
  '#d46a9c', '#57c4a3', '#e6a23c', '#9a8fe0', '#c85a5a',
  '#4fb0a0', '#d8a0d0', '#8aa8e8', '#b0b04f', '#e08a5a',
]
const POLICE_COLOR = '#3c4a63'
const RIVALS_MAX = 19      // 「20 人之下」：1~19 名对手
const KM_MAX = 200         // 里程上限 200 km（50 / 100 这类长图随便输）
/** 里程快选（km）：覆盖短局 / 标准 / 长途；其它值直接在上面的数字框里输 */
const KM_LIST = [3, 6, 12, 30, 50, 100]
/** 对手人数快选：面板上只放常用档，避免 19 个胶囊铺三行 */
const RIVALS_QUICK = [3, 5, 8, 12, 16, 19]

const cvEl = ref(null)
const phase = ref('idle')          // idle | run | win | lose
const st = reactive({ score: 0, durability: 100, speed: 0, dist: 0, lean: 0, onGrass: false })
const cfg = reactive({ ...MODES.classic })

const best = ref(0)
const isTouch = (typeof window !== 'undefined')
  && (window.matchMedia?.('(hover: none)')?.matches || 'ontouchstart' in window)

const isMobile = computed(() => (typeof window !== 'undefined')
  && (window.innerWidth < 900 || 'ontouchstart' in window))

/** 选择项：赛道 / 车辆 / 难度。赛道与车辆沿用上次（localStorage），难度优先取外层传入 */
const trackKey = ref(localStorage.getItem('roadrash_track') || 'plain')
const bikeKey = ref(localStorage.getItem('roadrash_bike') || 'street')
const mode = ref(props.initialMode || (isMobile.value ? 'easy' : 'classic'))
const modeCfg = MODES[mode.value] || MODES.classic

/** 可配置项：对手人数 1~19、里程 1~200 km。沿用上次选择（localStorage） */
const rivals = ref(clampInt(localStorage.getItem('roadrash_rivals'), 1, RIVALS_MAX, modeCfg.rivals))
const km = ref(pickKmValue(localStorage.getItem('roadrash_km'), Math.round(meters(modeCfg.length) / 1000)))

const track = computed(() => TRACKS[trackKey.value] || TRACKS.plain)
const bike = computed(() => BIKES[bikeKey.value] || BIKES.street)

/* ---------- 在线房间 ---------- */
const playMode = ref('solo')       // solo | online
const room = ref(null)             // 服务端房间快照；存在即「已在房间里」
const muted = ref(isMuted())
function toggleMute() {
  muted.value = !muted.value
  setMuted(muted.value)
}
const joinCode = ref('')
const roomErr = ref('')
const roomBusy = ref(false)
const netOn = computed(() => !!room.value)
const ghosts = []                  // 其他玩家的 ghost 车（普通对象，不进响应式）
let roomTimer = 0
let pollBusy = false
let raceStarted = false            // 本地是否已经起跑（避免每次轮询重复 reset）
let awaitingReset = false          // 已完赛、等房主重开；期间忽略 playing 快照
let onlineStartLocal = 0           // 开局倒计时终点（本地时钟 ms）

const modeLabel = computed(() => {
  if (netOn.value) return `在线 · 房间 ${room.value.code}`
  const m = MODES[mode.value] || MODES.classic
  const same = rivals.value === m.rivals && km.value === Math.round(meters(m.length) / 1000)
  return same ? m.label : `自定义 · ${rivals.value} 对手 · ${km.value} km`
})

const keys = { left: false, right: false, accel: false, brake: false, atkF: false, atkB: false }

/* 实体用普通对象（不进响应式，避免每帧深比较）；HUD 需要的量走 st */
let player = null
let folks = []        // 对手 + 警车
let obstacles = []
/** 被击落在地的武器：开过去就能捡（原版「打倒对手、抢他的棍子」） */
let drops = []
/** 武器伤害倍率：空手最轻，链子最重 */
const WEAPON_MULT = { fist: 1, stick: 1.35, whip: 1.25, chain: 1.6, baton: 1.4 }
const WEAPON_LABEL = { fist: '空手', stick: '木棍', whip: '皮鞭', chain: '铁链', baton: '警棍' }
let lastSpawn = 0
let flipClock = 0
/** 撞击反馈：震屏强度、红色闪屏、火花粒子 */
const impact = { shake: 0, flash: 0 }
let sparks = []
let hitStop = 0               // 撞击顿帧：几帧内世界几乎不动，冲击才有重量
let camX = 0.5                // 相机横向位置（滞后于玩家 → 车身会在画面里被「甩」一下）
const CRASH_FRAMES = 62        // 摔车时长（约 1 秒）：飞起 → 落地 → 扶正

function bump(strength, flash) {
  impact.shake = Math.max(impact.shake, strength)
  impact.flash = Math.max(impact.flash, flash)
}
function addSparks(n, color) {
  for (let i = 0; i < n; i++) {
    sparks.push({
      x: CX + (Math.random() - 0.5) * 110,
      y: H - 40 - Math.random() * 70,
      vx: (Math.random() - 0.5) * 11,
      vy: -Math.random() * 8 - 1,
      life: 20 + Math.random() * 20,
      color: color || '#ffd27a',
    })
  }
}
/** 每帧推进撞击反馈：震屏 / 闪屏衰减 + 火花粒子 */
function stepFx() {
  impact.shake *= 0.90
  impact.flash *= 0.92
  for (let i = sparks.length - 1; i >= 0; i--) {
    const s = sparks[i]
    s.x += s.vx
    s.y += s.vy
    s.vy += 0.34
    s.life--
    if (s.life <= 0) sparks.splice(i, 1)
  }
}
/** 打倒一名骑手：翻车 + 掉武器（开过去能捡） */
function knockDown(b) {
  if (!b || !b.alive) return
  b.alive = false
  b.flip = 0
  b.atkType = null
  b.pendingHit = null
  if (b.weapon && b.weapon !== 'fist') {
    drops.push({ x: b.x, roadPos: b.roadPos, weapon: b.weapon })
    b.weapon = 'fist'
  }
  rrSfx.impact(0.7)
}

/** 摔车：速度砸下来、车身被甩向一侧并飞起来转一圈，落地后短暂无敌再扶正 */
function crashPlayer(dir) {
  const p = player
  if (!p || p.crash > 0) return
  p.crash = CRASH_FRAMES
  p.crashDir = dir || (Math.random() < 0.5 ? -1 : 1)
  p.speed = Math.min(p.speed, 3)
  p.leanV = 0
  hitStop = 5
  bump(9, 0.5)
  addSparks(30, '#ffd27a')
  rrSfx.crash()
  // 摔车掉武器（原版设定）：要回头去捡回来
  if (p.weapon && p.weapon !== 'fist') {
    drops.push({ x: p.x, roadPos: p.roadPos - 260, weapon: p.weapon })
    p.weapon = 'fist'
  }
}

function clampInt(v, min, max, dft) {
  const n = Math.round(Number(v))
  return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : dft
}
function pickKmValue(v, dft) {
  const n = Math.round(Number(v))
  return Number.isFinite(n) ? Math.max(1, Math.min(KM_MAX, n)) : dft
}

/** 透视：越靠近屏幕下方越大（0.22 → 1）。远端收窄到约 1/5 屏宽，贴近原版公路的透视。 */
function sc(y) {
  const t = Math.max(0, Math.min(1, (y - hzNow) / (H - hzNow)))
  return 0.22 + 0.78 * t
}
/** 前方（roadPos 更大）画在屏幕上方 */
function objY(rel) { return PLAYER_Y - rel * 0.32 }

function makeBike(lane, roadPos, color, opt = {}) {
  const maxSpeed = opt.maxSpeed ?? 25
  const durability = opt.durability ?? 100
  return {
    lane, roadPos, color,
    /** 连续横向位置 0~1：车道只是 AI 的目标，真正画到屏幕与判定用的是 x */
    x: (lane + 0.5) / LANES,
    /** 车身倾角 -1~1（正 = 向右压弯），绘制时旋转，玩家输入驱动 */
    lean: 0,
    leanV: 0,
    isPlayer: !!opt.isPlayer,
    isPolice: !!opt.isPolice,
    speed: opt.isPlayer ? 10 : 5,
    maxSpeed,
    durability,
    maxDurability: durability,
    laneCdMax: opt.laneCdMax ?? 15,
    accel: opt.accel ?? 0.5,
    damage: opt.damage ?? 10,
    shape: opt.shape || (opt.isPolice ? 'police' : 'street'),
    alive: true,
    flip: 0,
    crash: 0,
    crashDir: 1,
    laneCd: 0,
    atkCd: 0,
    atkType: null,
    atkTimer: 0,
    atkAge: 0,
    hitT: 0,
    hitDir: 1,
    contactCd: 0,
    weapon: opt.isPolice ? 'baton' : 'fist',
    passed: false,
  }
}

function reset() {
  rrSfx.stopEngine()
  Object.assign(cfg, MODES[mode.value] || MODES.classic)
  // v2.46.150：人数与里程以面板上的可配置项为准（难度只决定警车数）
  cfg.rivals = rivals.value
  cfg.length = km.value * 5000   // METERS=5 → 1 km = 5000 像素
  const bk = bike.value

  player = makeBike(LANES >> 1, 0, bk.color, {
    isPlayer: true,
    maxSpeed: bk.maxSpeed,
    accel: bk.accel,
    laneCdMax: bk.laneCd,
    durability: bk.durability,
    damage: bk.damage,
    shape: bk.shape,
  })
  player.x = 0.5          // 起步站正中间：相机以玩家为中心，路面往两边推开
  folks = []
  ghosts.length = 0
  // 对手投放：始终放在玩家前方一段「滚动车流」里，而不是铺满全程前 40%。
  // 长图（50/100 km）如果按比例铺，开局几公里会一辆车都遇不到；这里把投放窗口
  // 封顶 13 km，跑过的对手再被回收接力（见 step 里的 recycleGap），全程一直有车。
  const span = Math.min(cfg.length * 0.4, 13000)
  const spacing = span / Math.max(1, cfg.rivals)
  // 每人一支不同的颜色；先剔除玩家车色与在线玩家的颜色，避免撞色
  const taken = new Set((room.value?.players || []).map((p) => p.color))
  const pool = RIVAL_COLORS.filter((c) => c !== bk.color && !taken.has(c))
  const colors = pool.length ? pool : RIVAL_COLORS
  for (let i = 0; i < cfg.rivals; i++) {
    const f = makeBike(
      1 + Math.floor(Math.random() * (LANES - 1)),
      800 + spacing * i + Math.random() * Math.min(400, spacing * 0.6 || 400),
      colors[i % colors.length],
    )
    // 被甩开多远之后重新投放到前方（每人不同，避免整队同一帧集体瞬移）
    f.recycleGap = 12000 + Math.random() * 12000
    // 部分对手自带家伙（打倒了才能抢过来）
    if (Math.random() < 0.45) f.weapon = ['stick', 'whip', 'chain'][Math.floor(Math.random() * 3)]
    folks.push(f)
  }
  for (let i = 0; i < cfg.police; i++) {
    folks.push(makeBike(
      1 + Math.floor(Math.random() * (LANES - 1)),
      3000 + Math.random() * 5000,
      POLICE_COLOR,
      { isPolice: true },
    ))
  }
  obstacles = []
  drops = []
  lastSpawn = 0
  flipClock = 0
  sparks = []
  impact.shake = 0
  impact.flash = 0
  hitStop = 0
  camX = 0.5
  st.score = 0
  st.durability = bk.durability
  st.speed = 0
  st.dist = 0
  st.lean = 0
  st.onGrass = false
  for (const k in keys) keys[k] = false
  loadBest()
}

/** 最高分按赛道分别记（换赛道就是换一条新纪录，不会被另一张图的成绩压着） */
function loadBest() {
  best.value = Number(localStorage.getItem(`roadrash_best_${trackKey.value}`) || 0) || 0
}

function pickTrack(k) {
  if (trackKey.value === k) return
  trackKey.value = k
  localStorage.setItem('roadrash_track', k)
  reset()
}
function pickBike(k) {
  if (bikeKey.value === k) return
  bikeKey.value = k
  localStorage.setItem('roadrash_bike', k)
  reset()
}
function pickMode(k) {
  mode.value = k
  // 难度预设同时把「对手人数 / 里程」拉到该档默认值，之后仍可单独微调
  const m = MODES[k] || MODES.classic
  rivals.value = m.rivals
  km.value = Math.round(meters(m.length) / 1000)
  localStorage.setItem('roadrash_rivals', String(rivals.value))
  localStorage.setItem('roadrash_km', String(km.value))
  reset()
}
function pickRivals(n) {
  const v = Math.max(1, Math.min(RIVALS_MAX, Math.round(Number(n) || 1)))
  if (rivals.value === v) return
  rivals.value = v
  localStorage.setItem('roadrash_rivals', String(v))
  reset()
}
function pickKm(n) {
  const v = Math.max(1, Math.min(KM_MAX, Math.round(Number(n) || 1)))
  if (km.value === v) return
  km.value = v
  localStorage.setItem('roadrash_km', String(v))
  reset()
}
/** 数字框输入：越界回写（0 / 999 都会被拉回合法区间） */
function onRivalsInput(e) {
  const v = Math.max(1, Math.min(RIVALS_MAX, Math.round(Number(e.target.value) || 1)))
  e.target.value = String(v)
  pickRivals(v)
}
function onKmInput(e) {
  const v = Math.max(1, Math.min(KM_MAX, Math.round(Number(e.target.value) || 1)))
  e.target.value = String(v)
  pickKm(v)
}
function setPlayMode(v) {
  if (playMode.value === v) return
  playMode.value = v
  roomErr.value = ''
  if (v === 'online') reset()
}

function start() {
  reset()
  rrSfx.startEngine()
  phase.value = 'run'
}

function restart() {
  reset()
  rrSfx.startEngine()
  phase.value = 'run'
}

/** 回到赛前设置（保留当前赛道/车辆的画面对照，改完点开始即开新局） */
function openSetup() {
  reset()
  phase.value = 'idle'
}

function finish(win) {
  phase.value = win ? 'win' : 'lose'
  rrSfx.stopEngine()
  if (st.score > best.value) {
    best.value = st.score
    localStorage.setItem(`roadrash_best_${trackKey.value}`, String(best.value))
  }
  if (netOn.value) {
    awaitingReset = true
    reportState()
  }
}

/* ---------- 在线房间（房号 + 轮询；后端见 roadrash_rooms.py） ---------- */
function apiMsg(e, fallback) {
  return e?.msg || e?.response?.data?.msg || fallback
}

/** 房主的赛道 / 里程 / 对手人数是权威设置，进房或开局时同步到本地 */
function applyRoomConfig(snap) {
  if (!snap) return
  if (TRACKS[snap.track]) trackKey.value = snap.track
  const n = Number(snap.km)
  if (Number.isFinite(n)) km.value = Math.max(1, Math.min(KM_MAX, Math.round(n)))
  const r = Number(snap.rivals)
  if (Number.isFinite(r)) rivals.value = Math.max(1, Math.min(RIVALS_MAX, Math.round(r)))
}

function beginOnlineRace(snap) {
  applyRoomConfig(snap)
  reset()
  rrSfx.startEngine()
  raceStarted = true
  awaitingReset = false
  // 服务端 start_at 是 3 秒后的开局时刻；用 server_now 校正本机时钟偏差
  onlineStartLocal = snap.start_at
    ? snap.start_at - (snap.server_now - Date.now())
    : 0
  phase.value = 'run'
  updateGhosts(snap)
  startPolling(450)
}

function applySnapshot(snap) {
  if (!snap) return
  room.value = snap
  if (snap.status === 'waiting') {
    raceStarted = false
    awaitingReset = false
    onlineStartLocal = 0
    ghosts.length = 0
    const before = `${trackKey.value}|${km.value}|${rivals.value}`
    applyRoomConfig(snap)
    const changed = before !== `${trackKey.value}|${km.value}|${rivals.value}`
    if (phase.value !== 'idle') {
      phase.value = 'idle'
      reset()
    } else if (changed) {
      reset()
    }
    return
  }
  if (snap.status === 'playing') {
    if (!raceStarted && !awaitingReset) beginOnlineRace(snap)
    else updateGhosts(snap)
  }
}

/** 其他玩家 → ghost 车：颜色由服务端分配，位置按里程插值，避免 450ms 轮询一跳一跳 */
function updateGhosts(snap) {
  const others = (snap.players || []).filter((p) => p.uid !== snap.my_uid)
  const seen = new Set()
  for (const p of others) {
    seen.add(p.uid)
    let g = ghosts.find((x) => x.uid === p.uid)
    if (!g) {
      g = makeBike(p.lane, p.dist, p.color, { shape: 'street' })
      g.uid = p.uid
      g.roadPos = p.dist
      ghosts.push(g)
    }
    g.tag = p.name
    g.color = p.color
    g.targetDist = p.dist
    g.lane = Math.max(0, Math.min(LANES - 1, p.lane | 0))
    g.targetX = (g.lane + 0.5) / LANES
    g.alive = p.alive !== false
    if (!g.alive) g.flip = 18
  }
  for (let i = ghosts.length - 1; i >= 0; i--) {
    if (!seen.has(ghosts[i].uid)) ghosts.splice(i, 1)
  }
}

function myState() {
  return {
    dist: Math.round(player?.roadPos || 0),
    score: st.score,
    speed: st.speed,
    lane: player?.lane || 0,
    durability: Math.round(st.durability),
    finished: phase.value === 'win',
    alive: phase.value !== 'lose',
  }
}

async function reportState() {
  if (!room.value) return
  try {
    const res = await roadrashApi.sync(room.value.code, myState())
    applySnapshot(res.data)
  } catch { /* 忽略：常规轮询会兜底 */ }
}

function startPolling(ms) {
  stopPolling()
  roomTimer = setInterval(pollRoom, ms)
}
function stopPolling() {
  if (roomTimer) { clearInterval(roomTimer); roomTimer = 0 }
}

async function pollRoom() {
  if (!room.value || pollBusy) return
  pollBusy = true
  try {
    const code = room.value.code
    const res = (phase.value === 'run' && room.value.status === 'playing')
      ? await roadrashApi.sync(code, myState())
      : await roadrashApi.state(code)
    applySnapshot(res.data)
  } catch (e) {
    if (e?.response?.status === 404) {
      stopPolling()
      room.value = null
      raceStarted = false
      awaitingReset = false
      phase.value = 'idle'
      roomErr.value = '房间已解散'
      reset()
    }
  } finally {
    pollBusy = false
  }
}

async function createRoom() {
  roomBusy.value = true
  roomErr.value = ''
  try {
    const res = await roadrashApi.create({
      track: trackKey.value,
      km: km.value,
      rivals: rivals.value,
      police: (MODES[mode.value] || MODES.classic).police,
    })
    applySnapshot(res.data)
    startPolling(800)
  } catch (e) {
    roomErr.value = apiMsg(e, '创建房间失败')
  } finally {
    roomBusy.value = false
  }
}

async function joinRoom() {
  const code = joinCode.value.trim()
  if (!/^\d{4,6}$/.test(code)) { roomErr.value = '房号是 5 位数字'; return }
  roomBusy.value = true
  roomErr.value = ''
  try {
    const res = await roadrashApi.join(code)
    applySnapshot(res.data)
    startPolling(res.data?.status === 'playing' ? 450 : 800)
  } catch (e) {
    roomErr.value = apiMsg(e, '加入失败，检查房号')
  } finally {
    roomBusy.value = false
  }
}

async function startOnline() {
  if (!room.value) return
  roomBusy.value = true
  roomErr.value = ''
  try {
    const res = await roadrashApi.start(room.value.code)
    applySnapshot(res.data)
    startPolling(450)
  } catch (e) {
    roomErr.value = apiMsg(e, '开局失败')
  } finally {
    roomBusy.value = false
  }
}

async function leaveRoom() {
  const code = room.value?.code
  stopPolling()
  room.value = null
  ghosts.length = 0
  raceStarted = false
  awaitingReset = false
  onlineStartLocal = 0
  if (phase.value !== 'idle') phase.value = 'idle'
  reset()
  if (code) {
    try { await roadrashApi.leave(code) } catch { /* 忽略 */ }
  }
}

function quitRace() {
  leaveRoom()
}

/** 一局结束回到房间：房主顺手把房间重置为等待，客机等房主重开 */
async function backToRoom() {
  awaitingReset = true
  phase.value = 'idle'
  reset()
  if (room.value?.is_host) {
    try {
      const res = await roadrashApi.reset(room.value.code)
      applySnapshot(res.data)
    } catch (e) {
      roomErr.value = apiMsg(e, '重开失败')
    }
  }
}

/* ---------- 触控 ---------- */
function hold(k, down) { keys[k] = down }
function tap(k) { keys[k] = true; setTimeout(() => { keys[k] = false }, 120) }

/* ---------- 每帧逻辑（与 pygame 版一一对应，车辆差异通过 player 属性生效） ---------- */
function step() {
  if (phase.value !== 'run') return
  // 在线开局 3 秒倒计时：服务端统一 start_at，倒计时期间冻结物理
  if (netOn.value && onlineStartLocal && Date.now() < onlineStartLocal) return
  const p = player
  if (p.laneCd > 0) p.laneCd--
  if (p.atkCd > 0) p.atkCd--
  if (p.contactCd > 0) p.contactCd--

  // 撞击顿帧：几帧内世界几乎静止，速度骤停的「重量」全靠这段时间
  if (hitStop > 0) {
    hitStop--
    p.speed *= 0.94
    p.roadPos += Math.max(0, p.speed * 0.5)
    camX += (p.x - camX) * 0.14
    st.speed = p.speed
    st.dist = p.roadPos
    rrSfx.setSpeed(p.speed / Math.max(1, p.maxSpeed), false)
    stepFx()
    return
  }

  // 摔车中：操控冻结，车身飞起打转、速度砸下来；落地后短暂无敌再扶正
  if (p.crash > 0) {
    p.crash--
    p.speed *= 0.9
    p.roadPos += Math.max(0, p.speed * 0.6)
    p.lean += (p.crashDir * 1.15 - p.lean) * 0.1
    p.x = Math.max(0, Math.min(1, p.x + p.crashDir * 0.004))
    camX += (p.x - camX) * 0.10
    st.dist = p.roadPos
    st.speed = p.speed
    st.durability = p.durability
    st.lean = p.lean
    stepFx()
    if (p.crash === 0) {
      p.lean = 0
      p.leanV = 0
      p.speed = 6
      p.contactCd = 70
      p.x = Math.max(0.08, Math.min(0.92, p.x))
    }
    if (p.durability <= 0) finish(false)
    else if (p.roadPos >= cfg.length) finish(true)
    return
  }

  // 速度（加速率取自所驾车辆）
  if (keys.accel) p.speed = Math.min(p.speed + p.accel * 1.5, p.maxSpeed)
  else if (keys.brake) p.speed = Math.max(p.speed - BRAKE * 2, 0)
  else if (p.speed > BASE_SPEED) p.speed = Math.max(p.speed - 0.1, BASE_SPEED)
  else if (p.speed < BASE_SPEED) p.speed = Math.min(p.speed + 0.1, BASE_SPEED)

  /* 压弯：按住 ←/→ 时倾角持续加大，松开后靠弹簧回正（会有轻微过冲，就是「摇晃」感）。
   * 横向位移由倾角 × 车速驱动：慢车压弯也更慢，符合真车手感。 */
  const steer = (keys.right ? 1 : 0) - (keys.left ? 1 : 0)
  p.leanV += (steer - p.lean) * 0.16 - p.leanV * 0.13
  p.lean = Math.max(-1, Math.min(1, p.lean + p.leanV))
  const spdRatio = Math.max(0, Math.min(1, p.speed / Math.max(1, p.maxSpeed)))
  p.x += p.lean * 0.020 * (0.4 + 0.6 * spdRatio)

  // 弯道离心力：曲率 × 车速，把车往弯外推；玩家得自己反压才能守住线路
  p.x += curveAt(p.roadPos + 300) * spdRatio * 0.0018

  // 冲出路面：压在草地上，限速 + 剧烈颠簸，且不能一路开到屏幕外
  const onGrass = p.x < 0.02 || p.x > 0.98
  if (onGrass) p.speed = Math.min(p.speed, p.maxSpeed * 0.5)
  p.x = Math.max(-0.05, Math.min(1.05, p.x))
  st.onGrass = onGrass && p.speed > 2
  st.lean = p.lean
  p.lane = Math.max(0, Math.min(LANES - 1, Math.floor(p.x * LANES)))
  // 相机滞后跟随：压弯时车身会先在画面里滑出去，再被相机追回来 —— 这就是「重量」
  camX += (p.x - camX) * 0.14
  rrSfx.setSpeed(spdRatio, !!keys.accel)

  // 攻击：空格向前、Shift 向后（举拳 → 出拳 → 收招，共 22 帧）
  if (keys.atkF && p.atkCd === 0 && !p.atkType) {
    p.atkType = 'forward'; p.atkTimer = 22; p.atkAge = 0; p.atkCd = 34
  }
  if (keys.atkB && p.atkCd === 0 && !p.atkType) {
    p.atkType = 'backward'; p.atkTimer = 22; p.atkAge = 0; p.atkCd = 34
  }

  p.roadPos += p.speed
  st.dist = p.roadPos
  st.speed = p.speed
  st.durability = p.durability

  // 攻击判定：只在拳头伸出的那一帧结算一次（不是整段挥拳都扣血）
  if (p.atkType) {
    p.atkAge++
    if (p.atkTimer > 0) p.atkTimer--
    else { p.atkType = null; p.atkAge = 0 }
    if (p.atkAge === 12) {
      for (const t of folks) {
        if (!t.alive) continue
        const d = t.roadPos - p.roadPos
        const hit = p.atkType === 'forward'
          ? (d > 0 && d < 150)
          : (d < 0 && d > -150)
        if (hit && Math.abs(t.x - p.x) < 0.16) {
          t.durability -= p.damage * (WEAPON_MULT[p.weapon] || 1)
          t.hitT = 14
          t.hitDir = Math.sign(t.x - p.x) || 1
          t.speed *= 0.86
          t.lean += t.hitDir * 0.35
          st.score += t.isPolice ? 500 : 200
          rrSfx.hit(p.weapon === 'chain' || p.weapon === 'stick')
          addSparks(6, '#f2f4f8')
          if (t.durability <= 0) knockDown(t)
        }
      }
    }
  }

  // 对手 / 警车也会动手：贴到一车身内就抡拳头（原版的核心乐趣之一）
  for (const f of folks) {
    if (!f.alive) { f.atkType = null; continue }
    if (f.hitT > 0) f.hitT--
    if (f.atkType) {
      f.atkAge++
      if (f.atkAge >= 22) f.atkType = null
      // 拳头伸出的那一帧结算
      if (f.atkAge === 12 && f.pendingHit) {
        const tgt = f.pendingHit.tgt
        const dmg = f.pendingHit.dmg
        f.pendingHit = null
        if (tgt && tgt.alive) {
          if (tgt === p) {
            p.durability -= dmg
            p.hitT = 12
            p.hitDir = Math.sign(p.x - f.x) || 1
            p.speed = Math.max(5, p.speed * 0.88)
            p.lean += p.hitDir * 0.4
            bump(3.5, 0.16)
            addSparks(5, '#ffd27a')
            rrSfx.hit(f.weapon === 'chain' || f.weapon === 'stick')
          } else {
            tgt.durability -= dmg
            tgt.hitT = 12
            tgt.hitDir = Math.sign(tgt.x - f.x) || 1
            tgt.speed *= 0.88
            if (tgt.durability <= 0) knockDown(tgt)
          }
        }
      }
      continue
    }
    if (f.atkCd > 0) { f.atkCd--; continue }
    if (Math.random() > 0.018) continue
    let tgt = null
    let best = 999
    const cands = [p, ...folks]
    for (const cd of cands) {
      if (!cd || cd === f || !cd.alive) continue
      const d = cd.roadPos - f.roadPos
      if (Math.abs(d) > 160 || Math.abs(cd.x - f.x) > 0.16) continue
      const w2 = Math.abs(d) + Math.abs(cd.x - f.x) * 500
      if (w2 < best) { best = w2; tgt = cd }
    }
    if (!tgt) continue
    f.atkType = tgt.roadPos > f.roadPos ? 'forward' : 'backward'
    f.atkAge = 0
    f.atkCd = 100 + Math.random() * 90
    f.pendingHit = { tgt, dmg: (f.damage || 8) * (WEAPON_MULT[f.weapon] || 1) * 0.8 }
  }

  // 地上掉落的武器：开过去就能捡（打倒对手 → 抢他的棍子）
  for (let i = drops.length - 1; i >= 0; i--) {
    const d = drops[i]
    if (d.roadPos < p.roadPos - 900) { drops.splice(i, 1); continue }
    if (Math.abs(d.roadPos - p.roadPos) < 130 && Math.abs(d.x - p.x) < 0.14) {
      p.weapon = d.weapon
      drops.splice(i, 1)
      st.score += 50
      rrSfx.hit(false)
    }
  }

  // 对手 / 警车行动
  // 前方车流配额：视野带内最多保持 8 辆普通对手，被甩远的才接力回前方；
  // 否则 19 名对手全线回收会让路上挤成一锅粥、超车分也刷得离谱。
  let activeRivals = 0
  for (const f of folks) {
    if (!f.isPolice && f.alive
      && f.roadPos > p.roadPos - 3000 && f.roadPos < p.roadPos + 13000) activeRivals++
  }
  for (const f of folks) {
    if (!f.alive) { f.flip++; continue }
    if (f.laneCd > 0) f.laneCd--

    const target = f.isPolice
      ? BASE_SPEED + 1 + (p.roadPos > f.roadPos + 200 ? 2 : (p.roadPos < f.roadPos - 200 ? -1 : 0))
      : BASE_SPEED + (Math.random() * 3 - 1)
    if (f.speed < target) f.speed = Math.min(f.speed + 0.05, target)
    else if (f.speed > target) f.speed = Math.max(f.speed - 0.05, target)
    f.speed = Math.max(5, Math.min(f.speed, f.maxSpeed - 5))

    // 换道：普通车随机微调，警车贴着玩家所在车道追
    const wantLane = f.isPolice
      ? (p.lane !== f.lane ? p.lane : f.lane)
      : (Math.random() < 0.01 ? f.lane + (Math.random() < 0.5 ? -1 : 1) : f.lane)
    if (wantLane !== f.lane && f.laneCd === 0
      && wantLane >= 0 && wantLane <= LANES - 1) {
      f.lane += wantLane > f.lane ? 1 : -1
      f.laneCd = 30
    }

    f.roadPos += f.speed
    // 横向：普通车按车道靠拢；警车直接咬住玩家的横向位置（才会真的贴上来）
    const wantX = f.isPolice ? p.x : (f.lane + 0.5) / LANES
    f.x += (wantX - f.x) * (f.isPolice ? 0.045 : Math.min(0.2, 0.05 + 0.1 * Math.random()))
    // 转向时车身也倾斜（画出来有压弯姿态，不是贴图平移）
    const drift = wantX - f.x
    f.lean += (Math.max(-1, Math.min(1, drift * 6)) - f.lean) * 0.2

    // 超车加分（只算普通对手，警车不算）
    if (!f.isPolice && p.roadPos > f.roadPos && !f.passed) {
      f.passed = true
      st.score += 50
    }

    // 长图接力：被甩开 12k~24k 像素（约 2.4~4.8 km）的对手在视野外重新投放到前方。
    // 快终点时不回收（避免把对手挪过终点线）；警车不回收（它本来就会追）。
    if (!f.isPolice && activeRivals < 8 && p.roadPos < cfg.length - 4000
      && f.roadPos < p.roadPos - (f.recycleGap || 12000)) {
      f.roadPos = p.roadPos + 1800 + Math.random() * Math.min(9000, Math.max(1500, cfg.length * 0.06))
      f.lane = 1 + Math.floor(Math.random() * (LANES - 1))
      f.x = (f.lane + 0.5) / LANES
      f.speed = BASE_SPEED
      f.passed = false
      activeRivals++
    }
  }

  // 路障：玩家每推进 400 像素有 30% 概率在前方 2000 处生成
  if (p.roadPos - lastSpawn > 400) {
    if (Math.random() < 0.3) {
      const lane = Math.floor(Math.random() * LANES)
      obstacles.push({
        lane,
        x: (lane + 0.5) / LANES,
        roadPos: p.roadPos + 2000,
        type: Math.random() < 0.5 ? 'car' : 'cone',
        dir: 1,
      })
    }
    // 迎面车流：开在最左车道朝你冲过来，相对速度是双方之和，撞上就是重摔
    if (Math.random() < 0.05) {
      obstacles.push({
        lane: 0,
        x: 0.5 / LANES,
        roadPos: p.roadPos + 4600,
        type: 'oncoming',
        dir: -1,
        speed: 9 + Math.random() * 3,
      })
    }
    lastSpawn = p.roadPos
  }

  // 迎面车逆向行驶
  for (const o of obstacles) {
    if (o.dir === -1) o.roadPos -= o.speed
  }

  // 碰撞分级：锥桶只是轻擦；路边车 / 迎面车直接摔车（飞起打转再落地）
  for (let i = obstacles.length - 1; i >= 0; i--) {
    const o = obstacles[i]
    const d = o.roadPos - p.roadPos
    const dx = Math.abs(o.x - p.x)
    let hit = false
    if (o.type === 'oncoming') {
      if (Math.abs(d) < 150 && dx < 0.17 && p.contactCd === 0) {
        p.durability -= 38
        p.contactCd = 30
        crashPlayer(p.x >= o.x ? 1 : -1)
        hit = true
      }
    } else if (Math.abs(d) < 200 && dx < 0.17 && p.contactCd === 0) {
      if (o.type === 'car') {
        p.durability -= 28
        p.contactCd = 30
        crashPlayer(p.x >= o.x ? 1 : -1)
      } else {
        p.speed = Math.max(3, p.speed * 0.62)
        p.durability -= 8
        p.contactCd = 14
        hitStop = 3
        bump(3, 0.12)
        addSparks(8, '#e2803c')
        rrSfx.impact(0.5)
      }
      hit = true
    }
    if (hit) { obstacles.splice(i, 1); continue }
    if (o.roadPos < p.roadPos - 600 || o.roadPos > p.roadPos + 14000) obstacles.splice(i, 1)
  }

  // 车车相撞：给真正的冲击 —— 车身被撞歪、横向被推开、速度掉一半、屏幕震一下
  for (const f of folks) {
    if (!f.alive) continue
    const d = f.roadPos - p.roadPos
    if (Math.abs(d) < 130 && Math.abs(f.x - p.x) < 0.17 && p.contactCd === 0) {
      const dir = p.x >= f.x ? 1 : -1
      p.durability -= f.isPolice ? 12 : 8
      f.durability -= 10
      p.lean += dir * 0.55
      p.x = Math.max(-0.03, Math.min(1.03, p.x + dir * 0.045))
      p.speed = Math.max(5, p.speed * 0.55)
      p.contactCd = 24
      hitStop = 4
      bump(5.5, 0.2)
      addSparks(12, '#ffd27a')
      rrSfx.impact(0.85)
      if (f.durability <= 0) knockDown(f)
    }
  }

  // 在线 ghost 车：向最新上报里程平滑靠拢（450ms 一次轮询，直接跳会一顿一顿）
  for (const g of ghosts) {
    if (g.targetDist != null) {
      const d = g.targetDist - g.roadPos
      g.roadPos = Math.abs(d) < 1 ? g.targetDist : g.roadPos + d * 0.14
    }
    if (g.targetX != null) g.x += (g.targetX - g.x) * 0.14
  }

  stepFx()

  if (p.durability <= 0) finish(false)
  else if (p.roadPos >= cfg.length) finish(true)
}

/* ---------- 绘制 ---------- */
function bikeInView(rel) {
  const y = objY(rel)
  return y > hzNow - 40 && y < H + 80
}

/* ================= 像素渲染层 =================
 * v2.46.162：按用户给的原版 Road Rash 截图重做画面。
 * 整幅场景先画在 400×233 的低分辨率缓冲上，再以最近邻放大到 1200×700：
 * 所有边缘都是硬像素块，没有渐变、抗锯齿与玻璃拟态。物理 / AI / 联机逻辑未动。
 */
const PIX = 3
const PW = Math.round(W / PIX)
const PH = Math.round(H / PIX)
let pbuf = null
let pctx = null
function pxBuf() {
  if (!pctx) {
    pbuf = document.createElement('canvas')
    pbuf.width = PW
    pbuf.height = PH
    pctx = pbuf.getContext('2d')
    pctx.imageSmoothingEnabled = false
  }
  return pctx
}
/** 游戏坐标 → 低分辨率像素坐标 */
function pu(v) { return Math.round(v / PIX) }
/** 确定性散列：同一位置的噪点每帧一致，不会闪成雪花 */
function hash(i) {
  let n = Math.imul(i ^ 0x9e3779b9, 0x85ebca6b)
  n ^= n >>> 13
  return ((n >>> 0) % 1000) / 1000
}

/** 当前扫描线对应的路面左右沿（像素坐标）+ 透视系数 */
function roadEdgeAt(py) {
  const gy = py * PIX
  const rel = (PLAYER_Y - gy) / 0.32
  const k = sc(gy)
  const rw = ROAD_W / PIX
  const base = PW / 2 + (bendAt(rel) - camX) * rw * k
  return { l: base, r: base + rw * k, k }
}

/** 像素圆盘：日月用（逐行 fillRect，边缘天然是阶梯状） */
function pixelDisc(g, cx, cy, r, color) {
  for (let y = -r; y <= r; y++) {
    const w = Math.floor(Math.sqrt(Math.max(0, r * r - y * y)))
    if (w <= 0) continue
    g.fillStyle = color
    g.fillRect(cx - w, cy + y, w * 2, 1)
  }
}

/** 远山 / 海岸线：逐像素列填充，底边做一层棋盘抖动 */
function drawRidge(ctx, pts, color, kf, dy, dither) {
  const hz = pu(hzNow)
  const shift = player ? (player.roadPos * (kf < 1 ? 0.010 : 0.018)) % W : 0
  for (let x = 0; x < PW; x++) {
    const gx = (x * PIX + shift) % W
    let top = hzNow
    for (let i = 1; i < pts.length; i++) {
      const x0 = pts[i - 1][0]
      const x1 = pts[i][0]
      if (gx >= x0 && gx <= x1) {
        const f = (gx - x0) / Math.max(1, x1 - x0)
        top = hzNow + (pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f) * kf + dy
        break
      }
    }
    const y0 = Math.max(0, pu(top))
    const y1 = Math.max(y0 + 1, hz + 1)
    ctx.fillStyle = color
    ctx.fillRect(x, y0, 1, y1 - y0)
    if (dither && y1 < PH && (x + y1) % 2 === 0) {
      ctx.fillStyle = dither
      ctx.fillRect(x, y1, 1, 1)
    }
  }
}

function drawSky(ctx, t) {
  const hz = pu(hzNow)
  const cuts = [0, 0.46, 0.78, 1]
  for (let i = 0; i < 3; i++) {
    const y0 = Math.round(hz * cuts[i])
    const y1 = Math.round(hz * cuts[i + 1])
    ctx.fillStyle = t.sky[i]
    ctx.fillRect(0, y0, PW, y1 - y0)
  }
  // 云：几层横向像素块，底部用暗色压一层
  const drift = player ? Math.floor(player.roadPos * 0.0035) : 0
  for (let i = 0; i < 7; i++) {
    const cw = 26 + Math.round(hash(i * 17 + 9) * 52)
    const cx0 = Math.round((hash(i * 31) * (PW + 80) + drift) % (PW + 80)) - 40
    const cy0 = 6 + Math.round(hash(i * 57 + 3) * (hz * 0.52))
    for (let r = 0; r < 5; r++) {
      const ww = Math.round(cw * (1 - Math.abs(r - 2) / 3))
      if (ww < 5) continue
      ctx.fillStyle = r >= 3 ? t.cloudShade : t.cloud
      ctx.fillRect(cx0 - (ww >> 1), cy0 + r * 2, ww, 2)
    }
  }
  // 星（夜城）
  if (t.stars) {
    for (let i = 0; i < 70; i++) {
      const x = Math.round(hash(i * 13 + 1) * PW)
      const y = Math.round(hash(i * 29 + 5) * hz * 0.8)
      ctx.fillStyle = i % 4 === 0 ? '#dfe8ff' : '#8fa4c8'
      ctx.fillRect(x, y, 1, 1)
    }
  }
  // 日 / 月：实心像素盘 + 稀疏辉光点
  if (t.orb) {
    const ox = Math.round(PW * t.orb.x)
    const oy = Math.round(hz * t.orb.y)
    const r = Math.max(4, pu(t.orb.r))
    for (let i = 0; i < 90; i++) {
      const a = hash(i * 7) * Math.PI * 2
      const rr = r + 2 + Math.floor(hash(i * 11 + 2) * r * 2.2)
      const px2 = Math.round(ox + Math.cos(a) * rr)
      const py2 = Math.round(oy + Math.sin(a) * rr)
      if (px2 < 0 || px2 >= PW || py2 < 0 || py2 >= hz) continue
      ctx.fillStyle = 'rgba(255,244,210,.55)'
      ctx.fillRect(px2, py2, 1, 1)
    }
    pixelDisc(ctx, ox, oy, r, t.orb.color)
  }
}

function drawGround(ctx, t) {
  const hz = pu(hzNow)
  ctx.fillStyle = t.ground
  ctx.fillRect(0, hz, PW, PH - hz)
  // 地平线压暗 + 抖动，避免一条硬直线
  for (let x = 0; x < PW; x++) {
    ctx.fillStyle = t.groundShade
    ctx.fillRect(x, hz, 1, 1 + Math.round(hash(x * 13 + 7) * 4))
  }
  if (t.scene === 'coast') {
    drawSea(ctx, t)
    drawCliff(ctx, t)
  } else if (t.scene === 'city') {
    drawCityGlow(ctx, t)
  } else {
    drawDunes(ctx, t)
  }
}

/** 海面：贴着右侧路肩，横向色带 + 白色浪花点 */
function drawSea(ctx, t) {
  const hz = pu(hzNow)
  const scroll = Math.floor((player ? player.roadPos : 0) / 40)
  for (let py = hz; py < PH; py++) {
    const e = roadEdgeAt(py)
    // v2.46.170：原来看起来「海占半屏、路面被挤成一条」，
    // 原因是海从路缘一路铺到画面右缘。这里给海面设上限（最多占画面 30%），
    // 路缘离得远时留出陆地/远岸，构图更接近原版。
    const seaMaxLeft = PW * 0.70
    const edge = Math.max(seaMaxLeft, Math.min(PW, Math.round(e.r + 8 * e.k)))
    if (edge >= PW) continue
    ctx.fillStyle = t.sea[0]
    ctx.fillRect(edge, py, PW - edge, 1)
    const band = (py + scroll) % 7
    if (band === 0) {
      ctx.fillStyle = t.sea[1]
      ctx.fillRect(edge, py, PW - edge, 1)
    } else if (band === 3) {
      ctx.fillStyle = t.sea[2]
      ctx.fillRect(edge, py, PW - edge, 1)
    }
    for (let x = edge + 2; x < PW; x += 7) {
      if (hash(x * 3 + py * 17 + scroll) > 0.78) {
        ctx.fillStyle = t.foam
        ctx.fillRect(x, py, 1, 1)
      }
    }
  }
}

/** 左侧土崖：紧贴左路肩，斜面纹路 + 碎石点（原版海岸关卡的主体背景） */
function drawCliff(ctx, t) {
  const hz = pu(hzNow)
  for (let py = hz; py < PH; py++) {
    const e = roadEdgeAt(py)
    // v2.46.170：同理限制土崖最大宽度（画面 24%），给路面留出空间
    const edge = Math.min(Math.round(PW * 0.24), Math.round(e.l - 10 * e.k))
    if (edge <= 0) continue
    ctx.fillStyle = t.cliff[0]
    ctx.fillRect(0, py, edge, 1)
    // 顶部受光亮边
    ctx.fillStyle = t.cliff[2]
    ctx.fillRect(0, py, edge, py < hz + 2 ? 1 : 0)
    // v2.46.179：水平分层色带 —— 大片纯色崖壁看起来像贴图，加几道沉积层才有土石感
    const layer = py % 26
    if (layer < 3) {
      ctx.fillStyle = t.cliff[1]
      ctx.fillRect(0, py, edge, 1)
    } else if (layer === 13) {
      ctx.fillStyle = t.cliff[2]
      ctx.fillRect(0, py, edge, 1)
    }
    // 斜纹：按行推进，形成连续斜线
    for (let s = 0; s < 6; s++) {
      const period = 24 + s * 13
      const sx = Math.floor((py * 1.7 + s * 37) % period)
      const w = Math.max(1, Math.round(edge / 70 - s * 0.35))
      if (sx < edge) {
        ctx.fillStyle = s % 2 ? t.cliff[1] : t.cliff[2]
        ctx.fillRect(sx, py, w, 1)
      }
    }
    // 碎石：密度 0.87 → 0.72，让崖面不再是平涂
    if (hash(py * 31) > 0.72) {
      ctx.fillStyle = t.cliff[1]
      const rx = Math.floor(hash(py * 17) * Math.max(1, edge - 3))
      ctx.fillRect(rx, py, 2, 1)
      if (hash(py * 53) > 0.6) ctx.fillRect(Math.max(0, rx - 4), py, 1, 1)
    }
  }
}

/** 沙地 / 林地的地表纹理：稀疏横条 + 色块，替代原来的渐变 */
function drawDunes(ctx, t) {
  const hz = pu(hzNow)
  for (let py = hz; py < PH; py++) {
    const band = t.scene === 'desert' ? 26 : 18
    for (let x = Math.floor(hash(py * 7) * band); x < PW; x += band) {
      if (hash(x * 5 + py * 23) > 0.62) {
        ctx.fillStyle = t.groundShade
        ctx.fillRect(x, py, 2 + Math.floor(hash(x + py) * 5), 1)
      }
    }
  }
}

/** 夜城：地平线附近的楼窗灯点 */
function drawCityGlow(ctx) {
  const hz = pu(hzNow)
  for (let x = 0; x < PW; x++) {
    for (let py = hz - 30; py < hz; py++) {
      if (hash(x * 91 + py * 37) > 0.986) {
        ctx.fillStyle = py % 3 === 0 ? '#ffd98a' : '#ffb45a'
        ctx.fillRect(x, py, 1, 1)
      }
    }
  }
}

/** 路面：逐像素行填色 —— 沥青、土路肩、双黄线、白边线全部吸附到像素网格。
 *  弯道仍由 bendAt 计算，所以压弯时整条路一起弯。 */
function drawRoad(ctx, t) {
  const hz = pu(hzNow)
  const scroll = Math.round(player ? player.roadPos : 0)
  for (let py = hz; py < PH; py++) {
    const e = roadEdgeAt(py)
    const l = Math.round(e.l)
    const r = Math.round(e.r)
    if (r <= 0 || l >= PW) continue
    const sw = Math.max(1, Math.round(13 * e.k))
    // 土路肩 + 外侧暗边
    ctx.fillStyle = t.shoulder
    ctx.fillRect(l - sw, py, sw, 1)
    ctx.fillRect(r, py, sw, 1)
    ctx.fillStyle = t.shoulderDark
    ctx.fillRect(l - sw, py, 1, 1)
    ctx.fillRect(r + sw - 1, py, 1, 1)
    // 沥青
    ctx.fillStyle = t.road
    ctx.fillRect(l, py, Math.max(1, r - l), 1)
    // 轮胎压痕：两条更暗的纵向带
    const tw = Math.max(1, Math.round((r - l) * 0.19))
    ctx.fillStyle = t.tyre ?? t.roadDark
    ctx.fillRect(Math.round(l + (r - l) * 0.17), py, tw, 1)
    ctx.fillRect(Math.round(l + (r - l) * 0.64), py, tw, 1)
    // 沥青颗粒：确定性噪点 + 里程滚动
    // v2.46.179：原来每行只撒 3 个点、命中率 30%，缩放到 3 倍后完全看不出颗粒感；
    // 加密到 9 个点 / 命中率 50%，路面才有粗糙的沥青质感。
    const grain = Math.min(9, Math.max(4, Math.round((r - l) / 12)))
    for (let i = 0; i < grain; i++) {
      const n = hash(py * 131 + i * 977 + Math.floor(scroll / 40))
      if (n > 0.5) {
        ctx.fillStyle = n > 0.82 ? t.roadLight : t.roadDark
        ctx.fillRect(l + Math.floor(hash(py * 37 + i * 7) * (r - l)), py, 1, 1)
      }
    }
    // 白色边线（v2.46.179：1px 在 3 倍缩放下几乎消失，加粗到 2px）
    ctx.fillStyle = t.edge
    const ew = Math.max(1, Math.round(2.4 * e.k))
    ctx.fillRect(l + Math.max(1, Math.round(2 * e.k)), py, ew, 1)
    ctx.fillRect(r - Math.max(1, Math.round(2 * e.k)) - ew, py, ew, 1)
    // 沥青补丁：每 900 像素一处不规则暗斑，路面不再是一条平涂
    const linePos = (player ? player.roadPos : 0) + (PLAYER_Y - py * PIX) / 0.32
    const patch = Math.floor(linePos / 900)
    if (hash(patch * 617) > 0.4) {
      const px0 = hash(patch * 131) * 0.7 + 0.12
      const pw = 0.1 + hash(patch * 733) * 0.16
      const a = Math.max(l, Math.round(l + (r - l) * px0))
      const bb = Math.min(r, Math.round(l + (r - l) * (px0 + pw)))
      if (bb > a && linePos % 900 < 170) {
        ctx.fillStyle = t.roadDark
        ctx.fillRect(a, py, bb - a, 1)
      }
    }
    // 双黄线：原版公路的中心线，两条线中间留 1px
    const cx1 = Math.round((l + r) / 2)
    ctx.fillStyle = t.dash
    const lw = Math.max(1, Math.round(1.6 * e.k))
    ctx.fillRect(cx1 - 2 - lw, py, lw, 1)
    ctx.fillRect(cx1 + 2, py, lw, 1)
  }
  // 路面接缝：每 1400 像素一条暗横带
  const jointStep = 1400
  const jb = Math.floor((player ? player.roadPos : 0) / jointStep)
  for (let i = jb; i < jb + 2; i++) {
    const rel = i * jointStep - (player ? player.roadPos : 0)
    if (rel < 40 || rel > VIEW_REL - 30) continue
    const py = pu(objY(rel))
    const e = roadEdgeAt(py)
    if (e.r <= e.l) continue
    ctx.fillStyle = 'rgba(18,18,22,.62)'
    ctx.fillRect(Math.round(e.l), py, Math.max(1, Math.round(e.r - e.l)), 2)
  }
}

/** 路旁景物：按 roadPos 分格推进，左右交替（远 → 近绘制）。
 *  原版路边是「有节奏的密集物」：护栏桩 + 树 + 路牌交替出现，不是稀疏点缀。 */
function drawScenery(ctx, t) {
  if (!player) return
  const step = 220
  const base = Math.floor(player.roadPos / step)
  for (let i = base + 10; i >= base; i--) {
    const rel = i * step - player.roadPos
    const y = objY(rel)
    if (y <= hzNow + 6 || y > H + 40) continue
    const k = sc(y)
    const side = i % 2 === 0 ? -1 : 1
    const offX = 0.54 + ((i * 53) % 56) / 900
    // 海岸：左侧是土崖，只放右侧棕榈；其它场景两侧都放
    if (t.scene === 'coast' && side < 0) continue
    // 每 7 格插一根护栏桩（更靠外沿），形成连续的护栏节奏
    if (i % 7 === 3) {
      drawProp(ctx, wpX(0.5 + side * 0.52, y, rel), y, k, 'post')
      continue
    }
    // 每 11 格插一块路牌
    if (i % 11 === 5) {
      drawProp(ctx, wpX(0.5 + side * 0.6, y, rel), y, k, 'sign')
      continue
    }
    const kind = (t.scene === 'valley' && i % 3 === 0) ? 'rock' : t.prop
    drawProp(ctx, wpX(0.5 + side * offX, y, rel), y, k, kind)
  }
}

/** 路旁景物像素精灵：全部用整数方块拼，没有圆角与渐变 */
function drawProp(ctx, x, y, k, kind) {
  const xp = Math.round(x / PIX)
  const yp = Math.round(y / PIX)
  const s = Math.max(0.3, k)
  const R = (lx, ly, w, h, c) => {
    ctx.fillStyle = c
    ctx.fillRect(
      Math.round(xp + lx * s), Math.round(yp + ly * s),
      Math.max(1, Math.round(w * s)), Math.max(1, Math.round(h * s)),
    )
  }
  if (kind === 'palm') {
    R(-1, -30, 2, 30, '#7a5a38')
    R(-2, -33, 4, 3, '#6a4c30')
    R(-13, -30, 12, 2, '#2f5a32')
    R(1, -30, 13, 2, '#2f5a32')
    R(-10, -34, 10, 2, '#3a6a3a')
    R(2, -34, 9, 2, '#3a6a3a')
    R(-6, -38, 12, 3, '#2d5630')
    R(-4, -40, 8, 2, '#24482a')
  } else if (kind === 'pine') {
    R(-1, -26, 2, 26, '#5a4028')
    R(-8, -30, 16, 6, '#2f5c3c')
    R(-6, -37, 12, 7, '#2a5236')
    R(-4, -44, 8, 7, '#244a2e')
  } else if (kind === 'cactus') {
    R(-2, -26, 4, 26, '#3f6b4a')
    R(-2, -26, 4, 3, '#4f7b5a')
    R(-8, -20, 6, 2, '#3f6b4a')
    R(-8, -20, 2, 9, '#3f6b4a')
    R(2, -16, 7, 2, '#3f6b4a')
    R(7, -16, 2, 7, '#3f6b4a')
  } else if (kind === 'rock') {
    R(-6, -8, 12, 8, '#6b7480')
    R(-4, -12, 8, 4, '#7a8492')
    R(-6, -4, 5, 4, '#58606c')
  } else if (kind === 'lamp') {
    R(-1, -38, 2, 38, '#48566b')
    R(-8, -40, 8, 2, '#48566b')
    R(-9, -43, 5, 3, '#ffe8a8')
    for (let i = 0; i < 10; i++) {
      ctx.fillStyle = 'rgba(255,232,168,.5)'
      const gx = Math.round(xp + (-6 + hash(i * 3) * 12) * s)
      const gy = Math.round(yp + (-46 - hash(i * 7) * 8) * s)
      ctx.fillRect(gx, gy, 1, 1)
    }
  } else if (kind === 'post') {
    // 护栏桩：白柱 + 反光条 + 一道横栏
    R(-1, -9, 2, 9, '#d0ccbc')
    R(-1, -6, 2, 2, '#c8402f')
    R(-5, -8, 10, 1, '#a8a494')
  } else if (kind === 'sign') {
    // 路牌：立柱 + 方形黄牌（原版常见的那种警示牌）
    R(0, -13, 1, 13, '#6a6a64')
    R(-5, -20, 10, 7, '#d8b83c')
    R(-5, -20, 10, 1, '#f0d868')
    R(-3, -18, 6, 1, '#2a2a2a')
    R(-3, -15, 4, 1, '#2a2a2a')
  }
}

/** 颜色提亮 / 压暗：给纯色块加一点体积感（渐变打光），避免整台车像一张卡纸 */
function shade(hex, k) {
  if (typeof hex !== 'string' || !/^#[0-9a-fA-F]{6}$/.test(hex)) return hex
  const n = parseInt(hex.slice(1), 16)
  const r = Math.min(255, Math.round(((n >> 16) & 255) * k))
  const g = Math.min(255, Math.round(((n >> 8) & 255) * k))
  const bl = Math.min(255, Math.round((n & 255) * k))
  return `rgb(${r},${g},${bl})`
}

/** 骑手 + 摩托的后视精灵 —— 按原版截图重画（不是一行行点阵，而是分层拼块）：
 *  下方是宽后胎 / 挡泥板 / 双排气 / 尾罩 + 尾灯 + 牌照，上方是跨坐的腿、皮衣、
 *  头盔和两只伸向车把的手臂。压弯时按高度做横向剪切（轮胎不动、头肩偏得最多），
 *  出拳用独立姿势帧：蓄力 → 前击 / 后击 → 收招。 */
const RIDER_W = 60
const RIDER_H = 68
const riderCache = new Map()

function riderPal(color, police) {
  const B = police ? POLICE_COLOR : color
  const P = '#2a2e38'
  const D = shade(B, 0.44)
  return {
    // 深色头盔 + 车色条纹：原版骑手多戴深盔，浅色圆顶压在皮衣上会像颗蛋
    H: police ? '#e8e4d6' : '#3a4150',
    h: police ? '#9c988c' : '#232833',
    S: police ? '#dfe6f2' : shade(B, 1.25),
    V: '#2e323c',
    B, L: shade(B, 1.28), D, X: shade(B, 0.3),
    P, p: '#464e5c',
    K: '#141418', k: '#2e3038', G: '#a2a8b0', g: '#5e6470',
    R: '#e0463a', W: '#f2f2ea', Y: '#d8a882', N: '#262a34',
  }
}

/** pose: 0 骑乘 / 1 蓄力 / 2 前击 / 3 后击 / 4 收招 */
function riderSprite(color, bucket, pose, police) {
  const key = `${color}|${bucket}|${pose}|${police ? 1 : 0}`
  const hit = riderCache.get(key)
  if (hit) return hit
  const c = document.createElement('canvas')
  c.width = RIDER_W
  c.height = RIDER_H
  const g = c.getContext('2d')
  const pal = riderPal(color, police)
  const OX = RIDER_W / 2
  const baseY = RIDER_H - 1
  // 压弯：轮胎不动，越往上的部位横向偏得越多
  const shear = (y) => Math.round(bucket * Math.max(0, y - 26) / 42 * 7)
  /** 方块坐标：x 相对车身中线，y 是底边（向上为正），tw 是出拳时的躯干扭转 */
  const R = (x, y, w, h, col, tw = 0) => {
    g.fillStyle = col
    g.fillRect(Math.round(OX + x + shear(y) + tw), baseY - y - h, Math.max(1, w), Math.max(1, h))
  }

  /* ---- 摩托（后视）：后胎在下，挡泥板/尾灯/牌照在上，两侧排气 ---- */
  R(-6, 0, 12, 2, pal.K)
  R(-8, 2, 16, 5, pal.K)
  R(-9, 7, 18, 8, pal.K)
  R(-8, 15, 16, 2, pal.K)
  R(-6, 4, 12, 1, pal.k)
  R(-8, 9, 16, 1, pal.k)
  R(-7, 13, 14, 1, pal.k)
  R(-3, 5, 6, 4, pal.G)
  R(-1, 6, 2, 2, pal.g)
  R(-6, 16, 3, 5, pal.g)
  R(3, 16, 3, 5, pal.g)
  R(-12, 15, 24, 3, pal.D)
  R(-11, 18, 22, 7, pal.B)
  R(-11, 18, 22, 2, pal.X)
  R(-3, 21, 6, 3, pal.R)
  R(-14, 12, 5, 7, pal.G)
  R(9, 12, 5, 7, pal.G)
  R(-14, 11, 5, 2, pal.g)
  R(9, 11, 5, 2, pal.g)
  R(-10, 19, 2, 2, '#e8a33a')
  R(8, 19, 2, 2, '#e8a33a')

  /* ---- 座垫 + 臀腿：和车身、上身都重叠一两格，避免出现「漂浮的黑缝」 ---- */
  R(-9, 25, 18, 6, '#262b34')
  R(-9, 30, 18, 7, pal.P)
  R(-13, 26, 5, 10, pal.P)
  R(8, 26, 5, 10, pal.P)
  R(-13, 34, 5, 2, pal.p)
  R(8, 34, 5, 2, pal.p)
  R(-14, 24, 6, 3, pal.X)
  R(8, 24, 6, 3, pal.X)

  const twist = pose === 2 ? 2 : pose === 3 ? -2 : 0

  /* ---- 躯干：收腰皮衣、斜肩；背上一块暗色俱乐部标 ---- */
  R(-10, 36, 20, 7, pal.B, twist)
  R(-12, 42, 24, 8, pal.B, twist)
  R(-13, 49, 26, 3, pal.B, twist)
  R(-11, 52, 22, 3, pal.B, twist)
  R(-13, 49, 4, 3, pal.L, twist)
  R(9, 49, 4, 3, pal.L, twist)
  R(-13, 49, 2, 5, pal.D, twist)
  R(11, 49, 2, 5, pal.D, twist)
  R(-5, 41, 10, 7, pal.D, twist)
  R(-1, 41, 2, 7, pal.S, twist)
  R(-6, 54, 12, 2, pal.N, twist)

  /* ---- 头盔：圆盔背壳（上下收窄），两条护耳 + 纵向条纹 ---- */
  R(-8, 54, 16, 2, pal.h, twist)
  R(-9, 56, 17, 5, pal.H, twist)
  R(-8, 61, 15, 2, pal.H, twist)
  R(-6, 63, 11, 1, pal.H, twist)
  R(-1, 56, 2, 7, pal.S, twist)
  R(-9, 56, 2, 4, pal.V, twist)
  R(8, 56, 2, 4, pal.V, twist)

  /* ---- 手臂：袖子比躯干暗一档，手臂伸到躯干轮廓之外才看得出是胳膊 ---- */
  // 左手（画面左）：后击时向下后方甩出
  if (pose === 3) {
    R(-15, 48, 5, 5, pal.D, twist)
    R(-19, 43, 5, 5, pal.D, twist)
    R(-23, 37, 5, 6, pal.D, twist)
    R(-26, 34, 4, 4, pal.W, twist)
  } else {
    R(-16, 50, 4, 6, pal.D, twist)
    R(-19, 44, 4, 7, pal.D, twist)
    R(-20, 41, 4, 3, pal.W, twist)
  }
  // 右手（画面右）：前击向上前方伸出
  if (pose === 1) {
    R(5, 44, 6, 7, pal.D, twist)
    R(1, 43, 4, 4, pal.W, twist)
  } else if (pose === 2) {
    R(10, 49, 5, 5, pal.D, twist)
    R(14, 52, 5, 5, pal.D, twist)
    R(18, 56, 5, 5, pal.D, twist)
    R(21, 60, 4, 4, pal.W, twist)
  } else if (pose === 4) {
    R(10, 48, 5, 5, pal.D, twist)
    R(14, 47, 5, 4, pal.D, twist)
    R(17, 46, 4, 3, pal.W, twist)
  } else {
    R(12, 50, 4, 6, pal.D, twist)
    R(15, 44, 4, 7, pal.D, twist)
    R(16, 41, 4, 3, pal.W, twist)
  }
  // 车把端头（只在骑乘 / 收招时露出）
  if (pose === 0 || pose === 4) {
    R(-23, 41, 3, 2, pal.g)
    R(19, 41, 3, 2, pal.g)
  }

  // ---- v2.46.179：给精灵加 1px 深色描边 ----
  // 低分辨率像素画（60×68）在 3 倍缩放下，相邻色块容易糊成一坨「红方块」，
  // 分不清头盔 / 手臂 / 车胎。描边是把轮廓勾出来的最有效手段：
  // 先把原图做成纯色剪影，向 8 个方向各偏移 1px 垫底，最后把原图盖回去。
  const OUT = 1
  const outlined = document.createElement('canvas')
  outlined.width = RIDER_W + OUT * 2
  outlined.height = RIDER_H + OUT * 2
  const og = outlined.getContext('2d')
  const sil = document.createElement('canvas')
  sil.width = RIDER_W
  sil.height = RIDER_H
  const sg = sil.getContext('2d')
  sg.drawImage(c, 0, 0)
  sg.globalCompositeOperation = 'source-in'
  sg.fillStyle = '#101318'
  sg.fillRect(0, 0, RIDER_W, RIDER_H)
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    og.drawImage(sil, OUT + dx, OUT + dy)
  }
  og.drawImage(c, OUT, OUT)

  riderCache.set(key, outlined)
  return outlined
}

/** 攻击进度 → 精灵姿势帧（0 骑乘 / 1 蓄力 / 2 前击 / 3 后击 / 4 收招） */
function attackPose(b) {
  if (!b.atkType) return 0
  if (b.atkAge < 5) return 1
  if (b.atkAge < 13) return b.atkType === 'forward' ? 2 : 3
  if (b.atkAge < 22) return 4
  return 0
}

/** 像素直线：用整数方块拼，斜线也不会出现抗锯齿 */
function pxLine(ctx, x0, y0, x1, y1, color, size) {
  const steps = Math.max(1, Math.round(Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0))))
  ctx.fillStyle = color
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    ctx.fillRect(Math.round(x0 + (x1 - x0) * t), Math.round(y0 + (y1 - y0) * t), size, size)
  }
}

const WEAPON_COLOR = { whip: '#a8332a', stick: '#8a5a2c', chain: '#c8ccd4', baton: '#2a2e36' }

/** 后视摩托 + 骑手：压弯换倾斜帧、出拳换动作帧、摔车整块旋转 */
function drawBike(ctx, x, y, k, b, dead) {
  if (!b) return
  const lean = dead ? 0 : (b.lean || 0)
  const bucket = Math.max(-2, Math.min(2, Math.round(lean * 2.4)))
  const color = dead ? '#6b7280' : (b.color || '#e05a4a')
  const pose = dead ? 0 : attackPose(b)
  const spr = riderSprite(color, bucket, pose, !!b.isPolice)
  // v2.46.170：原来玩家 0.82、对手 0.74，在 400px 宽的低分辨率画布上只有 40 多像素，
  // 细看也分不出头盔/手臂/车胎 —— 放大到 1.12 / 1.0，人形和出拳姿态才看得出来
  const scale = Math.max(0.42, k * (b.isPlayer ? 1.12 : 1.0))
  const w = Math.round(spr.width * scale)
  const h = Math.round(spr.height * scale)
  const xp = Math.round(x / PIX)
  const yp = Math.round(y / PIX)
  const crashK = !dead && b.crash ? 1 - b.crash / CRASH_FRAMES : 0
  const recoil = !dead && b.hitT > 0 ? (b.hitDir || 1) * 2 : 0
  // v2.46.179：地面投影 —— 之前没有任何影子，车看起来是「贴」在路面上的。
  // 用 3 条宽度递减的横线拼一个压扁的像素椭圆（与低分辨率像素画风一致，不用 ellipse 抗锯齿）。
  if (!dead && crashK <= 0) {
    const halfW = Math.max(3, Math.round(w * 0.36))
    ctx.save()
    ctx.globalAlpha = 0.32
    ctx.fillStyle = '#080a0e'
    for (let i = 0; i < 3; i++) {
      const ww = Math.max(2, Math.round(halfW * (1 - i * 0.26)))
      ctx.fillRect(Math.round(xp + recoil - ww / 2), Math.round(yp - 2 + i), ww, 1)
    }
    ctx.restore()
  }
  ctx.save()
  if (crashK > 0 || dead) {
    ctx.translate(xp, yp - h * 0.42)
    ctx.rotate(dead ? 1.1 : (b.crashDir || 1) * Math.min(1, crashK) * 2.6)
    ctx.drawImage(spr, Math.round(-w / 2), Math.round(-h * 0.5), w, h)
  } else {
    ctx.drawImage(spr, Math.round(xp - w / 2 + recoil), Math.round(yp - h), w, h)
  }
  ctx.restore()

  // 警灯：车顶红蓝爆闪
  if (b.isPolice && !dead) {
    const on = Math.floor(flipClock / 24) % 2 === 0
    const ly = Math.round(yp - h - 3)
    ctx.fillStyle = on ? '#e5484d' : '#3b82f6'
    ctx.fillRect(Math.round(xp - 6), ly, 5, 2)
    ctx.fillStyle = on ? '#3b82f6' : '#e5484d'
    ctx.fillRect(Math.round(xp + 1), ly, 5, 2)
  }

  // 手里的家伙：空手不画；骑乘时斜挎在背后，出拳时跟着拳头甩出去
  if (!dead && b.weapon && b.weapon !== 'fist') {
    const wc = WEAPON_COLOR[b.weapon] || '#8a5a2c'
    const ox = xp - w / 2 + recoil
    const oy = yp - h
    const P = (sx, sy) => [ox + (sx + RIDER_W / 2) * scale, oy + (RIDER_H - 1 - sy) * scale]
    if (pose === 0) {
      const a = P(-14, 40)
      const c2 = P(14, 58)
      pxLine(ctx, a[0], a[1], c2[0], c2[1], wc, 2)
    } else {
      const fist = pose === 2 ? [25, 66] : pose === 3 ? [-25, 40] : pose === 1 ? [4, 51] : [20, 52]
      const f = P(fist[0], fist[1])
      const dx = pose === 3 ? -0.85 : 0.7
      const dy = pose === 3 ? -0.5 : 0.75
      const len = (pose === 1 ? 9 : 16) * scale * 1.4
      const tx = f[0] + dx * len
      const ty = f[1] - dy * len
      pxLine(ctx, f[0], f[1], tx, ty, wc, 2)
      if (b.weapon === 'chain') {
        ctx.fillStyle = wc
        ctx.fillRect(Math.round(tx) - 1, Math.round(ty) - 1, 3, 3)
      }
    }
  }

  // 出拳瞬间的速度残影：拳外侧两颗白点（空手也画）
  if (!dead && pose === 2) {
    ctx.fillStyle = '#f4f6fa'
    ctx.fillRect(Math.round(xp + w * 0.4), Math.round(yp - h * 0.95), 2, 1)
    ctx.fillRect(Math.round(xp + w * 0.46), Math.round(yp - h * 0.88), 1, 1)
  } else if (!dead && pose === 3) {
    ctx.fillStyle = '#f4f6fa'
    ctx.fillRect(Math.round(xp - w * 0.42), Math.round(yp - h * 0.45), 2, 1)
    ctx.fillRect(Math.round(xp - w * 0.48), Math.round(yp - h * 0.52), 1, 1)
  }

  // 被击中：白色像素闪一下（1 帧内的高光块）
  if (!dead && b.hitT > 0) {
    ctx.fillStyle = 'rgba(255,255,255,.45)'
    ctx.fillRect(Math.round(xp - w * 0.18), Math.round(yp - h * 0.9), Math.round(w * 0.36), Math.round(h * 0.38))
  }

  // 在线名牌（原版没有，联机才显示）
  const topY = Math.round(yp - h - 10)
  if (b.isPlayer && netOn.value && !dead) {
    drawNameTag(ctx, xp, topY, '我', '#e2c16a')
  } else if (b.tag) {
    drawNameTag(ctx, xp, topY, b.tag, b.color)
  }
}

/** 头顶名牌（像素坐标，低分辨率下直接渲染） */
function drawNameTag(ctx, x, y, text, color) {
  const label = String(text).slice(0, 6)
  ctx.font = '8px "Microsoft YaHei", sans-serif'
  const w = Math.ceil(ctx.measureText(label).width) + 8
  ctx.fillStyle = 'rgba(10,14,22,.8)'
  ctx.fillRect(Math.round(x - w / 2), y - 9, w, 11)
  ctx.fillStyle = color
  ctx.fillRect(Math.round(x - w / 2) + 2, y - 5, 2, 2)
  ctx.fillStyle = '#eef1f6'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'top'
  ctx.fillText(label, Math.round(x - w / 2) + 6, y - 8)
}

/** 地上掉落的武器：小图标 + 上下浮动的黄点提示（打倒对手后开过去捡） */
function drawDrop(ctx, x, y, k, d) {
  const xp = Math.round(x / PIX)
  const yp = Math.round(y / PIX)
  const s = Math.max(0.35, k)
  const bob = Math.round(Math.sin(flipClock * 0.12) * 2)
  const wc = WEAPON_COLOR[d.weapon] || '#8a5a2c'
  const len = Math.max(5, Math.round(16 * s))
  ctx.fillStyle = 'rgba(8,10,16,.45)'
  ctx.fillRect(Math.round(xp - len / 2), yp - 2, len + 2, 3)
  ctx.fillStyle = wc
  ctx.fillRect(Math.round(xp - len / 2), yp - 4 - bob, len, 2)
  ctx.fillStyle = '#ffe08a'
  ctx.fillRect(xp - 1, yp - 10 - bob, 2, 2)
}

/** 路障 / 车流：像素精灵。迎面车画车头（大灯正对你），抛锚车画车尾 */
function drawObstacle(ctx, x, y, k, o) {
  const xp = Math.round(x / PIX)
  const yp = Math.round(y / PIX)
  const s = Math.max(0.3, k)
  const R = (lx, ly, w, h, c) => {
    ctx.fillStyle = c
    ctx.fillRect(
      Math.round(xp + lx * s), Math.round(yp + ly * s),
      Math.max(1, Math.round(w * s)), Math.max(1, Math.round(h * s)),
    )
  }
  if (o.type === 'oncoming') {
    R(-20, -28, 40, 14, '#c8c8c0')
    R(-18, -40, 36, 12, '#8fa0b0')
    R(-20, -16, 40, 3, '#a8a8a0')
    R(-16, -26, 7, 4, '#ffe89a')
    R(9, -26, 7, 4, '#ffe89a')
    R(-4, -26, 8, 5, '#3a3a40')
    R(-21, -6, 5, 6, '#141418')
    R(16, -6, 5, 6, '#141418')
  } else if (o.type === 'car') {
    R(-19, -32, 38, 32, '#8a5a34')
    R(-14, -44, 28, 14, '#242a33')
    R(-12, -42, 24, 8, '#4a6070')
    R(-15, -24, 6, 4, '#ff4d4d')
    R(9, -24, 6, 4, '#ff4d4d')
    R(-20, -6, 6, 6, '#141418')
    R(14, -6, 6, 6, '#141418')
  } else {
    R(-5, -10, 10, 10, '#e2803c')
    R(-5, -6, 10, 2, '#f2f4f8')
    R(-6, -1, 12, 2, '#d0d0c8')
  }
}

/** 高速时两侧的像素风线（只在极速时出现，不抢画面） */
function drawSpeedLines(ctx, spd) {
  if (spd < 0.72) return
  const n = Math.round((spd - 0.7) * 34)
  for (let i = 0; i < n; i++) {
    const side = i % 2 ? 1 : -1
    const x = Math.round(PW / 2 + side * (108 + hash(i * 13) * 46))
    const y = Math.round(54 + ((flipClock * 6 + i * 37) % 140))
    ctx.fillStyle = 'rgba(240,246,255,.5)'
    ctx.fillRect(x, y, 1, 3)
  }
}

/** 低分辨率缓冲 → 主画布：最近邻放大，这是像素颗粒感的来源 */
function blit(out) {
  out.imageSmoothingEnabled = false
  out.drawImage(pbuf, 0, 0, W, H)
}

function draw() {
  const cv = cvEl.value
  if (!cv) return
  const g = pxBuf()
  const out = cv.getContext('2d')
  const t = track.value
  hzNow = HORIZON + hillAt(player ? player.roadPos : 0)
  g.imageSmoothingEnabled = false
  g.clearRect(0, 0, PW, PH)

  drawSky(g, t)
  drawRidge(g, t.peaks, t.farPeaks, 0.58, 0, t.cloudShade)
  drawRidge(g, t.peaks, t.nearPeaks, 1, 0, null)
  drawGround(g, t)

  const p = player
  if (!p) { blit(out); return }
  const spd = Math.min(1, st.speed / Math.max(1, p.maxSpeed))
  // 震屏幅度换算到低分辨率像素，再取整 —— 抖动时依然是整像素位移
  const amp = ((st.onGrass ? 3.4 : 1.15) * spd + impact.shake) / PIX
  g.save()
  g.translate(
    Math.round(Math.sin(flipClock * 0.83) * amp + (Math.random() - 0.5) * impact.shake / PIX * 1.6),
    Math.round(Math.cos(flipClock * 1.17) * amp * 0.7 + (Math.random() - 0.5) * impact.shake / PIX * 1.2),
  )

  drawRoad(g, t)
  drawScenery(g, t)
  // 地平线薄雾：抖动点，不遮车
  for (let y = pu(HORIZON); y < pu(HORIZON) + 10; y++) {
    for (let x = 0; x < PW; x += 2) {
      if (hash(x * 7 + y * 131) > 0.72) {
        g.fillStyle = t.sky[2]
        g.fillRect(x, y, 1, 1)
      }
    }
  }
  drawSpeedLines(g, spd)

  // 实体：远的先画（画面纵深），玩家最后画
  const drawList = []
  for (const o of obstacles) drawList.push({ rel: o.roadPos - p.roadPos, kind: 'o', o })
  for (const d of drops) drawList.push({ rel: d.roadPos - p.roadPos, kind: 'd', o: d })
  for (const f of folks) drawList.push({ rel: f.roadPos - p.roadPos, kind: 'b', b: f })
  for (const gh of ghosts) drawList.push({ rel: gh.roadPos - p.roadPos, kind: 'b', b: gh })
  drawList.sort((a, b) => b.rel - a.rel)
  for (const it of drawList) {
    if (!bikeInView(it.rel)) continue
    const y = objY(it.rel)
    const k = sc(y)
    if (it.kind === 'o') drawObstacle(g, wpX(it.o.x, y, it.rel), y, k, it.o)
    else if (it.kind === 'd') drawDrop(g, wpX(it.o.x, y, it.rel), y, k, it.o)
    else drawBike(g, wpX(it.b.x, y, it.rel), y, k, it.b, !it.b.alive)
  }

  // 玩家：永远在画面正下方中央；摔车时整车被甩出去、飞起来打转再落地
  const crashK = p.crash > 0 ? 1 - p.crash / CRASH_FRAMES : 0
  const lift = crashK > 0 ? Math.sin(crashK * Math.PI) * 112 : 0
  const pushX = crashK > 0 ? p.crashDir * 46 * crashK : 0
  const frameX = (p.x - camX) * ROAD_W
  const bob = Math.sin(flipClock * 0.9) * (1.0 + spd * 3.2)
    + (st.onGrass ? Math.sin(flipClock * 2.4) * 5 : 0)
  drawBike(g, CX + pushX + frameX, PLAYER_DRAW_Y + 4 - lift - bob, 1, p, false)

  // 火花：1~2 像素方块
  for (const s of sparks) {
    g.globalAlpha = Math.max(0, Math.min(1, s.life / 30))
    g.fillStyle = s.color
    g.fillRect(Math.round(s.x / PIX), Math.round(s.y / PIX), 2, 2)
  }
  g.globalAlpha = 1

  g.restore()

  drawHud(g, t)

  // 撞击闪屏（红色一层，快速衰减）
  if (impact.flash > 0.02) {
    g.fillStyle = `rgba(196,44,38,${Math.min(0.5, impact.flash * 0.55)})`
    g.fillRect(0, 0, PW, PH)
  }
  blit(out)
}

/** 像素风面板：实心暗底 + 1px 硬边框（没有圆角、没有毛玻璃） */
function panel(g, x, y, w, h, border) {
  g.fillStyle = 'rgba(10,14,22,.78)'
  g.fillRect(x, y, w, h)
  g.strokeStyle = border || '#8a7a4a'
  g.lineWidth = 1
  g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1)
}

function drawHud(ctx, t) {
  const g = ctx
  g.textBaseline = 'top'

  // 左上：速度 + 段式耐久条
  panel(g, 8, 6, 126, 44)
  g.textAlign = 'left'
  g.fillStyle = '#e8d8a8'
  g.font = 'bold 18px "Courier New", monospace'
  g.fillText(String(Math.round(st.speed * 10)), 14, 8)
  g.fillStyle = '#a8b0bc'
  g.font = '8px "Microsoft YaHei", sans-serif'
  g.fillText('KM/H', 64, 18)
  g.fillStyle = '#d8ccae'
  g.fillText('耐久', 14, 32)
  const ratio = Math.max(0, Math.min(1, st.durability / (player?.maxDurability || 100)))
  for (let i = 0; i < 12; i++) {
    g.fillStyle = i < Math.round(ratio * 12)
      ? (ratio > 0.5 ? '#7fc4a5' : ratio > 0.25 ? '#e2c16a' : '#e5484d')
      : '#2a2e36'
    g.fillRect(38 + i * 7, 33, 6, 8)
  }

  // 右上：名次 + 距离 + 进度段
  const rank = 1 + folks.filter((f) => f.alive && f.roadPos > (player?.roadPos || 0)).length
  panel(g, PW - 118, 6, 110, 44)
  g.textAlign = 'right'
  g.fillStyle = rank <= 4 ? '#e8d8a8' : '#ff9c8c'
  g.font = 'bold 18px "Courier New", monospace'
  g.fillText(String(rank), PW - 78, 8)
  g.fillStyle = '#a8b0bc'
  g.font = '8px "Microsoft YaHei", sans-serif'
  g.fillText('名次', PW - 62, 18)
  g.fillStyle = '#d8ccae'
  g.fillText(`${meters(st.dist)} / ${meters(cfg.length)} m`, PW - 12, 31)
  const prog = Math.max(0, Math.min(1, st.dist / cfg.length))
  for (let i = 0; i < 23; i++) {
    g.fillStyle = i < Math.round(prog * 23) ? '#c7a96b' : '#2a2e36'
    g.fillRect(PW - 118 + 7 + i * 4, 43, 3, 3)
  }

  // 画面顶部细条：赛道 / 车款 / 最高分
  g.textAlign = 'left'
  g.fillStyle = 'rgba(240,232,205,.8)'
  g.font = '8px "Microsoft YaHei", sans-serif'
  g.fillText(`${t.label} · ${bike.value.label} · ${WEAPON_LABEL[player?.weapon] || '空手'}`, 10, 55)
  if (!netOn.value) {
    g.textAlign = 'right'
    g.fillText(`最高 ${best.value}`, PW - 10, 55)
  }

  if (netOn.value) drawLeaderboard(g)

  // 压弯指示 + 出界 / 摔车提示
  if (phase.value === 'run') {
    const gx = 60
    const gy = PH - 18
    g.fillStyle = 'rgba(10,14,22,.7)'
    g.fillRect(gx - 34, gy - 7, 68, 14)
    g.fillStyle = '#2a2e36'
    g.fillRect(gx - 26, gy - 2, 52, 4)
    g.fillStyle = Math.abs(st.lean) > 0.6 ? '#e2c16a' : '#e8eef4'
    g.fillRect(Math.round(gx + Math.max(-1, Math.min(1, st.lean)) * 24) - 2, gy - 5, 3, 9)
    g.fillStyle = 'rgba(216,204,174,.75)'
    g.font = '7px "Microsoft YaHei", sans-serif'
    g.textAlign = 'center'
    g.fillText('压弯', gx, gy + 8)
    if (st.onGrass) {
      g.fillStyle = '#ff9c8c'
      g.font = 'bold 11px "Microsoft YaHei", sans-serif'
      g.fillText('冲出路面 · 快压回来', PW / 2, PH - 56)
    }
    if (player && player.crash > 0) {
      g.fillStyle = '#ffd27a'
      g.font = 'bold 14px "Microsoft YaHei", sans-serif'
      g.fillText('摔车！', PW / 2, PH - 80)
    }
  }

  // 开局倒计时（服务端 start_at 统一，倒计时期间物理冻结）
  if (netOn.value && phase.value === 'run' && onlineStartLocal) {
    const leftMs = onlineStartLocal - Date.now()
    if (leftMs > 0) {
      g.fillStyle = 'rgba(8,10,18,.55)'
      g.fillRect(0, 0, PW, PH)
      g.textAlign = 'center'
      g.fillStyle = '#e8d8a8'
      g.font = 'bold 64px "Courier New", monospace'
      g.fillText(String(Math.ceil(leftMs / 1000)), PW / 2, PH / 2 - 40)
      g.fillStyle = 'rgba(238,241,246,.85)'
      g.font = '10px "Microsoft YaHei", sans-serif'
      g.fillText('准备起步', PW / 2, PH / 2 + 34)
    }
  }

  // 结算
  if (phase.value === 'win' || phase.value === 'lose') {
    g.fillStyle = 'rgba(8,10,18,.72)'
    g.fillRect(0, 0, PW, PH)
    const w = 230
    const h = 104
    const x0 = (PW - w) / 2
    const y0 = (PH - h) / 2
    panel(g, x0, y0, w, h, '#c7a96b')
    g.textAlign = 'center'
    g.fillStyle = phase.value === 'win' ? '#e8d8a8' : '#e5484d'
    g.font = 'bold 22px "Microsoft YaHei", sans-serif'
    g.fillText(phase.value === 'win' ? '冲过终点' : '翻车了', PW / 2, y0 + 14)
    g.fillStyle = '#eef1f6'
    g.font = '9px "Microsoft YaHei", sans-serif'
    const me = netOn.value ? room.value?.players?.find((pl) => pl.uid === room.value.my_uid) : null
    g.fillText(`本局 ${st.score} 分 · 行驶 ${meters(st.dist)} 米${me ? ` · 第 ${me.rank} 名` : ''}`, PW / 2, y0 + 52)
    g.fillStyle = 'rgba(226,232,240,.7)'
    g.font = '8px "Microsoft YaHei", sans-serif'
    g.fillText(netOn.value ? '点上方「回到房间」等房主再开一局' : '点上方「重开」再来一局 · 「换车 / 换赛道」改设置', PW / 2, y0 + 74)
  }
}

/** 在线排行榜：像素面板 */
function drawLeaderboard(ctx) {
  const r = room.value
  if (!r?.players?.length) return
  const rows = r.players.slice(0, RIVALS_MAX)
  const x = PW - 128
  const y = 60
  const w = 120
  const h = 16 + rows.length * 9
  panel(ctx, x, y, w, h, '#8a7a4a')
  ctx.textAlign = 'left'
  ctx.textBaseline = 'top'
  ctx.fillStyle = '#e8d8a8'
  ctx.font = '7px "Microsoft YaHei", sans-serif'
  ctx.fillText('在线排行榜', x + 6, y + 5)
  for (let i = 0; i < rows.length; i++) {
    const pl = rows[i]
    const yy = y + 16 + i * 9
    if (pl.uid === r.my_uid) {
      ctx.fillStyle = 'rgba(226,193,106,.18)'
      ctx.fillRect(x + 3, yy - 1, w - 6, 8)
    }
    ctx.fillStyle = pl.color
    ctx.fillRect(x + 6, yy + 1, 3, 3)
    ctx.fillStyle = pl.uid === r.my_uid ? '#e8d8a8' : 'rgba(226,232,240,.85)'
    ctx.font = '7px "Microsoft YaHei", sans-serif'
    ctx.fillText(`${i + 1}. ${pl.name}`.slice(0, 14), x + 12, yy)
    ctx.textAlign = 'right'
    ctx.fillStyle = 'rgba(226,232,240,.7)'
    ctx.fillText(pl.finished ? '完赛' : `${meters(pl.dist)}m`, x + w - 5, yy)
    ctx.textAlign = 'left'
  }
}

/* ---------- 主循环 ---------- */
let raf = 0
let last = 0
let acc = 0
function frame(ts) {
  if (!last) last = ts
  let dt = (ts - last) / 1000
  last = ts
  if (dt > 0.25) dt = 0.25
  acc += dt
  let guard = 0
  while (acc >= 1 / FPS && guard++ < 6) { flipClock++; step(); acc -= 1 / FPS }
  draw()
  raf = requestAnimationFrame(frame)
}

/* ---------- 键盘 ---------- */
const KEYMAP = {
  KeyA: 'left', ArrowLeft: 'left',
  KeyD: 'right', ArrowRight: 'right',
  KeyW: 'accel', ArrowUp: 'accel',
  KeyS: 'brake', ArrowDown: 'brake',
  Space: 'atkF', KeyJ: 'atkF',
  ShiftLeft: 'atkB', ShiftRight: 'atkB', KeyK: 'atkB',
}
function onDown(e) {
  const t = e.target
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  // 在线局不能单方面按 R 重开（会和房间里的成绩对不上），只允许单机重开
  if (e.key === 'r' || e.key === 'R') { if (phase.value !== 'idle' && !netOn.value) restart(); return }
  const k = KEYMAP[e.code]
  if (!k) return
  if (phase.value === 'run') e.preventDefault()
  keys[k] = true
}
function onUp(e) {
  const k = KEYMAP[e.code]
  if (k) keys[k] = false
}

onMounted(() => {
  reset()
  draw()
  window.addEventListener('keydown', onDown)
  window.addEventListener('keyup', onUp)
  raf = requestAnimationFrame(frame)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  stopPolling()
  rrSfx.stopEngine()
  beaconRoadrashLeave(room.value?.code)
  window.removeEventListener('keydown', onDown)
  window.removeEventListener('keyup', onUp)
})
</script>

<style scoped>
.rr-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.rr-bar { font-size: 13.5px; color: var(--dp-text2, #45505b); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center; }
.rr-bar b { color: var(--yq-accent, #c7a96b); }
.rr-tag { font-size: 12px; padding: 2px 8px; border-radius: 0;
  border: 1px solid var(--dp-line, rgba(0,0,0,.22)); background: rgba(127,127,127,.05); color: var(--dp-text2, #45505b); }
.rr-best { font-size: 12px; color: var(--dp-text3, #8a8f98); }
.rr-btn { padding: 4px 14px; border-radius: 0; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--color-bg-glass, rgba(127,127,127,.06));
  color: var(--dp-text2, #45505b); font-family: inherit; transition: all .18s; }
.rr-btn:hover { border-color: var(--yq-accent, #c7a96b); color: var(--yq-accent-deep, var(--yq-accent-bright, #c7a96b)); }
.rr-btn.primary { padding: 5px 18px; font-size: 12.5px; font-weight: 600;
  border-color: var(--yq-accent, #c7a96b); background: var(--yq-accent, #c7a96b); color: var(--yq-accent-fg, #fff);
  box-shadow: none; }
.rr-btn.primary:hover { filter: brightness(1.06); color: var(--yq-accent-fg, #fff); }
.rr-btn.tiny { padding: 3px 10px; font-size: 11.5px; }

.rr-cvt { position: relative; width: 100%; max-width: 1020px; }
.rr-cv { display: block; width: 100%; height: auto; aspect-ratio: 12 / 7;
  border-radius: 0; border: 2px solid #8a7a4a; image-rendering: pixelated; }

/* 赛前设置面板：四张赛道卡 + 四张车辆卡，窄屏两列，内容多时可滚 */
.rr-veil { position: absolute; inset: 0; border-radius: 0; display: flex; flex-direction: column;
  align-items: center; gap: 9px; text-align: center; padding: 18px 16px; overflow: auto;
  background: rgba(6,8,14,.82); color: #eef1f6; }
.rr-veil b { font-size: 17px; color: var(--yq-accent, #e2c16a); }
.rr-vsec { font-size: 11.5px; letter-spacing: .12em; color: rgba(238,241,246,.6); }
.rr-vgrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px;
  width: 100%; max-width: 560px; }
.rr-card { display: flex; flex-direction: column; gap: 3px; align-items: flex-start;
  padding: 8px 10px; border-radius: 0; cursor: pointer; font-family: inherit; text-align: left;
  border: 1px solid rgba(238,241,246,.18); background: rgba(255,255,255,.05); color: #eef1f6;
  transition: border-color .18s, background .18s; }
.rr-card:hover { border-color: rgba(226,193,106,.55); }
.rr-card.on { border-color: var(--yq-accent, #e2c16a); background: rgba(226,193,106,.16); }
.rr-card:disabled { opacity: .5; cursor: not-allowed; }
.rr-card:disabled:hover { border-color: rgba(238,241,246,.18); }
.rr-card-t { font-size: 13px; font-weight: 600; }
.rr-card-s { font-size: 10.5px; color: rgba(238,241,246,.62); }
.rr-stats { display: flex; flex-direction: column; gap: 2px; margin-top: 2px; }
.rr-stat { display: flex; align-items: center; gap: 3px; font-size: 10px; color: rgba(238,241,246,.6); }
.rr-stat em { font-style: normal; width: 24px; }
.rr-stat i { width: 8px; height: 5px; border-radius: 0; background: rgba(255,255,255,.16); }
.rr-stat i.on { background: var(--yq-accent, #e2c16a); }
.rr-tip { font-size: 11.5px; color: rgba(238,241,246,.7); }

/* 可配置项：对手人数 / 里程 / 玩法 */
.rr-nums { display: flex; gap: 12px; justify-content: center; width: 100%; max-width: 420px; }
.rr-num { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: rgba(238,241,246,.75); }
.rr-num input[type="number"] { width: 76px; padding: 6px 8px; border-radius: 0; font-family: inherit; font-size: 14px;
  text-align: center; color: #eef1f6; appearance: textfield;
  border: 1px solid rgba(238,241,246,.22); background: rgba(8,10,18,.5); outline: none; }
.rr-num input[type="number"]::-webkit-outer-spin-button,
.rr-num input[type="number"]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.rr-num input[type="number"]:focus { border-color: var(--yq-accent, #e2c16a); }
.rr-num input[type="number"]:disabled { opacity: .5; cursor: not-allowed; }
.rr-chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; width: 100%; max-width: 560px; }
.rr-chip { padding: 5px 12px; border-radius: 0; font-size: 12px; cursor: pointer; font-family: inherit;
  border: 1px solid rgba(238,241,246,.18); background: rgba(255,255,255,.05); color: #eef1f6;
  transition: border-color .18s, background .18s; }
.rr-chip:hover { border-color: rgba(226,193,106,.55); }
.rr-chip.on { border-color: var(--yq-accent, #e2c16a); background: rgba(226,193,106,.16); color: #f4e6bd; }
.rr-chip:disabled { opacity: .5; cursor: not-allowed; }

/* 在线房间面板 */
.rr-net { width: 100%; max-width: 560px; display: flex; flex-direction: column; align-items: center; gap: 7px;
  padding: 10px 12px; border-radius: 0;
  border: 1px solid rgba(226,193,106,.25); background: rgba(255,255,255,.045); }
.rr-netrow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center; }
.rr-code { width: 108px; padding: 6px 10px; border-radius: 0; font-family: inherit; font-size: 13px;
  text-align: center; letter-spacing: .16em; color: #eef1f6;
  border: 1px solid rgba(238,241,246,.22); background: rgba(8,10,18,.5); outline: none; }
.rr-code:focus { border-color: var(--yq-accent, #e2c16a); }
.rr-roomcode { font-size: 12.5px; color: rgba(238,241,246,.75); }
.rr-roomcode b { font-size: 16px; color: var(--yq-accent, #e2c16a); letter-spacing: .14em; }
.rr-players { display: flex; flex-wrap: wrap; gap: 6px 12px; justify-content: center; }
.rr-player { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: rgba(238,241,246,.9); }
.rr-player i { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.rr-player em { font-style: normal; font-size: 10.5px; color: rgba(238,241,246,.55); }
.rr-neterr { font-size: 11.5px; color: #ff8f7f; }
.rr-nettip { font-size: 11px; color: rgba(238,241,246,.6); }

.rr-pad { display: grid; grid-template-columns: repeat(4, minmax(58px, 1fr)); gap: 8px; width: 100%; max-width: 460px; }
.rr-pk { padding: 12px 8px; border-radius: 0; font-size: 13px; font-family: inherit; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--color-bg-glass, rgba(127,127,127,.06));
  color: var(--dp-text2, #45505b); touch-action: none; user-select: none; }
.rr-pk:active { border-color: var(--yq-accent, #c7a96b); color: var(--yq-accent-deep, #c7a96b); }
.rr-pk.wide { grid-column: span 2; }
.rr-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
