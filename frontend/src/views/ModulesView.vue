<template>
  <!-- 手机端：一级模块分组 + 二级模块横向滑动条 -->
  <section v-if="isMobile" class="mdl" aria-label="全部模块">
    <header class="mdl-head">
      <h1 class="mdl-title">全部模块</h1>
      <p class="mdl-sub">{{ total }} 个模块 · 按账号角色展示</p>
    </header>

    <section v-for="g in groups" :key="g.label || '__home__'" class="mdl-group">
      <div class="mdl-group__head">
        <h2 class="mdl-group__name">{{ g.label || '总览' }}</h2>
        <span class="mdl-group__n">{{ g.items.length }} 项</span>
      </div>

      <div ref="strips" class="mdl-stripwrap">
        <div class="mdl-strip" @scroll="onStripScroll">
          <template v-for="it in g.items" :key="it.path">
            <a
              v-if="it.external"
              :href="it.path"
              class="mdl-card"
              @click="buzz"
            >
              <span class="mdl-card__ico" aria-hidden="true"><component :is="it.icon" /></span>
              <span class="mdl-card__lab">{{ it.title }}</span>
            </a>
            <RouterLink
              v-else
              :to="it.path"
              class="mdl-card"
              :class="{ active: isActive(it.path) }"
              :aria-current="isActive(it.path) ? 'page' : undefined"
              @click="buzz"
            >
              <span class="mdl-card__ico" aria-hidden="true"><component :is="it.icon" /></span>
              <span class="mdl-card__lab">{{ it.title }}</span>
            </RouterLink>
          </template>
        </div>
        <!-- 右缘渐隐：提示「向右还有」。滑到末尾时由 .at-end 自动隐去 -->
        <span class="mdl-strip__fade" aria-hidden="true"></span>
      </div>
    </section>
  </section>

  <!-- 桌面端兜底（直接访问 /modules 时）：分组卡片网格 -->
  <div v-else class="mdld">
    <header class="mdld-head">
      <h1 class="mdld-title">全部模块</h1>
      <p class="mdld-sub">{{ total }} 个模块 · 按账号角色展示</p>
    </header>
    <section v-for="g in groups" :key="g.label || '__home__'" class="mdld-group">
      <h2 class="mdld-group__name">{{ g.label || '总览' }}</h2>
      <div class="mdld-grid">
        <template v-for="it in g.items" :key="it.path">
          <a v-if="it.external" :href="it.path" class="mdld-card">
            <span class="mdld-card__ico" aria-hidden="true"><component :is="it.icon" /></span>
            <span class="mdld-card__lab">{{ it.title }}</span>
          </a>
          <RouterLink v-else :to="it.path" class="mdld-card" :class="{ active: isActive(it.path) }">
            <span class="mdld-card__ico" aria-hidden="true"><component :is="it.icon" /></span>
            <span class="mdld-card__lab">{{ it.title }}</span>
          </RouterLink>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
defineOptions({ name: 'ModulesView' })
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useIsMobile } from '@/composables/useIsMobile'
import { buildNavModules, countNavItems, isNavItemActive } from '@/constants/navModules'

const route = useRoute()
const auth = useAuthStore()
const { isMobile } = useIsMobile()

const isSuper = computed(() => auth.user?.role === 'super_admin' || auth.user?.is_super_admin === 1)
const groups = computed(() => buildNavModules(isSuper.value))
const total = computed(() => countNavItems(groups.value))

const isActive = (path) => isNavItemActive(path, route.path)

const strips = ref([])

/** 滑到末尾就隐去右缘渐隐，避免「还有内容」的错觉 */
function syncStrip(el) {
  const s = el.querySelector?.('.mdl-strip')
  if (!s) return
  const atEnd = s.scrollLeft + s.clientWidth >= s.scrollWidth - 4
  s.classList.toggle('at-end', atEnd)
}

function onStripScroll(e) {
  syncStrip(e.currentTarget.parentElement)
}

function buzz() {
  try { if (navigator && navigator.vibrate) navigator.vibrate(6) } catch { /* noop */ }
}

onMounted(async () => {
  await nextTick()
  strips.value.forEach(syncStrip)
})
</script>

<style scoped>
/* ============ 手机端 ============ */
.mdl {
  min-height: 100svh;
  padding: calc(env(safe-area-inset-top, 0px) + 18px) 0 calc(88px + env(safe-area-inset-bottom, 0px));
  background: var(--m-bg, #0b1016);
  color: var(--m-text, #f0f5f8);
}

.mdl-head { padding: 0 16px 4px; }
.mdl-title {
  margin: 0;
  font-size: 26px;
  font-weight: 780;
  letter-spacing: -.035em;
  color: var(--m-text, #f0f5f8);
}
.mdl-sub {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: var(--m-text-3, #71808c);
}

.mdl-group { margin-top: 26px; }
.mdl-group__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 0 16px 10px;
}
.mdl-group__name {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -.01em;
  color: var(--m-text, #f0f5f8);
}
.mdl-group__n {
  font-size: 11.5px;
  color: var(--m-text-3, #71808c);
  font-variant-numeric: tabular-nums;
}

.mdl-stripwrap { position: relative; }
.mdl-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
  padding: 2px 16px 6px;
  scrollbar-width: none;
}
.mdl-strip::-webkit-scrollbar { display: none; }

/* 右缘渐隐：贴住条带右端，滑到末尾（.at-end）自动淡出 */
.mdl-strip__fade {
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 30px;
  pointer-events: none;
  background: linear-gradient(90deg, transparent, var(--m-bg, #0b1016));
  transition: opacity .22s ease;
}
.mdl-strip.at-end + .mdl-strip__fade { opacity: 0; }

.mdl-card {
  flex: 0 0 auto;
  width: 84px;
  min-height: 82px;
  scroll-snap-align: start;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 4px;
  border: 1px solid var(--m-line, rgba(220, 235, 246, .10));
  border-radius: 14px;
  background: var(--m-surface, #141c26);
  color: inherit;
  text-decoration: none;
  transition: transform .16s ease, border-color .18s ease;
  -webkit-tap-highlight-color: transparent;
}
.mdl-card:active { transform: scale(.95); }
.mdl-card__ico {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 23px;
  line-height: 1;
  color: var(--m-text-2, #a9b7c2);
}
.mdl-card__lab {
  font-size: 11.5px;
  line-height: 1.25;
  text-align: center;
  color: var(--m-text-2, #a9b7c2);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mdl-card.active {
  border-color: var(--m-accent, #62e6d1);
  background: var(--m-surface-2, #18222d);
}
.mdl-card.active .mdl-card__ico { color: var(--m-accent, #62e6d1); }
.mdl-card.active .mdl-card__lab { color: var(--m-text, #f0f5f8); font-weight: 600; }

@media (prefers-reduced-motion: reduce) {
  .mdl-card, .mdl-strip__fade { transition: none; }
}

/* ============ 桌面端兜底 ============ */
.mdld {
  min-height: 100vh;
  padding: 96px 40px 60px;
  background: var(--dp-bg);
  color: var(--dp-text);
}
.mdld-head { max-width: 1000px; margin: 0 auto 8px; }
.mdld-title { margin: 0; font-size: 26px; font-weight: 700; color: var(--dp-text); }
.mdld-sub { margin: 6px 0 0; font-size: 13px; color: var(--dp-text3); }
.mdld-group { max-width: 1000px; margin: 28px auto 0; }
.mdld-group__name {
  margin: 0 0 12px;
  font-size: 12px;
  letter-spacing: .14em;
  text-transform: uppercase;
  font-weight: 500;
  color: var(--dp-text3);
}
.mdld-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.mdld-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid var(--dp-line);
  border-radius: 12px;
  background: var(--dp-surface);
  color: var(--dp-text2);
  text-decoration: none;
  font-size: 13.5px;
  transition: border-color .16s, color .16s, background .16s;
}
.mdld-card:hover { border-color: var(--dp-accent); color: var(--dp-text); }
.mdld-card__ico { display: flex; font-size: 18px; line-height: 1; color: var(--dp-text3); }
.mdld-card.active { border-color: var(--dp-accent); color: var(--dp-accent); background: var(--dp-accent-faint); }
.mdld-card.active .mdld-card__ico { color: var(--dp-accent); }
.mdld-card__lab { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
