<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ChatDotRound, Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../api'
import type { Question } from '../api'
import { useAsyncData } from '../composables/useAsyncData'
import PageHeading from '../components/PageHeading.vue'
import LoadError from '../components/LoadError.vue'

const { data, loading, error, refresh } = useAsyncData(adminApi.questions)
const query = ref('')
const status = ref('all')
const dialogOpen = ref(false)
const saving = ref(false)
const dialogError = ref('')
const changing = ref(new Set<string>())
const form = reactive({ id: '', text: '', active: true })
const filtered = computed(() => (data.value?.items || []).filter((row) => {
  return (!query.value.trim() || row.text.toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase()))
    && (status.value === 'all' || row.active === (status.value === 'active'))
}))
const activeCount = computed(() => data.value?.items.filter((row) => row.active).length || 0)
onMounted(refresh)

function edit(row?: Question) {
  form.id = row?.id || ''
  form.text = row?.text || ''
  form.active = row?.active ?? true
  dialogError.value = ''
  dialogOpen.value = true
}

async function save() {
  const text = form.text.trim()
  if (!text || saving.value) return
  saving.value = true
  dialogError.value = ''
  try {
    if (form.id) await adminApi.updateQuestion(form.id, { text, active: form.active })
    else await adminApi.createQuestion(text, form.active)
    dialogOpen.value = false
    ElMessage.success(form.id ? '问题已保存' : '问题已添加')
    await refresh()
  } catch (reason) {
    dialogError.value = reason instanceof Error ? reason.message : '保存失败，请稍后重试。'
  } finally {
    saving.value = false
  }
}

async function setActive(row: Question, value: string | number | boolean) {
  if (changing.value.has(row.id)) return
  changing.value.add(row.id)
  try {
    const saved = await adminApi.updateQuestion(row.id, { active: Boolean(value) })
    row.active = saved.active
    ElMessage.success(saved.active ? '问题已启用' : '问题已停用')
  } catch (reason) {
    ElMessage.error(reason instanceof Error ? reason.message : '状态更新失败，请重试。')
  } finally {
    changing.value.delete(row.id)
  }
}
</script>

<template>
  <div>
    <PageHeading title="每日题库" description="用一个好问题，让两个人每天多了解彼此一点。" eyebrow="共赴山海手记 / 内容运营">
      <el-button :icon="Refresh" :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="primary" :icon="Plus" @click="edit()">添加问题</el-button>
    </PageHeading>
    <div class="question-guide"><span class="guide-icon"><el-icon><ChatDotRound /></el-icon></span><div><strong>适合认真听，也适合轻松聊</strong><p>准备关于旅行、日常、偏好和共同期待的原创问题。只有启用的问题会进入每日互动。</p></div><span class="active-count" v-if="data">{{ activeCount }} 个已启用</span></div>
    <LoadError v-if="error" :message="error" @retry="refresh" />
    <section v-else class="surface table-panel" :aria-busy="loading">
      <div class="table-toolbar">
        <div><strong>全部问题</strong><span class="count-tag">{{ data ? data.total : '—' }}</span></div>
        <div class="table-filters"><el-select v-model="status" aria-label="按启用状态筛选" class="status-filter"><el-option label="全部状态" value="all" /><el-option label="已启用" value="active" /><el-option label="已停用" value="inactive" /></el-select><el-input v-model="query" :prefix-icon="Search" placeholder="搜索问题内容" aria-label="搜索问题内容" clearable class="table-search" /></div>
      </div>
      <el-table v-loading="loading" :data="filtered" row-key="id" stripe :empty-text="loading ? '正在加载…' : query || status !== 'all' ? '没有匹配的问题，调整筛选条件后重试。' : '题库还是空的，点击“添加问题”准备第一个话题。'">
        <el-table-column label="问题" min-width="350"><template #default="{ row }"><p class="question-text">{{ row.text }}</p><span class="id-text question-id">{{ row.id }}</span></template></el-table-column>
        <el-table-column label="启用状态" width="150"><template #default="{ row }"><el-switch :model-value="row.active" :loading="changing.has(row.id)" :disabled="changing.has(row.id)" active-text="启用" :aria-label="`问题 ${row.id} 的启用状态`" @change="(value: string | number | boolean) => setActive(row, value)" /></template></el-table-column>
        <el-table-column label="操作" width="110" fixed="right"><template #default="{ row }"><el-button type="primary" link :icon="Edit" @click="edit(row)">编辑</el-button></template></el-table-column>
      </el-table>
      <div class="table-footer"><span>显示 {{ filtered.length }} 个问题</span><span>停用后不再用于新的每日互动</span></div>
    </section>

    <el-dialog v-model="dialogOpen" :title="form.id ? '编辑问题' : '添加问题'" width="min(560px, calc(100vw - 32px))" :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving">
      <el-alert v-if="dialogError" :title="dialogError" type="error" :closable="false" show-icon class="dialog-alert" role="alert" />
      <form id="question-form" @submit.prevent="save">
        <label for="question-text" class="form-label">问题内容</label>
        <el-input id="question-text" v-model="form.text" type="textarea" :rows="5" maxlength="500" show-word-limit placeholder="例如：如果下次旅行只能选一个地方，你最想和我去哪儿？" :disabled="saving" required />
        <div class="form-switch-row"><div><label for="question-active">启用这个问题</label><p>启用后可用于每日互动</p></div><el-switch id="question-active" v-model="form.active" :disabled="saving" /></div>
      </form>
      <template #footer><el-button :disabled="saving" @click="dialogOpen = false">取消</el-button><el-button type="primary" native-type="submit" form="question-form" :loading="saving" :disabled="!form.text.trim()">{{ form.id ? '保存修改' : '添加问题' }}</el-button></template>
    </el-dialog>
  </div>
</template>
