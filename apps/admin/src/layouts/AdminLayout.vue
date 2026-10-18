<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, ChatDotRound, Collection, DataAnalysis, Document, Lock, Menu, Monitor, Reading, SwitchButton, User } from '@element-plus/icons-vue'
import { clearSession, session } from '../auth'
import BrandMark from '../components/BrandMark.vue'

const route = useRoute()
const router = useRouter()
const drawerOpen = ref(false)
const groups = [
  { label: '工作台', items: [{ path: '/overview', label: '运营概览', icon: DataAnalysis }] },
  { label: '空间与内容', items: [
    { path: '/users', label: '用户管理', icon: User },
    { path: '/spaces', label: '情侣空间', icon: Collection },
    { path: '/memories', label: '回忆元数据', icon: Reading },
  ] },
  { label: '内容运营', items: [
    { path: '/questions', label: '每日题库', icon: ChatDotRound },
    { path: '/feedback', label: '用户反馈', icon: Document },
  ] },
  { label: '服务管理', items: [
    { path: '/audit-logs', label: '操作审计', icon: Lock },
    { path: '/settings', label: '服务状态', icon: Monitor },
  ] },
]
const section = computed(() => String(route.meta.section || '工作台'))
watch(() => route.fullPath, () => { drawerOpen.value = false })

function logout() {
  clearSession()
  void router.replace('/login')
}
</script>

<template>
  <div class="admin-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <aside class="desktop-sidebar">
      <router-link to="/overview" class="brand" aria-label="共赴山海手记，回到运营概览">
        <BrandMark class="brand-mark" />
        <span><strong>共赴山海手记</strong><small>运营管理后台</small></span>
      </router-link>
      <nav class="nav-groups" aria-label="管理导航">
        <div v-for="group in groups" :key="group.label" class="nav-group">
          <p>{{ group.label }}</p>
          <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="nav-link">
            <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
            <span class="nav-active-mark" aria-hidden="true"></span>
          </router-link>
        </div>
      </nav>
      <div class="sidebar-note"><el-icon><Lock /></el-icon><span>守护两个人的回忆<small>私密内容保留在他们之间</small></span></div>
    </aside>

    <el-drawer v-model="drawerOpen" title="共赴山海手记 · 导航" direction="ltr" size="260px" class="mobile-drawer">
      <nav class="nav-groups" aria-label="移动端管理导航">
        <div v-for="group in groups" :key="group.label" class="nav-group">
          <p>{{ group.label }}</p>
          <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="nav-link">
            <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
          </router-link>
        </div>
      </nav>
    </el-drawer>

    <div class="workspace">
      <header class="topbar">
        <div class="breadcrumb">
          <el-button class="mobile-menu-button" text aria-label="打开管理导航" @click="drawerOpen = true"><el-icon><Menu /></el-icon></el-button>
          <span>{{ section }}</span><el-icon><ArrowRight /></el-icon><strong>{{ route.meta.title }}</strong>
        </div>
        <div class="account-tools">
          <span class="account-avatar" aria-hidden="true">{{ session.username.slice(0, 1).toUpperCase() }}</span>
          <span class="account-name">{{ session.username }}</span>
          <el-button text class="logout-button" @click="logout"><el-icon><SwitchButton /></el-icon><span>退出登录</span></el-button>
        </div>
      </header>
      <main id="main-content" class="main-content" tabindex="-1">
        <router-view />
      </main>
      <footer class="workspace-footer"><span>共赴山海手记 · 一起把日子走成故事</span><span>Love Space / 管理工作台</span></footer>
    </div>
  </div>
</template>
