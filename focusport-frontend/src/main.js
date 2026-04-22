import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Legacy styles first (will be overridden by design system)
import './style.css'

// Design System styles (override legacy)
import './styles/tokens.css'
import './styles/base.css'
import './styles/transitions.css'

import App from './App.vue'
import { router } from './router'
import TresJS from '@tresjs/core'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(TresJS)

app.mount('#app')
