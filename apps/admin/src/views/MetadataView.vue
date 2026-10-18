<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Lock, Refresh, Search } from '@element-plus/icons-vue'
import { adminApi } from '../api'
import { display, formatTime } from '../format'
import { useAsyncData } from '../composables/useAsyncData'
import PageHeading from '../components/PageHeading.vue'
import LoadError from '../components/LoadError.vue'

interface Column { key: string; label: string; width?: number; minWidth?: number; type?: 'time' | 'date' | 'status' | 'visibility' | 'kind' }
interface ResourceDefinition { title: string; description: string; empty: string; search: string; columns: Column[] }
const definitions: Record<string, ResourceDefinition> = {
  users: {
    title: '用户管理', description: '查看账号与当前空间的归属信息。', empty: '还没有用户，真实用户首次登录后会显示在这里。', search: '搜索用户编号、昵称或空间编号',
    columns: [{ key: 'nickname', label: '用户昵称', minWidth: 150 }, { key: 'id', label: '用户编号', minWidth: 250 }, { key: 'space_id', label: '当前空间', minWidth: 250 }, { key: 'created_at', label: '注册时间', minWidth: 170, type: 'time' }],
  },
  spaces: {
    title: '情侣空间', description: '了解空间的使用状态与成员数量。', empty: '还没有情侣空间，用户创建空间后会显示在这里。', search: '搜索空间名称或编号',
    columns: [{ key: 'title', label: '空间名称', minWidth: 170 }, { key: 'id', label: '空间编号', minWidth: 250 }, { key: 'member_count', label: '成员数', width: 90 }, { key: 'active', label: '状态', width: 110, type: 'status' }, { key: 'start_date', label: '在一起的日期', minWidth: 140 }, { key: 'created_at', label: '创建时间', minWidth: 170, type: 'time' }],
  },
  memories: {
    title: '回忆元数据', description: '查看回忆的归属、分类与数量，帮助排查使用问题。', empty: '还没有回忆记录，用户保存第一条回忆后会显示在这里。', search: '搜索回忆编号、作者、空间或行程编号',
    columns: [{ key: 'id', label: '回忆编号', minWidth: 250 }, { key: 'kind', label: '类型', width: 110, type: 'kind' }, { key: 'visibility', label: '可见范围', width: 110, type: 'visibility' }, { key: 'author_id', label: '作者编号', minWidth: 250 }, { key: 'space_id', label: '空间编号', minWidth: 250 }, { key: 'trip_id', label: '行程编号', minWidth: 250 }, { key: 'photo_count', label: '照片数', width: 90 }, { key: 'occurred_on', label: '发生日期', width: 130 }, { key: 'created_at', label: '记录时间', minWidth: 170, type: 'time' }],
  },
  feedback: {
    title: '用户反馈', description: '阅读用户主动提交的建议，找到需要改进的体验。', empty: '还没有用户反馈。用户提交建议后，会汇集到这里。', search: '搜索反馈内容或用户编号',
    columns: [{ key: 'content', label: '反馈内容', minWidth: 360 }, { key: 'author_id', label: '用户编号', minWidth: 250 }, { key: 'id', label: '反馈编号', minWidth: 250 }, { key: 'created_at', label: '提交时间', minWidth: 170, type: 'time' }],
  },
  'audit-logs': {
    title: '操作审计', description: '查看服务记录的操作与发生时间，追溯管理变更。', empty: '还没有审计记录。系统记录的操作会显示在这里。', search: '搜索操作者、操作或目标编号',
    columns: [{ key: 'actor', label: '操作者', minWidth: 150 }, { key: 'action', label: '操作', minWidth: 200 }, { key: 'target_id', label: '目标编号', minWidth: 250 }, { key: 'created_at', label: '发生时间', minWidth: 170, type: 'time' }, { key: 'id', label: '记录编号', minWidth: 250 }],
  },
}
const route = useRoute()
const resource = computed(() => String(route.meta.resource || 'users'))
const definition = computed(() => definitions[resource.value]!)
const query = ref('')
const page = ref(1)
const pageSize = ref(15)
const { data, loading, error, refresh } = useAsyncData(() => adminApi.list(resource.value))
onMounted(refresh)
watch(resource, () => { query.value = ''; page.value = 1; data.value = undefined; void refresh() })
watch([query, pageSize], () => { page.value = 1 })
const rows = computed(() => {
  const filter = query.value.trim().toLocaleLowerCase()
  const items = data.value?.items || []
  if (!filter) return items
  return items.filter((row) => definition.value.columns.some((column) => display(row[column.key]).toLocaleLowerCase().includes(filter)))
})
const pageRows = computed(() => rows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const kindLabels: Record<string, string> = { travel: '旅行', milestone: '重要时刻', daily: '日常' }
</script>

<template>
  <div>
    <PageHeading :title="definition.title" :description="definition.description" :eyebrow="`共赴山海手记 / ${route.meta.section}`">
      <el-button :icon="Refresh" :loading="loading" @click="refresh">刷新列表</el-button>
    </PageHeading>
    <div v-if="resource === 'memories'" class="privacy-banner"><el-icon><Lock /></el-icon><span>仅展示元数据。标题、正文、精确坐标和照片链接保留在用户的私密空间。</span></div>
    <LoadError v-if="error" :message="error" @retry="refresh" />
    <section v-else class="surface table-panel" :aria-busy="loading">
      <div class="table-toolbar">
        <div><strong>全部{{ resource === 'audit-logs' ? '操作' : resource === 'feedback' ? '反馈' : resource === 'memories' ? '回忆' : resource === 'spaces' ? '空间' : '用户' }}</strong><span class="count-tag">{{ data ? data.total : '—' }}</span></div>
        <el-input v-model="query" :prefix-icon="Search" :placeholder="definition.search" :aria-label="definition.search" clearable class="table-search" />
      </div>
      <el-table v-loading="loading" :data="pageRows" row-key="id" stripe :empty-text="loading ? '正在加载…' : query ? '没有匹配的结果，试试其他关键词。' : definition.empty" class="metadata-table" table-layout="auto">
        <el-table-column v-for="column in definition.columns" :key="column.key" :prop="column.key" :label="column.label" :width="column.width" :min-width="column.minWidth" :show-overflow-tooltip="column.key !== 'content'">
          <template #default="{ row }">
            <template v-if="column.type === 'time'"><span class="table-time">{{ formatTime(row[column.key]) }}</span></template>
            <template v-else-if="column.type === 'status'"><el-tag :type="row[column.key] ? 'success' : 'info'" effect="light" round>{{ row[column.key] ? '使用中' : '已归档' }}</el-tag></template>
            <template v-else-if="column.type === 'visibility'"><el-tag :type="row[column.key] === 'shared' ? 'success' : 'info'" effect="plain" round>{{ row[column.key] === 'shared' ? '情侣共享' : '仅本人' }}</el-tag></template>
            <template v-else-if="column.type === 'kind'"><span>{{ kindLabels[String(row[column.key])] || display(row[column.key]) }}</span></template>
            <span v-else :class="{ 'id-text': column.key === 'id' || column.key.endsWith('_id'), 'feedback-content': column.key === 'content' }">{{ display(row[column.key]) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-footer">
        <span>{{ query ? `匹配 ${rows.length} 条` : `已加载 ${data?.items.length || 0} 条记录` }}</span>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[15, 30, 50]" :total="rows.length" layout="prev, pager, next, sizes" background small />
      </div>
    </section>
  </div>
</template>
