<template>
  <view class="page"><view v-if="loading" class="loading">正在翻开旅行…</view><view v-if="error" class="error">{{error}}<text class="link" @tap="load"> · 重试</text></view><view v-if="trip"><text class="eyebrow">一起出发 / TRAVEL NOTES</text><view class="title">{{trip.title}}</view><view class="caption serif">{{trip.start_date||'出发日待定'}}<text v-if="trip.end_date"> — {{trip.end_date}}</text></view><view v-if="trip.description" class="card content space-top">{{trip.description}}</view>
    <view class="row between section-title"><text>沿途的回忆</text><button class="primary small" @tap="add">＋ 写手记</button></view><text class="help">{{trip.visibility==='private'?'私人旅行':'共享旅行'}} · {{state.scope==='personal'?'显示我写的手记':'显示当前空间共享手记'}}</text>
    <MapCanvas v-if="mapped.length" class="space-top" :points="mapped" @select="openMemory($event.id)"/>
    <view class="space-top"><MemoryCard v-for="item in memories" :key="item.id" :item="item"/></view>
    <view v-if="!memories.length" class="empty"><view class="empty-title">这一程，故事还在继续</view><text>添加回忆时关联这段旅行，<br/>沿途的照片和地点就会收在这里。</text></view>
    <view v-if="trip.author_id===state.user?.id" class="actions"><button class="ghost" @tap="edit">编辑旅行</button><button class="danger" :loading="deleting" :disabled="deleting" @tap="remove">删除旅行</button></view>
  </view></view>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import MapCanvas from '../../components/MapCanvas.vue'
import MemoryCard from '../../components/MemoryCard.vue'
import { api, state, ensureAuth, refreshContext, message, query, openMemory, confirm, toast } from '../../lib/api'
import type { Memory, Trip, List } from '../../lib/types'
const id=ref(''),trip=ref<Trip|null>(null),memories=ref<Memory[]>([]),loading=ref(true),deleting=ref(false),error=ref('')
const mapped=computed(()=>memories.value.filter(m=>m.place?.latitude!=null&&m.place?.longitude!=null))
onLoad(o=>{id.value=String(o?.id||'')});onShow(load)
async function load(){if(!ensureAuth()||!id.value)return;loading.value=true;error.value='';trip.value=null;memories.value=[];try{await refreshContext();trip.value=await api<Trip>(`/trips/${encodeURIComponent(id.value)}`);const r=await api<List<Memory>>('/memories'+query({scope:trip.value.visibility==='private'?'personal':state.scope,trip_id:id.value}));memories.value=r.items.sort((a,b)=>b.occurred_on.localeCompare(a.occurred_on))}catch(e){error.value=message(e)}finally{loading.value=false}}
function add(){uni.navigateTo({url:`/pages/memory/edit?trip_id=${encodeURIComponent(id.value)}&kind=travel`})}function edit(){uni.navigateTo({url:`/pages/trips/edit?id=${encodeURIComponent(id.value)}`})}
async function remove(){if(deleting.value||!await confirm('删除这段旅行？','旅行中的手记会保留，并解除与这段旅行的关联。'))return;deleting.value=true;try{await api(`/trips/${encodeURIComponent(id.value)}`,'DELETE');toast('旅行已删除');uni.switchTab({url:'/pages/trips/index'})}catch(e){error.value=message(e)}finally{deleting.value=false}}
</script>
