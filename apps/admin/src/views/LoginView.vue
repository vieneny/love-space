<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Lock, User } from '@element-plus/icons-vue'
import { adminApi } from '../api'
import { setSession } from '../auth'
import BrandMark from '../components/BrandMark.vue'

const route = useRoute()
const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const expired = computed(() => route.query.expired === '1')

async function login() {
  if (!form.username.trim() || !form.password || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const result = await adminApi.login(form.username.trim(), form.password)
    if (!result.access_token) throw new Error('服务未返回有效登录信息，请联系管理员。')
    setSession(result.access_token, form.username.trim())
    form.password = ''
    const target = typeof route.query.redirect === 'string' ? route.query.redirect : '/overview'
    await router.replace(target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/login') ? target : '/overview')
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '登录失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-story">
      <div class="brand login-brand"><BrandMark class="brand-mark" /><span><strong>共赴山海手记</strong><small>OUR JOURNEY, TOGETHER</small></span></div>
      <div class="login-story-copy">
        <div class="eyebrow">两个人的地图，一路上的故事</div>
        <h1>把走过的路，<br />留在共同的时光里。</h1>
        <p>每一座去过的城市，每一个值得记住的日子，<br class="desktop-break" />都成为两个人的共同回忆。</p>
        <div class="journey-illustration" aria-hidden="true">
          <svg viewBox="0 0 600 260" fill="none">
            <path d="M-30 225c75-43 122-128 207-86 74 38 118 65 180-18 55-75 151-76 269-112" stroke="#C6D9DC" stroke-width="1" />
            <path d="M-20 255c103-76 129-106 214-68 98 43 116-40 171-81 61-48 145-25 247-91M-20 190C76 172 93 80 178 97c84 17 143 76 204 1 50-62 157-42 239-93" stroke="#DCE7E7" stroke-width="1" />
            <path d="M74 180c63-83 127-35 188-34 53 1 69-60 132-65 38-3 69 8 119-34" stroke="#477A68" stroke-width="2" stroke-dasharray="5 7" />
            <circle cx="74" cy="180" r="7" fill="#F5F8FA" stroke="#477A68" stroke-width="3" />
            <circle cx="263" cy="146" r="7" fill="#F5F8FA" stroke="#477A68" stroke-width="3" />
            <path d="M513 26c-10 0-18 8-18 18 0 13 18 28 18 28s18-15 18-28c0-10-8-18-18-18Z" fill="#E2917D" />
            <circle cx="513" cy="44" r="6" fill="#F5F8FA" />
            <path d="m353 216 15-26 14 26m-5-10 6-11 13 21M136 59l8-14 8 14" stroke="#7D9B96" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <div class="login-story-caption"><span>共同旅行</span><span class="caption-dot"></span><span>重要时刻</span><span class="caption-dot"></span><span>日常回忆</span></div>
      </div>
      <p class="login-copyright">一起把日子走成故事。</p>
    </div>

    <div class="login-panel">
      <div class="login-form-wrap">
        <div class="login-kicker"><span></span> 运营工作台</div>
        <h2>欢迎回来</h2>
        <p class="login-description">登录管理账号，继续照顾这段共同旅程。</p>
        <el-alert v-if="expired && !error" title="登录已过期，请重新登录。" type="info" :closable="false" show-icon class="login-alert" />
        <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="login-alert" role="alert" />
        <form class="login-form" @submit.prevent="login">
          <label for="admin-username">管理账号</label>
          <el-input id="admin-username" v-model="form.username" :prefix-icon="User" placeholder="输入管理账号" autocomplete="username" size="large" autofocus maxlength="120" :disabled="loading" required />
          <label for="admin-password">密码</label>
          <el-input id="admin-password" v-model="form.password" :prefix-icon="Lock" type="password" show-password placeholder="输入密码" autocomplete="current-password" size="large" :disabled="loading" required />
          <el-button class="login-submit" type="primary" size="large" native-type="submit" :loading="loading" :disabled="!form.username.trim() || !form.password">登录工作台<el-icon v-if="!loading"><ArrowRight /></el-icon></el-button>
        </form>
        <p class="login-access-note"><el-icon><Lock /></el-icon>仅限获授权的运营人员访问</p>
      </div>
      <div class="login-panel-footer">共赴山海手记 <span>/</span> 管理后台</div>
    </div>
  </div>
</template>
