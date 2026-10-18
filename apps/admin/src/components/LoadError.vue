<script setup lang="ts">
defineProps<{ message: string }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="load-error" role="alert">
    <div><strong>暂时无法加载</strong><p>{{ message }}</p></div>
    <el-button @click="$emit('retry')">重新加载</el-button>
  </div>
</template>
