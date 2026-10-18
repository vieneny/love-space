import { onBeforeUnmount, ref, shallowRef } from 'vue'

export function useAsyncData<T>(loader: () => Promise<T>) {
  const data = shallowRef<T>()
  const loading = ref(false)
  const error = ref('')
  let revision = 0
  onBeforeUnmount(() => { revision += 1 })

  async function refresh() {
    const current = ++revision
    loading.value = true
    error.value = ''
    try {
      const result = await loader()
      if (current === revision) data.value = result
    } catch (reason) {
      if (current === revision) error.value = reason instanceof Error ? reason.message : '加载失败，请稍后重试。'
    } finally {
      if (current === revision) loading.value = false
    }
  }
  return { data, loading, error, refresh }
}
