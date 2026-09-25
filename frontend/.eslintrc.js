module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended'
  ],
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module'
  },
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/no-v-html': 'warn',
    'no-console': 'warn',
    'no-debugger': 'warn',
    // 项目里大量「尽力而为」的旁路操作（localStorage 写入、navigator.vibrate、
    // SW 注册/换版消息）都刻意吞掉异常，空 catch 是设计而非疏漏
    'no-empty': ['error', { allowEmptyCatch: true }],

    /* ---------- 关掉纯排版规则，让 eslint 只管语义 ----------
     * vue3-recommended 自带一批「排版」规则（换行位置、属性排序、缩进、自闭合），
     * 原本指望 prettier 接管，但 prettier 并未安装（.prettierrc / lint-staged 是空配置），
     * 于是这批规则长期处于「从未被满足」状态——全仓 5800+ 条告警全是排版，
     * 真正的语义问题（未使用变量、空块、错用 ref）被淹没在里面没人看。
     * 关掉后基线只剩 14 条有意义的告警，新增告警一眼可见。
     * 若日后接入 prettier，可把 'eslint-config-prettier' 加进 extends 代替这段。
     */
    'vue/max-attributes-per-line': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/multiline-html-element-content-newline': 'off',
    'vue/html-self-closing': 'off',
    'vue/html-indent': 'off',
    'vue/html-closing-bracket-spacing': 'off',
    'vue/html-closing-bracket-newline': 'off',
    'vue/first-attribute-linebreak': 'off',
    'vue/attributes-order': 'off'
  }
}
