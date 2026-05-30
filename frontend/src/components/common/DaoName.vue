<template>
  <div class="dao-name-display" v-if="show" :title="`修行于天外天·第${visitDays}日`">
    <span class="dao-name-text">{{ daoName }}</span>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const show = ref(false)
const daoName = ref('')
const visitDays = ref(1)

// Seeded random function for consistent animation
const random = (seed) => Math.abs(Math.sin(seed * 12.9898 * 43758.5453) % 1)

// Extended 道号库 - 50+ entries
const daoNames = [
  '青莲居士', '听雨真人', '凌霄剑仙', '墨染书生', '逍遥子',
  '云中君', '碧落仙', '丹青客', '问道者', '归云溪',
  '风陵渡', '夜未央', '星河转', '清虚子', '太和仙',
  '白云深', '翠微峰', '天枢子', '玄明子', '清离子',
  '天璇仙', '天玑子', '天权子', '玉衡仙', '开阳子',
  '摇光仙', '北辰子', '南极仙', '东华帝君', '西王母',
  '青云子', '赤松子', '白眉仙', '紫霄子', '金虹仙',
  '玉泉子', '碧霞子', '赤霞仙', '玄天子', '昊天仙',
  '玄武子', '白虎仙', '青龙子', '朱雀仙', '麒麟子',
  '凤凰仙', '鲲鹏子', '鸿钧祖', '盘古子', '女娲仙',
  '醉月仙尊', '听风者', '望月仙', '踏雪真人', '寻梅子',
  '访山客', '问道仙', '悟真子', '养心仙', '卧云居士',
  '枕石仙子', '醉墨真人', '敲棋子', '拈花仙', '扫叶客'
]

// Immortal realms for variety
const realms = ['天外天', '三十三天', '九重云霄', '昆仑仙境', '蓬莱仙岛', '方丈瀛洲']

const loadDaoName = () => {
  // Check if first visit timestamp exists
  let firstVisit = localStorage.getItem('first_visit')
  if (!firstVisit) {
    firstVisit = Date.now()
    localStorage.setItem('first_visit', firstVisit.toString())
  }

  // Calculate visit days
  const days = Math.floor((Date.now() - parseInt(firstVisit)) / (1000 * 60 * 60 * 24))
  visitDays.value = days + 1

  // Get or generate dao name
  let stored = localStorage.getItem('dao_name')
  if (!stored) {
    // First visit - generate with seed based on timestamp for variety
    const seed = Math.floor(Date.now() / (1000 * 60 * 60 * 24)) // New seed each day
    const index = Math.floor(random(seed) * daoNames.length)
    stored = daoNames[index]
    localStorage.setItem('dao_name', stored)
  }
  daoName.value = stored

  show.value = true
}

onMounted(() => {
  loadDaoName()
})
</script>

<style scoped>
.dao-name-display {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: rgba(201, 169, 98, 0.08);
  border: 1px solid rgba(201, 169, 98, 0.25);
  border-radius: 20px;
  cursor: default;
  transition: all 0.3s ease;
}

.dao-name-display:hover {
  background: rgba(201, 169, 98, 0.15);
  border-color: rgba(201, 169, 98, 0.4);
  box-shadow: 0 0 15px rgba(201, 169, 98, 0.2);
}

.dao-name-text {
  font-family: var(--font-serif);
  font-size: 14px;
  color: var(--color-gold);
  letter-spacing: 2px;
  transition: all 0.3s ease;
}

.dao-name-display:hover .dao-name-text {
  text-shadow: 0 0 12px var(--color-gold);
  filter: drop-shadow(0 0 6px var(--color-gold));
}
</style>