<template>
  <!-- 桌面端顶栏已「去条化」：不再有整条背景/分隔线
       玄黄品牌 + 全局搜索已迁入侧栏；AI 对话改为每页悬浮按钮
       这里只保留右上角的悬浮按钮组（背景音乐 / 下载 App / 账号） -->
  <div class="lj-topbar" ref="topbarRef">
    <!-- 右侧：音频 + 下载 + 用户区 -->
    <div class="tb-right">
      <!-- 音频控制（内联面板，不弹窗） -->
      <el-dropdown trigger="click" placement="bottom-end" :show-arrow="false">
        <button class="tb-icon-btn" :title="player.isPlaying ? '背景音乐（播放中）' : '背景音乐'">
          <el-icon><Headset /></el-icon>
          <span class="tb-audio-dot" :class="{ off: !player.isPlaying }"></span>
        </button>
        <template #dropdown>
          <div class="tb-audio-panel" @click.stop>
            <div class="tb-panel-title">音频面板</div>

            <!-- 背景音乐总开关（滑动开关，状态持久化） -->
            <div class="tb-audio-row">
              <span class="tb-audio-label">背景音乐</span>
              <button
                type="button"
                class="tb-switch"
                role="switch"
                :aria-checked="player.bgmEnabled ? 'true' : 'false'"
                :class="{ on: player.bgmEnabled }"
                :title="player.bgmEnabled ? '点击关闭背景音乐' : '点击开启背景音乐'"
                @click="player.toggleBgm()"
              >
                <span class="tb-switch-thumb"></span>
              </button>
              <span class="tb-switch-hint" :class="{ off: !player.bgmEnabled }">
                {{ player.bgmEnabled ? '开启' : '关闭' }}
              </span>
            </div>

            <!-- 背景音乐选择 -->
            <div class="tb-audio-seg" :class="{ 'is-muted': !player.bgmEnabled }">
              <div class="tb-seg-head" @click="bgmListOpen = !bgmListOpen">
                <span class="tb-audio-label">背景音乐</span>
                <span class="tb-bgm-cur">{{ curBgmName }}</span>
                <el-icon class="tb-seg-arrow" :class="{ open: bgmListOpen }"><CaretBottom /></el-icon>
              </div>
              <transition name="fade-drop">
                <div v-if="bgmListOpen" class="tb-bgm-list">
                  <div
                    v-for="it in bgm.musicLibrary"
                    :key="it.id"
                    class="tb-bgm-item"
                    :class="{ active: String(it.id) === String(bgm.bgmChoiceId) }"
                    @click="chooseBgm(it)"
                  >
                    <span class="tb-bgm-name">{{ it.title }}</span>
                    <el-icon v-if="String(it.id) === String(bgm.bgmChoiceId)" class="tb-bgm-check"><Check /></el-icon>
                  </div>
                  <div v-if="!bgm.musicLibrary.length" class="tb-bgm-empty">音乐库为空</div>
                </div>
              </transition>
            </div>

            <!-- 音量 -->
            <div class="tb-audio-row tb-audio-vol" :class="{ 'is-muted': !player.bgmEnabled }">
              <span class="tb-audio-label">音量</span>
              <div class="tb-knob" @mousedown.prevent="startVolDrag($event)">
                <div class="tb-knob-fill" :style="{ width: player.volume * 100 + '%' }"></div>
                <span class="tb-knob-thumb" :style="{ left: player.volume * 100 + '%' }"></span>
              </div>
            </div>
          </div>
        </template>
      </el-dropdown>

      <!-- 下载 App 入口：新窗口打开 /download/（多平台下载页，含鸿蒙/苹果预留位） -->
      <a
        class="tb-icon-btn"
        href="/download/"
        target="_blank"
        rel="noopener"
        title="下载手机软件"
      >
        <el-icon><Cellphone /></el-icon>
      </a>

      <!-- 用户区 -->
      <el-dropdown trigger="click" @command="onCommand">
        <div class="tb-user">
          <span class="tb-user-name">{{ userName }}</span>
          <el-icon class="tb-caret"><CaretBottom /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人中心</el-dropdown-item>
            <!-- 管理后台入口已迁移到侧栏「管理」分组（含用户 / 角色 / 菜单三个二级模块），顶栏不再单独入口 -->
            <el-dropdown-item command="logout" divided><el-icon><SwitchButton /></el-icon>退出账号</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  User, SwitchButton, Headset, CaretBottom, Check, Cellphone
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import { useBgmLibraryStore } from '@/stores/bgmLibrary'

const router = useRouter()
const auth = useAuthStore()
const player = usePlayerStore()
const bgm = useBgmLibraryStore()

const topbarRef = ref(null)

/* ---- 用户区 ---- */
const userName = computed(() => auth.user?.nickname || auth.user?.name || auth.user?.email || '道友')

/* ---- 音频控制（接 player store）---- */
const bgmListOpen = ref(false)

const curBgmName = computed(() => {
  const id = bgm.bgmChoiceId
  const it = bgm.musicLibrary.find(x => String(x.id) === String(id))
  return it ? it.title : '默认古筝'
})

function chooseBgm(item) {
  // 选曲即视为「想听」：总开关若处于关闭态先打开，避免出现「选了却没反应」
  if (!player.bgmEnabled) player.setBgmEnabled(true)
  bgm.setBackground(item, true)
  bgmListOpen.value = false
}

function startVolDrag(e) {
  const track = e.currentTarget
  const apply = (ev) => {
    const r = track.getBoundingClientRect()
    player.setVolume(Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)))
  }
  apply(e)
  const move = (ev) => apply(ev)
  const up = () => {
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
}

/* ---- 下拉命令 ---- */
function onCommand(cmd) {
  switch (cmd) {
    case 'profile': router.push('/profile'); break
    case 'logout':
      auth.logoutAction()
      router.push('/login')
      break
  }
}

onMounted(async () => {
  await bgm.initBgm()
})

onUnmounted(() => {})
</script>

<style scoped>
/* 顶栏已「去条化」：不再是一条通栏，只有右上角悬浮按钮组
   —— 品牌与搜索已迁入侧栏，AI 入口改为每页悬浮按钮 */
.lj-topbar {
  position: fixed;
  top: 12px;
  right: 16px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  background: transparent;
  border: none;
  box-shadow: none;
  box-sizing: border-box;
}
@media (max-width: 767px) {
  .lj-topbar { top: calc(10px + var(--safe-top)); right: 10px; }
}

.tb-brand { display: flex; align-items: center; gap: 8px; cursor: pointer; flex: none; color: var(--lj-dai); transition: all 0.25s; }
.tb-brand:hover { color: var(--lj-seal); }
.tb-brand:hover .tb-logo { filter: drop-shadow(0 0 5px rgba(217, 138, 118, 0.4)); }
.tb-logo { width: 26px; height: 26px; }
.tb-brand-text {
  font-family: var(--font-serif);
  font-size: 18px; font-weight: 600; letter-spacing: 0.3em;
  color: var(--lj-text);
}

/* AI 对话常驻入口（桌面与移动端均显示）——朱砂胶囊 */
.tb-ai-entry {
  position: relative;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 999px;
  font-size: 13px; color: var(--lj-text-2); cursor: pointer; white-space: nowrap;
  transition: all 0.25s;
  flex: none;
  border: 1px solid transparent;
}
/* 未激活：hover 淡朱砂底 + 朱砂字 + 极淡外辉（克制，不铺满不喧宾） */
.tb-ai-entry:not(.active):hover {
  color: var(--lj-seal);
  background: var(--lj-seal-soft);
  box-shadow: 0 0 0 1px var(--lj-seal) inset, 0 0 14px rgba(217, 138, 118, 0.16);
}
/* 激活（当前在 /assistant）：实填充朱砂渐变胶囊，柔和投影 */
.tb-ai-entry.active {
  color: #fff;
  background: linear-gradient(135deg, var(--lj-seal), var(--lj-seal-hover));
  border-color: transparent;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(217, 138, 118, 0.32), inset 0 1px 0 rgba(255, 255, 255, 0.25);
}
.tb-ai-icon { font-size: 15px; }

.tb-search { position: relative; flex: 1; max-width: 460px; }
.tb-search-input :deep(.el-input__wrapper) {
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015)), rgba(18, 26, 34, 0.5);
  border-radius: 999px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 0 0 1px var(--lj-line) inset;
  padding-left: 14px;
}
.tb-search-input :deep(.el-input__placeholder),
.tb-search-input :deep(::placeholder) { color: var(--lj-text-3); }
.tb-search-input :deep(.el-input__wrapper:hover):not(.is-focus) {
  background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02)), rgba(20, 28, 36, 0.55);
}
.tb-search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--lj-seal) inset, 0 0 0 3px var(--lj-seal-soft);
}

/* 联想面板 */
.tb-suggest {
  position: absolute; top: calc(100% + 8px); left: 0; right: 0;
  background: var(--lj-paper);
  border: 1px solid var(--lj-line);
  border-radius: 12px;
  box-shadow: var(--lj-shadow);
  overflow: hidden;
  z-index: 100;
}
.suggest-group { padding: 6px 0; }
.suggest-group + .suggest-group { border-top: 1px solid var(--lj-line); }
.suggest-head { padding: 4px 16px; font-size: 11px; color: var(--lj-text-3); letter-spacing: 0.15em; }
.suggest-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 16px;
  font-size: 13px; color: var(--lj-text-2); cursor: pointer;
}
.suggest-item:hover { background: rgba(74, 95, 99, 0.06); color: var(--lj-seal); }
.suggest-icon { font-size: 14px; }
.suggest-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.suggest-empty { padding: 14px 16px; font-size: 13px; color: var(--lj-text-3); }

/* 模块快捷入口 */
.suggest-modules { padding: 6px 0 8px; border-top: 1px solid var(--lj-line); }
.suggest-mod-row { display: flex; flex-wrap: wrap; gap: 6px; padding: 2px 16px; }
/* 二级分组：与普通入口同排布局，仅多一行小标题作为层级提示 */
.suggest-mod-group { margin-top: 6px; }
.suggest-mod-group + .suggest-mod-group { margin-top: 8px; }
.suggest-subhead {
  display: flex; align-items: center; gap: 5px;
  padding: 2px 16px 4px; font-size: 11px; letter-spacing: 0.12em; color: var(--lj-text-3);
}
.suggest-mod {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 10px; border: 1px solid var(--lj-line); border-radius: 8px;
  font-size: 12px; color: var(--lj-text-2); cursor: pointer;
  background: rgba(127, 168, 163, 0.06); transition: all 0.2s;
}
.suggest-mod.active { color: var(--lj-seal); border-color: var(--lj-seal); background: var(--lj-seal-soft); }
.suggest-mod:hover { color: var(--lj-seal); border-color: var(--lj-seal); background: var(--lj-seal-soft); }

.fade-drop-enter-active, .fade-drop-leave-active { transition: all 0.18s ease; }
.fade-drop-enter-from, .fade-drop-leave-to { opacity: 0; transform: translateY(-4px); }

.tb-right { display: flex; align-items: center; gap: 8px; margin-left: auto; flex: none; }

.tb-icon-btn {
  position: relative;
  width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 10px;
  background: transparent;
  color: var(--dp-text2, var(--lj-text-2)); font-size: 17px; cursor: pointer; transition: all 0.18s;
}
.tb-icon-btn:hover {
  color: var(--dp-accent, var(--lj-dai));
  background: var(--dp-accent-faint, rgba(127, 168, 163, 0.12));
}
.tb-audio-dot {
  position: absolute; top: 5px; right: 5px; width: 6px; height: 6px; border-radius: 50%;
  background: rgba(217, 138, 118, 0.75);
}
.tb-audio-dot.off { background: var(--lj-vermilion); }

@media (max-width: 767px) {
  /* 触控目标 ≥44px（WCAG）：移动端顶栏图标按钮加大命中区，顶栏高度仍容纳得下 */
  .tb-icon-btn { width: 40px; height: 44px; }
}
/* 音频面板 */
.tb-audio-panel { width: 240px; padding: 14px 16px; }
.tb-panel-title { font-size: 13px; color: var(--lj-text); font-weight: 600; margin-bottom: 12px; letter-spacing: 0.05em; }
.tb-audio-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.tb-audio-label { font-size: 12px; color: var(--lj-text-2); width: 60px; flex: none; }

/* 背景音乐总开关：滑动开关（.tb-switch）——关闭即彻底停播并记忆状态 */
.tb-switch {
  position: relative; flex: none; padding: 0;
  width: 42px; height: 22px; border-radius: 999px; cursor: pointer;
  border: 1px solid var(--lj-line-strong);
  background: rgba(74, 95, 99, 0.16);
  transition: background 0.28s ease, border-color 0.28s ease, box-shadow 0.28s ease;
}
.tb-switch:hover { border-color: var(--lj-dai); }
.tb-switch-thumb {
  position: absolute; top: 50%; left: 3px;
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--lj-text-3); transform: translateY(-50%);
  transition: left 0.28s cubic-bezier(0.34, 1.3, 0.64, 1), background 0.28s ease;
}
.tb-switch.on {
  background: var(--lj-seal-soft);
  border-color: var(--lj-seal);
  box-shadow: 0 0 0 1px var(--lj-seal-soft), 0 0 12px rgba(217, 138, 118, 0.18);
}
.tb-switch.on .tb-switch-thumb {
  left: 21px; background: var(--yq-rain-bright);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}
.tb-switch:focus-visible { outline: var(--focus-outline); outline-offset: var(--focus-outline-offset); }
.tb-switch-hint { font-size: 12px; color: var(--lj-dai); flex: none; }
.tb-switch-hint.off { color: var(--lj-text-3); }

/* 总开关关闭时：曲目选择与音量区降权，暗示当前不生效 */
.tb-audio-seg.is-muted, .tb-audio-vol.is-muted { opacity: 0.5; }

.tb-knob {
  flex: 1; height: 5px; border-radius: 999px; background: rgba(74, 95, 99, 0.15);
  position: relative; cursor: pointer;
}
.tb-knob-fill { position: absolute; inset: 0; right: auto; border-radius: 999px; background: var(--lj-dai); }
.tb-knob-thumb {
  position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%;
  background: var(--yq-rain-bright); border: 2px solid var(--lj-dai);
  transform: translate(-50%, -50%);
}

/* 背景音乐选择折叠区 */
.tb-audio-seg { margin-bottom: 10px; }
.tb-seg-head {
  display: flex; align-items: center; gap: 6px; cursor: pointer;
  padding: 6px 4px; border-radius: 8px;
}
.tb-seg-head:hover { background: rgba(74, 95, 99, 0.06); }
.tb-bgm-cur {
  flex: 1; text-align: right; font-size: 12px; color: var(--lj-dai);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 100px;
}
.tb-seg-arrow { font-size: 12px; color: var(--lj-text-2); transition: transform 0.2s; }
.tb-seg-arrow.open { transform: rotate(180deg); }
.tb-bgm-list {
  max-height: 200px; overflow-y: auto; margin-top: 4px;
  border-top: 1px solid var(--lj-line); padding: 6px 0;
}
.tb-bgm-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 8px; border-radius: 8px; cursor: pointer;
}
.tb-bgm-item:hover { background: rgba(74, 95, 99, 0.06); }
.tb-bgm-item.active { background: rgba(112, 150, 170, 0.14); }
.tb-bgm-name {
  flex: 1; font-size: 13px; color: var(--lj-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tb-bgm-item.active .tb-bgm-name { color: var(--lj-seal-hover); font-weight: 600; }
.tb-bgm-check { font-size: 14px; color: var(--lj-dai); }
.tb-bgm-empty { padding: 10px 8px; color: var(--lj-text-2); font-size: 12px; text-align: center; }

.tb-user { display: flex; align-items: center; gap: 4px; cursor: pointer; padding: 6px 10px; border-radius: 10px; background: transparent; transition: all 0.18s; }
.tb-user:hover { background: var(--dp-accent-faint, rgba(127, 168, 163, 0.12)); }
.tb-user:hover .tb-user-name { color: var(--dp-accent, var(--lj-dai)); }
.tb-user-name { font-size: 13px; color: var(--dp-text, var(--lj-text)); }
.tb-caret { font-size: 12px; color: var(--dp-text3, var(--lj-text-2)); }

/* 收起态悬浮按钮 */
.tb-mini {
  position: fixed; top: 8px; right: 22px; z-index: 999;
  width: 40px; height: 40px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--lj-line); border-radius: 12px; background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  color: var(--lj-dai); font-size: 18px; cursor: pointer;
  box-shadow: var(--lj-shadow);
}
.tb-mini:hover { color: var(--lj-seal); border-color: var(--lj-seal); box-shadow: 0 0 0 1px rgba(217, 138, 118, 0.5), var(--lj-shadow); }

.tb-search-toggle { display: none; }

@media (max-width: 767px) {
  .tb-search { display: none; }
  .tb-search.is-mobile { display: block; max-width: none; flex: 1; }
  .tb-search-toggle { display: inline-flex; }
  .tb-user-name { display: none; }
}
</style>
