<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { ArrowRight, Collection, Compass, Lock, Picture, Reading, Refresh, User } from '@element-plus/icons-vue'
import { adminApi } from '../api'
import { display, formatBytes } from '../format'
import { useAsyncData } from '../composables/useAsyncData'
import PageHeading from '../components/PageHeading.vue'
import LoadError from '../components/LoadError.vue'

const { data, loading, error, refresh } = useAsyncData(adminApi.overview)
onMounted(refresh)
const metrics = computed(() => [
  { title: '用户', value: data.value?.users, suffix: '位', icon: User, color: 'ocean', path: '/users', note: '在这里开始记录' },
  { title: '情侣空间', value: data.value?.spaces, suffix: '个', icon: Collection, color: 'forest', path: '/spaces', note: '共同收藏生活' },
  { title: '共同与个人回忆', value: data.value?.memories, suffix: '条', icon: Reading, color: 'coral', path: '/memories', note: '地点、故事与重要时刻' },
  { title: '旅行', value: data.value?.trips, suffix: '次', icon: Compass, color: 'ocean', path: '/memories', note: '串起每一站的故事' },
])
</script>

<template>
  <div>
    <PageHeading title="运营概览" description="看见服务的使用情况，让每段共同旅程安心被记录。" eyebrow="共赴山海手记 / 工作台">
      <el-button :icon="Refresh" :loading="loading" @click="refresh">刷新数据</el-button>
    </PageHeading>
    <LoadError v-if="error" :message="error" @retry="refresh" />
    <template v-else>
      <section class="overview-intro" aria-label="工作台说明">
        <div>
          <span class="journal-label">我们的地图 · 共同的时光</span>
          <h2>每一段同行，<br class="mobile-only" />都值得被认真守护。</h2>
          <p>从想去的地方，到已经走过的路；从日常片刻，到人生的重要时刻。</p>
        </div>
        <div class="intro-route" aria-hidden="true"><i></i><span></span><i></i><span></span><b>♡</b></div>
      </section>
      <section class="metric-grid" aria-label="使用统计" :aria-busy="loading">
        <router-link v-for="metric in metrics" :key="metric.title" :to="metric.path" class="metric-card">
          <div class="metric-top"><span>{{ metric.title }}</span><span class="metric-icon" :class="metric.color"><el-icon><component :is="metric.icon" /></el-icon></span></div>
          <el-skeleton v-if="loading && !data" :rows="0" animated><template #template><el-skeleton-item variant="h1" class="metric-skeleton" /></template></el-skeleton>
          <div v-else class="metric-value">{{ display(metric.value) }}<span>{{ metric.suffix }}</span></div>
          <p>{{ metric.note }}<el-icon><ArrowRight /></el-icon></p>
        </router-link>
      </section>
      <div class="overview-bottom-grid">
        <section class="surface storage-panel">
          <div class="section-heading"><div><span class="eyebrow">让回忆有处安放</span><h2>媒体与生活记录</h2></div><el-icon><Picture /></el-icon></div>
          <el-skeleton v-if="loading && !data" :rows="3" animated />
          <div v-else class="resource-grid">
            <div><span>媒体文件</span><strong>{{ display(data?.media_count) }} <small>个</small></strong></div>
            <div><span>已用存储</span><strong class="storage-size">{{ formatBytes(data?.storage_bytes) }}</strong></div>
            <div><span>共同愿望</span><strong>{{ display(data?.wishes) }} <small>个</small></strong></div>
            <div><span>共同习惯</span><strong>{{ display(data?.habits) }} <small>个</small></strong></div>
          </div>
          <p class="panel-footnote">显示当前服务中的实际记录数量，刷新后更新。</p>
        </section>
        <section class="surface quick-panel">
          <div class="section-heading"><div><span class="eyebrow">日常照顾</span><h2>运营快捷入口</h2></div></div>
          <router-link to="/questions" class="quick-link"><span><strong>准备下一次对话</strong><small>维护每日问题，启用适合两个人的话题</small></span><el-icon><ArrowRight /></el-icon></router-link>
          <router-link to="/feedback" class="quick-link"><span><strong>听听他们的建议</strong><small>查看用户主动提交的产品反馈</small></span><el-icon><ArrowRight /></el-icon></router-link>
          <div class="privacy-note"><el-icon><Lock /></el-icon><p>回忆列表只提供运营所需元数据，私密故事、坐标与照片不在后台展示。</p></div>
        </section>
      </div>
    </template>
  </div>
</template>
