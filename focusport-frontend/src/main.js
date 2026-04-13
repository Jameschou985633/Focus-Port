import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Legacy styles first (will be overridden by design system)
import './style.css'

// Design System Styles (overrides legacy)
import './styles/tokens.css'
import './styles/base.css'
import './styles/transitions.css'

import App from './App.vue'
import { router } from './router'

// TresJS components are auto-registered when TresCanvas is used

const app = createApp(App)

// Pinia 状态管理
const pinia = createPinia()
app.use(pinia)

// Vue Router
app.use(router)

app.mount('#app')
