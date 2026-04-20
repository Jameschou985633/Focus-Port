import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../components/LoginPage.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/',
    name: 'FocusHubHome',
    component: () => import('../components/FocusHubPage.vue'),
    meta: { title: '自律中枢', requiresAuth: true }
  },
  {
    path: '/island',
    name: 'Island',
    component: () => import('../components/CityDimensionShell.vue'),
    meta: { title: '星港基地', requiresAuth: true }
  },
  {
    path: '/stats',
    name: 'Stats',
    component: () => import('../components/StatsPanel.vue'),
    meta: { title: '统计数据', requiresAuth: true }
  },
  {
    path: '/shop',
    name: 'UnifiedShop',
    component: () => import('../components/shop/UnifiedShop.vue'),
    meta: { title: '建筑商店', requiresAuth: true }
  },
  {
    path: '/vault',
    name: 'BlueprintVault',
    component: () => import('../components/BlueprintVaultPage.vue'),
    meta: { title: '工程装备仓', requiresAuth: true }
  },
  {
    path: '/backpack',
    redirect: '/vault'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../components/Dashboard.vue'),
    meta: { title: '数据仪表', requiresAuth: true }
  },
  {
    path: '/focus-hub',
    redirect: '/'
  },
  {
    path: '/leaderboard',
    name: 'Leaderboard',
    component: () => import('../components/Leaderboard.vue'),
    meta: { title: '排行榜', requiresAuth: true }
  },
  {
    path: '/achievements',
    name: 'Achievements',
    component: () => import('../components/AchievementPanel.vue'),
    meta: { title: '成就墙', requiresAuth: true }
  },
  {
    path: '/friends',
    name: 'Friends',
    component: () => import('../components/FriendsPanel.vue'),
    meta: { title: '星港社区', requiresAuth: true }
  },
  {
    path: '/build-shop',
    redirect: '/shop'
  },
  {
    path: '/ai',
    name: 'AIAssistant',
    component: () => import('../components/AIAssistant.vue'),
    meta: { title: '副官终端', requiresAuth: true }
  },
  {
    path: '/plans',
    name: 'StudyPlan',
    component: () => import('../components/StudyPlan.vue'),
    meta: { title: '学习计划', requiresAuth: true }
  },
  {
    path: '/events',
    name: 'Events',
    component: () => import('../components/EventPanel.vue'),
    meta: { title: '活动与签到', requiresAuth: true }
  },
  {
    path: '/exam',
    name: 'Exam',
    component: () => import('../components/ExamPage.vue'),
    meta: { title: '语言考核站', requiresAuth: true }
  },
  {
    path: '/pk',
    name: 'PKChallenge',
    component: () => import('../components/PKChallenge.vue'),
    meta: { title: 'PK 挑战', requiresAuth: true }
  },
  {
    path: '/collab',
    name: 'CollabTimer',
    component: () => import('../components/collab/CollabTimerList.vue'),
    meta: { title: '联合星桥枢纽 · FLEET NEXUS', requiresAuth: true }
  },
  {
    path: '/collab/:id',
    name: 'CollabTimerRoom',
    component: () => import('../components/collab/CollabTimerRoom.vue'),
    meta: { title: '联合星桥枢纽 · FLEET NEXUS', requiresAuth: true }
  },
  {
    path: '/playground',
    name: 'Playground',
    component: () => import('../components/PlaygroundPage.vue'),
    meta: { title: '游乐场', requiresAuth: true }
  },
  {
    path: '/playground/gomoku/online/:roomCode',
    name: 'GomokuOnline',
    component: () => import('../components/GomokuRoom.vue'),
    meta: { title: '五子棋', requiresAuth: true }
  },
  {
    path: '/playground/gomoku/:id',
    name: 'GomokuRoom',
    component: () => import('../components/GomokuRoom.vue'),
    meta: { title: '五子棋', requiresAuth: true }
  },
  {
    path: '/playground/gomoku-solo',
    name: 'GomokuSolo',
    component: () => import('../components/GomokuRoom.vue'),
    meta: { title: '五子棋', requiresAuth: true }
  },
  {
    path: '/playground/tictactoe',
    name: 'TicTacToe',
    component: () => import('../components/TicTacToeGame.vue'),
    meta: { title: '井字棋', requiresAuth: true }
  },
  {
    path: '/playground/tictactoe/online/:roomCode',
    name: 'TicTacToeOnline',
    component: () => import('../components/TicTacToeGame.vue'),
    meta: { title: '井字棋', requiresAuth: true }
  },
  {
    path: '/playground/connect-four',
    name: 'ConnectFour',
    component: () => import('../components/ConnectFourGame.vue'),
    meta: { title: '四子棋', requiresAuth: true }
  },
  {
    path: '/playground/connect-four/online/:roomCode',
    name: 'ConnectFourOnline',
    component: () => import('../components/ConnectFourGame.vue'),
    meta: { title: '四子棋', requiresAuth: true }
  },
  {
    path: '/playground/reversi',
    name: 'Reversi',
    component: () => import('../components/ReversiGame.vue'),
    meta: { title: '黑白棋', requiresAuth: true }
  },
  {
    path: '/playground/reversi/online/:roomCode',
    name: 'ReversiOnline',
    component: () => import('../components/ReversiGame.vue'),
    meta: { title: '黑白棋', requiresAuth: true }
  },
  {
    path: '/more',
    name: 'More',
    component: () => import('../components/MorePage.vue'),
    meta: { title: '舰桥中控', requiresAuth: true }
  },
  {
    path: '/mail',
    name: 'Mail',
    component: () => import('../components/MailPage.vue'),
    meta: { title: '星际信箱', requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../components/AdminPanel.vue'),
    meta: { title: '开发者设置', requiresAuth: true }
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'FocusPort'} - FocusPort`

  const isLoggedIn = localStorage.getItem('username')

  if (to.meta.requiresAuth && !isLoggedIn) {
    next('/login')
  } else if (to.meta.guest && isLoggedIn) {
    next('/')
  } else {
    next()
  }
})