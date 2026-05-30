<template>
  <div class="spirit-quiz" v-if="isVisible">
    <div class="quiz-card">
      <div class="quiz-header">
        <h2>🧘 灵根测试</h2>
        <p class="quiz-subtitle">探索你的修仙潜质</p>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="quiz-progress">
        <div class="progress-bar" :style="{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }"></div>
        <span class="progress-text">{{ currentQuestion + 1 }} / {{ questions.length }}</span>
      </div>

      <div class="quiz-content" v-if="!resultVisible">
        <p class="question-text">{{ questions[currentQuestion].question }}</p>

        <div class="options">
          <button
            v-for="(option, index) in questions[currentQuestion].options"
            :key="index"
            class="option-btn"
            :class="{ selected: selectedOption === index }"
            @click="selectOption(index)"
          >
            <span class="option-letter">{{ String.fromCharCode(65 + index) }}</span>
            <span class="option-text">{{ option.text }}</span>
          </button>
        </div>

        <button class="next-btn" :disabled="selectedOption === null" @click="nextQuestion">
          {{ currentQuestion < questions.length - 1 ? '下一题' : '查看结果' }}
        </button>
      </div>

      <div class="result-content" v-else>
        <div class="result-badge">{{ result.root }}</div>
        <p class="result-description">{{ result.description }}</p>
        <p class="result-traits">灵根特性：{{ result.traits }}</p>

        <div class="share-section">
          <button class="share-btn" @click="shareResult">📤 分享结果</button>
        </div>

        <button class="restart-btn" @click="restart">重新测试</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const isVisible = computed(() => props.visible)
const currentQuestion = ref(0)
const selectedOption = ref(null)
const resultVisible = ref(false)
const answers = ref([])

const questions = [
  {
    question: '你更喜欢在什么环境中修炼？',
    options: [
      { text: '高山之巅，云雾缭绕', element: 'wood' },
      { text: '江河湖畔，水汽氤氲', element: 'water' },
      { text: '荒漠戈壁，烈阳高照', element: 'fire' },
      { text: '金石之地，矿产丰富', element: 'metal' }
    ]
  },
  {
    question: '面对强敌你会怎么做？',
    options: [
      { text: '以柔克刚，四两拨千斤', element: 'wood' },
      { text: '静观其变，以退为进', element: 'water' },
      { text: '雷霆一击，速战速决', element: 'fire' },
      { text: '以守为攻，稳如磐石', element: 'metal' }
    ]
  },
  {
    question: '你渴望获得什么样的力量？',
    options: [
      { text: '生生不息的生命力', element: 'wood' },
      { text: '深邃莫测的智慧', element: 'water' },
      { text: '炽热如火的激情', element: 'fire' },
      { text: '坚不可摧的防御', element: 'metal' }
    ]
  },
  {
    question: '你的修炼方式更接近？',
    options: [
      { text: '亲近自然，吸收天地灵气', element: 'wood' },
      { text: '冥想打坐，心如止水', element: 'water' },
      { text: '实战炼体，突破极限', element: 'fire' },
      { text: '研读经典，参悟天道', element: 'metal' }
    ]
  },
  {
    question: '你最看重哪种品质？',
    options: [
      { text: '仁慈与包容', element: 'wood' },
      { text: '智慧与深远', element: 'water' },
      { text: '勇气与决断', element: 'fire' },
      { text: '坚毅与原则', element: 'metal' }
    ]
  }
]

const roots = {
  wood: {
    root: '🌿 木灵根',
    description: '你拥有生生不息的生命力，修仙之路适合走治愈与辅助之道。',
    traits: '生命亲和、自然感知、治愈之力'
  },
  water: {
    root: '🌊 水灵根',
    description: '你拥有深邃如海的智慧，修仙之路适合走心法与阵法之道。',
    traits: '智慧深远、心境如水、阵法天赋'
  },
  fire: {
    root: '🔥 火灵根',
    description: '你拥有炽热如火的激情，修仙之路适合走攻击与突破之道。',
    traits: '攻击犀利、突破迅速、战斗天赋'
  },
  metal: {
    root: '⚔️ 金灵根',
    description: '你拥有坚不可摧的意志，修仙之路适合走防御与炼器之道。',
    traits: '坚毅不屈、防御强大、炼器天赋'
  }
}

const result = computed(() => {
  const counts = { wood: 0, water: 0, fire: 0, metal: 0 }
  answers.value.forEach(answer => {
    if (answer) counts[answer.element]++
  })

  const maxElement = Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]
  return roots[maxElement]
})

const selectOption = (index) => {
  selectedOption.value = index
}

const nextQuestion = () => {
  answers.value.push(questions[currentQuestion.value].options[selectedOption.value])
  selectedOption.value = null

  if (currentQuestion.value < questions.length - 1) {
    currentQuestion.value++
  } else {
    resultVisible.value = true
  }
}

const restart = () => {
  currentQuestion.value = 0
  selectedOption.value = null
  resultVisible.value = false
  answers.value = []
}

const shareResult = () => {
  const text = `我在灵根测试中测出了【${result.value.root}】！修仙之路：${result.value.traits}`
  // 复制到剪贴板
  navigator.clipboard.writeText(text).then(() => {
    alert('结果已复制到剪贴板！')
  }).catch(() => {
    alert('分享失败，请手动复制')
  })
}

const close = () => {
  emit('close')
}
</script>

<style scoped>
.spirit-quiz {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 12, 18, 0.9);
  backdrop-filter: blur(10px);
}

.quiz-card {
  width: 90%;
  max-width: 500px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-gold);
  border-radius: var(--radius-lg);
  padding: 30px;
  box-shadow: var(--shadow-gold);
}

.quiz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.quiz-header h2 {
  font-family: var(--font-serif);
  color: var(--color-gold);
  margin: 0;
}

.quiz-subtitle {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin: 5px 0 0;
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 24px;
  cursor: pointer;
  padding: 0 10px;
}

.close-btn:hover {
  color: var(--color-gold);
}

.quiz-progress {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--color-gold);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  color: var(--color-text-muted);
  font-size: 12px;
}

.question-text {
  font-size: 18px;
  color: var(--color-text);
  margin-bottom: 25px;
  line-height: 1.6;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 25px;
}

.option-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 20px;
  background: var(--color-bg);
  border: 1px solid rgba(201, 169, 98, 0.2);
  border-radius: var(--radius);
  color: var(--color-text);
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.option-btn:hover {
  border-color: var(--color-gold);
  background: rgba(201, 169, 98, 0.1);
}

.option-btn.selected {
  border-color: var(--color-gold);
  background: rgba(201, 169, 98, 0.2);
}

.option-letter {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-gold);
  color: var(--color-bg);
  border-radius: 50%;
  font-weight: 600;
  font-size: 14px;
}

.option-text {
  flex: 1;
  font-size: 15px;
}

.next-btn {
  width: 100%;
  padding: 15px;
  background: var(--color-gold);
  border: none;
  border-radius: var(--radius);
  color: var(--color-bg);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.next-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.next-btn:not(:disabled):hover {
  background: var(--color-gold-dark);
}

.result-content {
  text-align: center;
}

.result-badge {
  font-size: 32px;
  margin-bottom: 20px;
}

.result-description {
  color: var(--color-text);
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 15px;
}

.result-traits {
  color: var(--color-gold);
  font-size: 14px;
  margin-bottom: 25px;
}

.share-section {
  margin-bottom: 15px;
}

.share-btn, .restart-btn {
  padding: 12px 24px;
  border-radius: var(--radius);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.share-btn {
  background: transparent;
  border: 1px solid var(--color-gold);
  color: var(--color-gold);
}

.share-btn:hover {
  background: rgba(201, 169, 98, 0.1);
}

.restart-btn {
  background: transparent;
  border: 1px solid var(--color-text-muted);
  color: var(--color-text-muted);
}

.restart-btn:hover {
  border-color: var(--color-text);
  color: var(--color-text);
}
</style>