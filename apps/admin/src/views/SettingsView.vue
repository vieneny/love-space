<script setup lang="ts">
import { onMounted } from 'vue'
import { CircleCheck, Lock, Refresh, Setting } from '@element-plus/icons-vue'
import { adminApi } from '../api'
import { display, formatBytes } from '../format'
import { useAsyncData } from '../composables/useAsyncData'
import PageHeading from '../components/PageHeading.vue'
import LoadError from '../components/LoadError.vue'

const { data, loading, error, refresh } = useAsyncData(adminApi.settings)
onMounted(refresh)
const environmentLabels: Record<string, string> = { development: '开发环境', production: '生产环境', test: '测试环境', testing: '测试环境', staging: '预发布环境' }
function statusLabel(value: unknown) { return value === true ? '已配置' : value === false ? '未配置' : '—' }
</script>

<template>
  <div>
    <PageHeading title="服务状态" description="查看当前环境与服务能力，确认配置是否就绪。" eyebrow="共赴山海手记 / 服务管理"><el-button :icon="Refresh" :loading="loading" @click="refresh">刷新状态</el-button></PageHeading>
    <LoadError v-if="error" :message="error" @retry="refresh" />
    <div v-else v-loading="loading" class="settings-grid" :aria-busy="loading">
      <section class="surface settings-panel">
        <div class="section-heading"><div><span class="eyebrow">运行环境</span><h2>服务与登录</h2></div><el-icon><Setting /></el-icon></div>
        <dl class="settings-list">
          <div><dt>当前环境</dt><dd><el-tag effect="light">{{ environmentLabels[String(data?.environment)] || display(data?.environment) }}</el-tag></dd></div>
          <div><dt>管理接口</dt><dd><span v-if="data" class="status-text"><i></i>连接正常</span><span v-else>—</span></dd></div>
          <div><dt>微信登录</dt><dd><el-tag :type="data?.wechat_login_configured === true ? 'success' : 'info'" effect="light">{{ statusLabel(data?.wechat_login_configured) }}</el-tag></dd></div>
          <div><dt>开发登录</dt><dd>{{ data?.dev_login_enabled === true ? '已开启' : data?.dev_login_enabled === false ? '已关闭' : '—' }}</dd></div>
        </dl>
        <p class="panel-footnote">微信登录状态反映服务端凭证配置情况，实际授权登录仍需在微信中验证。</p>
      </section>
      <section class="surface settings-panel">
        <div class="section-heading"><div><span class="eyebrow">回忆的存放方式</span><h2>存储与地图</h2></div><el-icon><Lock /></el-icon></div>
        <dl class="settings-list">
          <div><dt>媒体访问</dt><dd>{{ data?.media_storage === 'private' ? '私密存储 · 访问需授权' : display(data?.media_storage) }}</dd></div>
          <div><dt>单文件大小上限</dt><dd>{{ formatBytes(data?.media_max_bytes) }}</dd></div>
          <div><dt>地图服务</dt><dd><el-tag :type="data?.map_provider === 'unconfigured' ? 'info' : 'success'" effect="light">{{ data?.map_provider === 'unconfigured' ? '未配置' : display(data?.map_provider) }}</el-tag></dd></div>
        </dl>
        <p class="panel-footnote">地图未配置时仍可保存地点文字和回忆。地图展示能力需结合小程序配置验证。</p>
      </section>
      <section class="surface settings-principles"><span class="principle-icon"><el-icon><CircleCheck /></el-icon></span><div><h2>只展示状态，妥善保管凭证</h2><p>服务凭证由部署环境管理。后台只读取运行状态，不显示微信密钥或存储密钥。</p></div></section>
    </div>
  </div>
</template>
