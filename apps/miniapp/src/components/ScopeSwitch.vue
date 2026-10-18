<template><view class="scope"><view class="scope-item" :class="{selected:state.scope==='personal'}" role="button" @tap="select('personal')">我的手记</view><view class="scope-item" :class="{selected:state.scope==='shared'}" role="button" @tap="select('shared')">我们的手记</view></view></template>
<script setup lang="ts">
import { state, setScope, toast } from '../lib/api'
import type { Scope } from '../lib/types'
const emit = defineEmits<{ change: [scope: Scope] }>()
function select(scope: Scope) { if (scope==='shared' && !state.space) { toast('先到「我们」创建或加入双人空间'); return }; setScope(scope); emit('change', scope) }
</script>
