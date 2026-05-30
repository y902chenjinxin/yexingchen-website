<template>
  <div class="realm-selector" :class="{ 'ancient-mode': isAncient }">
    <button class="realm-toggle" @click="toggleMode">
      <span class="realm-icon">{{ isAncient ? '古' : '今' }}</span>
      <span class="realm-label">{{ isAncient ? '古文模式' : '今文模式' }}</span>
    </button>

    <Teleport to="body">
      <div class="realm-hint" v-if="showHint">
        <p>{{ hintText }}</p>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const isAncient = ref(false)
const showHint = ref(false)

const modeText = {
  modern: {
    login: '登录',
    logout: '退出账号',
    settings: '设置',
    home: '首页'
  },
  ancient: {
    login: '入山门',
    logout: '归隐',
    settings: '法诀',
    home: '仙府'
  }
}

// 翻译映射
const translations = {
  modern: {
    '登录': '登录',
    '退出账号': '退出账号',
    '个人中心': '个人中心',
    '修改密码': '修改密码',
    '选择头像': '选择头像',
    '音乐岛': '音乐岛',
    '小说岛': '小说岛',
    '视频岛': '视频岛',
    '日志岛': '日志岛',
    '工具岛': '工具岛',
    '管理后台': '管理后台',
    '音乐岛内景': '琉璃宫',
    '小说岛内景': '竹简阁',
    '视频岛内景': '光影廊',
    '日志岛内景': '墨池台',
    '工具岛内景': '天机阁'
  },
  ancient: {
    '登录': '入山门',
    '退出账号': '归隐',
    '个人中心': '灵台',
    '修改密码': '换脉',
    '选择头像': '易容',
    '音乐岛': '音律岛',
    '小说岛': '书卷岛',
    '视频岛': '光影岛',
    '日志岛': '墨迹岛',
    '工具岛': '机关岛',
    '管理后台': '掌教台',
    '音乐岛内景': '琉璃宫',
    '小说岛内景': '竹简阁',
    '视频岛内景': '光影廊',
    '日志岛内景': '墨池台',
    '工具岛内景': '天机阁'
  }
}

const hintText = computed(() => {
  return isAncient.value
    ? '已切换至古文模式，UI文字将变为半文言'
    : '已切换至现代模式，UI文字为标准中文'
})

const toggleMode = () => {
  isAncient.value = !isAncient.value

  // 保存到 localStorage
  localStorage.setItem('realm_mode', isAncient.value ? 'ancient' : 'modern')

  // 显示提示
  showHint.value = true
  setTimeout(() => {
    showHint.value = false
  }, 2000)

  // 广播模式切换事件
  window.dispatchEvent(new CustomEvent('realm-mode-change', {
    detail: { mode: isAncient.value ? 'ancient' : 'modern' }
  }))
}

const getText = (key) => {
  const mode = isAncient.value ? 'ancient' : 'modern'
  return translations[mode][key] || key
}

// 暴露给外部使用
defineExpose({ getText, isAncient })

onMounted(() => {
  // 读取保存的模式
  const savedMode = localStorage.getItem('realm_mode')
  if (savedMode === 'ancient') {
    isAncient.value = true
  }
})
</script>

<style scoped>
.realm-selector {
  position: fixed;
  bottom: 80px;
  left: 20px;
  z-index: 100;
}

.realm-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--color-bg-elevated);
  border: 1px solid rgba(201, 169, 98, 0.3);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.realm-toggle:hover {
  border-color: var(--color-gold);
  box-shadow: var(--shadow-gold);
}

.realm-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-gold);
  color: var(--color-bg);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
}

.ancient-mode .realm-icon {
  background: var(--color-purple);
}

.realm-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.ancient-mode .realm-label {
  color: var(--color-gold);
}

.realm-hint {
  position: fixed;
  bottom: 140px;
  left: 20px;
  padding: 12px 20px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-gold);
  border-radius: var(--radius);
  box-shadow: var(--shadow-gold);
  z-index: 2000;
  animation: fade-in 0.3s ease;
}

.realm-hint p {
  margin: 0;
  font-size: 14px;
  color: var(--color-text);
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>