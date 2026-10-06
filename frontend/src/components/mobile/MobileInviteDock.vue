<template>
  <!-- 移动端没有桌面顶栏，对局邀请需要一个独立入口（v2.45）。
       只在有待处理邀请时出现 —— 无邀请时整块不渲染，对现有布局零影响。
       位置贴右上（主页头部左侧是品牌 Logo，右侧留白），点击展开玻璃卡片列表。 -->
  <div v-if="pendingCount" class="mid">
    <div v-if="open" class="mid-mask" @click="open = false"></div>

    <button
      class="mid-pill"
      :class="{ open }"
      :aria-expanded="open"
      aria-label="对局邀请"
      @click="open = !open"
    >
      <span class="mid-pill__ico" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 9.5h10a3.5 3.5 0 0 1 3.4 4.3l-.8 4a3 3 0 0 1-5.2 1.3l-.6-.8a1 1 0 0 0-1.6 0l-.6.8a3 3 0 0 1-5.2-1.3l-.8-4A3.5 3.5 0 0 1 7 9.5Z"/>
          <path d="M9 12.5v2M8 13.5h2M15.2 13h.01M16.8 14.6h.01"/>
        </svg>
      </span>
      <span class="mid-pill__lab">对局邀请</span>
      <span class="mid-pill__n">{{ pendingCount > 99 ? '99+' : pendingCount }}</span>
    </button>

    <transition name="mid-pop">
      <div v-if="open" class="mid-card" role="dialog" aria-label="对局邀请列表">
        <div class="mid-card__head">待处理邀请</div>
        <div v-for="inv in invites" :key="inv.key" class="mid-row">
          <div class="mid-row__main">
            <span class="mid-tag" :class="inv.kind">{{ inv.kind === 'chess' ? '棋局' : '牌桌' }}</span>
            <span class="mid-row__txt">
              <b>{{ inv.fromName }}</b> 邀你来一局 {{ inv.gameName }}
            </span>
          </div>
          <div class="mid-row__foot">
            <span class="mid-row__meta">{{ agoLabel(inv.createdAt) }}</span>
            <span class="mid-row__acts">
              <button class="mid-btn accept" :disabled="busy.has(inv.key)" @click="onAccept(inv)">接受</button>
              <button class="mid-btn decline" :disabled="busy.has(inv.key)" @click="onDecline(inv)">拒绝</button>
            </span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useGameInvites, agoLabel } from '@/composables/useGameInvites'

const router = useRouter()
const { invites, pendingCount, accept, decline } = useGameInvites()

const open = ref(false)
const busy = ref(new Set())
// 邀请被处理完 / 对方撤回后，卡片自动收起，避免留一个空壳
watch(pendingCount, (n) => { if (!n) open.value = false })

function setBusy(key, on) {
  const s = new Set(busy.value)
  if (on) s.add(key); else s.delete(key)
  busy.value = s
}

function buzz() {
  try { if (navigator && navigator.vibrate) navigator.vibrate(8) } catch { /* noop */ }
}

async function onAccept(inv) {
  if (busy.value.has(inv.key)) return
  buzz()
  setBusy(inv.key, true)
  try {
    await accept(inv)
    open.value = false
    router.push(inv.route)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.msg || '接受失败，请稍后再试')
  } finally {
    setBusy(inv.key, false)
  }
}

async function onDecline(inv) {
  if (busy.value.has(inv.key)) return
  buzz()
  setBusy(inv.key, true)
  try {
    await decline(inv)
  } catch (e) {
    ElMessage.warning(e?.response?.data?.msg || '操作失败，请稍后再试')
  } finally {
    setBusy(inv.key, false)
  }
}
</script>

<style scoped>
.mid {
  position: fixed;
  top: calc(10px + var(--safe-top, env(safe-area-inset-top, 0px)));
  right: 12px;
  z-index: 1600;
}

.mid-mask {
  position: fixed;
  inset: 0;
  z-index: -1;
}

.mid-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px 7px 10px;
  border-radius: 999px;
  border: 1px solid var(--lj-line, rgba(15, 40, 70, .14));
  background: var(--lj-glass, rgba(22, 30, 39, .62));
  -webkit-backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  box-shadow: 0 6px 20px rgba(0, 0, 0, .22);
  color: var(--lj-text, #e8eaee);
  font-family: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: transform .15s ease, border-color .2s ease;
}
.mid-pill:active { transform: scale(.96); }
.mid-pill.open { border-color: var(--lj-dai, #5b6ae0); }
.mid-pill__ico { width: 16px; height: 16px; display: inline-flex; color: var(--lj-dai, #5b6ae0); }
.mid-pill__ico svg { width: 100%; height: 100%; }
.mid-pill__lab { font-size: 12px; letter-spacing: .02em; }
.mid-pill__n {
  min-width: 17px; height: 17px; padding: 0 5px;
  border-radius: 999px;
  background: #D8504F; color: #fff;
  font-size: 10.5px; font-weight: 600; line-height: 17px; text-align: center;
  font-variant-numeric: tabular-nums;
}

.mid-card {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: min(78vw, 300px);
  max-height: 56vh;
  overflow-y: auto;
  padding: 10px 12px 12px;
  border-radius: 14px;
  border: 1px solid var(--lj-line, rgba(15, 40, 70, .14));
  background: var(--lj-glass, rgba(22, 30, 39, .82));
  -webkit-backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  backdrop-filter: var(--lj-glass-blur, saturate(180%) blur(20px));
  box-shadow: 0 14px 40px rgba(0, 0, 0, .34);
  color: var(--lj-text, #e8eaee);
}
.mid-card__head {
  font-size: 11.5px; font-weight: 600;
  color: var(--lj-text-3, #8a8f98);
  padding-bottom: 8px; margin-bottom: 6px;
  border-bottom: 1px solid var(--lj-line, rgba(15, 40, 70, .14));
}
.mid-row { padding: 8px 0; border-bottom: 1px dashed var(--lj-line, rgba(15, 40, 70, .14)); }
.mid-row:last-child { border-bottom: none; padding-bottom: 2px; }
.mid-row__main { display: flex; align-items: center; gap: 7px; }
.mid-tag {
  flex: none;
  padding: 2px 7px; border-radius: 999px;
  font-size: 10.5px; font-weight: 600;
}
.mid-tag.chess { background: rgba(127, 168, 163, .18); color: #7fa8a3; }
.mid-tag.table { background: rgba(199, 169, 107, .18); color: #c7a96b; }
.mid-row__txt {
  min-width: 0; font-size: 12.5px; line-height: 1.45;
  color: var(--lj-text, #e8eaee);
}
.mid-row__txt b { font-weight: 600; }
.mid-row__foot {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 7px;
}
.mid-row__meta { font-size: 11px; color: var(--lj-text-3, #8a8f98); }
.mid-row__acts { display: inline-flex; gap: 8px; }
.mid-btn {
  border-radius: 999px; border: 1px solid transparent;
  padding: 4px 14px; font-size: 12px; font-family: inherit;
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: all .18s ease;
}
.mid-btn:active:not(:disabled) { transform: scale(.95); }
.mid-btn.accept { background: rgba(63, 150, 142, .18); color: #3F968E; border-color: rgba(63, 150, 142, .4); }
.mid-btn.decline { background: transparent; color: var(--lj-text-3, #8a8f98); border-color: var(--lj-line, rgba(15, 40, 70, .14)); }
.mid-btn:disabled { opacity: .5; }

.mid-pop-enter-active, .mid-pop-leave-active { transition: opacity .18s ease, transform .18s ease; }
.mid-pop-enter-from, .mid-pop-leave-to { opacity: 0; transform: translateY(-6px) scale(.98); }

@media (prefers-reduced-motion: reduce) {
  .mid-pop-enter-active, .mid-pop-leave-active { transition-duration: .01s; }
  .mid-pill:active { transform: none; }
}
</style>
