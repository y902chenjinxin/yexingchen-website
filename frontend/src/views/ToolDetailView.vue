<template>
  <IslandInnerBase type="tool" :title="tool ? (tool.title || '工具') : '工具'" subtitle="妙用无穷">
    <div class="tool-detail">
      <template v-if="tool">
        <div class="detail-head">
          <div class="detail-icon">{{ tool.icon || '🔧' }}</div>
          <div class="detail-info">
            <span class="detail-name">{{ tool.title || '无名工具' }}</span>
            <span class="detail-desc">{{ tool.description || '暂无描述' }}</span>
          </div>
        </div>

        <div class="detail-actions">
          <el-button type="primary" @click="loaded = !loaded">
            {{ loaded ? '隐藏工具' : '加载工具' }}
          </el-button>
          <a v-if="tool.url" :href="tool.url" target="_blank" rel="noopener noreferrer" class="open-link">在新标签打开</a>
        </div>

        <div v-if="loaded" class="detail-frame-wrap">
          <iframe :src="tool.url" class="detail-frame" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads" />
        </div>
      </template>

      <div v-else class="not-found">
        <span class="nf-icon">🔧</span>
        <span class="nf-text">工具不存在或不开放</span>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { useToolStore } from '@/stores/tool'

const route = useRoute()
const toolStore = useToolStore()

const loaded = ref(false)

const tool = computed(() =>
  toolStore.list.find((t) => String(t.id) === String(route.params.id))
)

onMounted(() => { toolStore.fetchList() })
</script>

<style scoped>
.tool-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-head {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px 24px;
  background: linear-gradient(165deg, rgba(255,255,255,.03), rgba(255,255,255,0) 55%), var(--ls-glass);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
  backdrop-filter: saturate(150%) blur(10px);
}

.detail-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #a5825a 0%, rgba(196, 154, 108, 0.3) 100%);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-name {
  font-family: var(--font-serif);
  color: var(--ls-text);
  font-size: 18px;
}

.detail-desc {
  color: var(--ls-text-2);
  font-size: 13px;
}

.detail-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.open-link {
  color: var(--ls-dai);
  font-size: 13px;
  text-decoration: none;
  border: 1px solid var(--ls-line-strong);
  border-radius: var(--radius-sm);
  padding: 7px 14px;
  transition: all var(--transition);
}

.open-link:hover {
  border-color: var(--ls-dai);
  color: var(--ls-dai);
}

.detail-frame-wrap {
  border: 1px solid var(--ls-line-strong);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: #0d1115;
}

.detail-frame {
  width: 100%;
  height: 70vh;
  border: none;
  display: block;
}

.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 70px 20px;
  gap: 16px;
  background: var(--ls-glass);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius);
}

.nf-icon {
  font-size: 56px;
  opacity: 0.5;
}

.nf-text {
  color: var(--ls-text-3);
  font-size: 14px;
}
</style>