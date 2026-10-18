import { createRouter, createWebHistory } from 'vue-router'
import { session } from './auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/login', name: 'login', component: () => import('./views/LoginView.vue'), meta: { title: '登录' } },
    {
      path: '/', component: () => import('./layouts/AdminLayout.vue'), meta: { authenticated: true },
      children: [
        { path: '', redirect: '/overview' },
        { path: 'overview', name: 'overview', component: () => import('./views/OverviewView.vue'), meta: { title: '运营概览', section: '总览' } },
        { path: 'users', name: 'users', component: () => import('./views/MetadataView.vue'), meta: { title: '用户管理', section: '空间与内容', resource: 'users' } },
        { path: 'spaces', name: 'spaces', component: () => import('./views/MetadataView.vue'), meta: { title: '情侣空间', section: '空间与内容', resource: 'spaces' } },
        { path: 'memories', name: 'memories', component: () => import('./views/MetadataView.vue'), meta: { title: '回忆元数据', section: '空间与内容', resource: 'memories' } },
        { path: 'questions', name: 'questions', component: () => import('./views/QuestionsView.vue'), meta: { title: '每日题库', section: '内容运营' } },
        { path: 'feedback', name: 'feedback', component: () => import('./views/MetadataView.vue'), meta: { title: '用户反馈', section: '内容运营', resource: 'feedback' } },
        { path: 'audit-logs', name: 'audit-logs', component: () => import('./views/MetadataView.vue'), meta: { title: '操作审计', section: '服务管理', resource: 'audit-logs' } },
        { path: 'settings', name: 'settings', component: () => import('./views/SettingsView.vue'), meta: { title: '服务状态', section: '服务管理' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/overview' },
  ],
})

router.beforeEach((to) => {
  if (to.matched.some((route) => route.meta.authenticated) && !session.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && session.token) return { name: 'overview' }
})
router.afterEach((to) => { document.title = `${String(to.meta.title || '管理后台')} · 共赴山海手记` })
window.addEventListener('admin-session-expired', () => {
  if (router.currentRoute.value.name !== 'login') {
    void router.replace({ name: 'login', query: { expired: '1', redirect: router.currentRoute.value.fullPath } })
  }
})

export default router
