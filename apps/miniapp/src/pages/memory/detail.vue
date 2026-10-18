<template>
  <view class="page">
    <view v-if="loading" class="loading">正在打开这一页…</view><view v-if="error" class="error">{{error}}<text class="link" @tap="load"> · 重试</text></view>
    <view v-if="item">
      <text class="eyebrow">{{kindNames[item.kind]}} / {{item.occurred_on.replace(/-/g,'.')}}</text><view class="title">{{item.title}}</view>
      <view class="row between space-bottom"><text class="muted">{{item.author_name}}</text><text class="badge">{{item.visibility==='private'?'仅自己':'双人共享'}}</text></view>
      <view v-if="item.photos?.length" class="photo-story"><image v-for="(photo,index) in item.photos" :key="photo.id" class="story-photo" :src="photoUrl(photo.url)" mode="widthFix" @tap="preview(index)"/></view>
      <view v-if="item.content" class="story-content content serif">{{item.content}}</view>
      <view v-if="item.place" class="card space-top"><text class="caption">这一天，在这里</text><view class="section-title">{{item.place.name||item.place.city}}</view><view class="muted">{{[item.place.country_name,item.place.city].filter(Boolean).join(' · ')}}</view><view v-if="item.place.latitude!=null" class="help">{{item.place.latitude}}, {{item.place.longitude}} · {{item.place.coordinate_system.toUpperCase()}}</view><view v-if="item.place.timezone" class="help">{{item.place.timezone}}</view></view>
      <view v-if="item.trip_id" class="card row between" @tap="openTrip"><text>查看关联旅行</text><text class="link">→</text></view>
      <view v-if="item.author_id===state.user?.id" class="actions"><button class="ghost" @tap="edit">编辑手记</button><button class="danger" :loading="deleting" :disabled="deleting" @tap="remove">删除</button></view>
      <view class="help space-top">发生于 {{item.occurred_on}} · {{item.visibility==='private'?'这一页只属于你':'这一页与当前空间的对方共享'}}</view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { api, state, ensureAuth, refreshContext, message, photoUrl, kindNames, confirm, toast } from '../../lib/api'
import type { Memory } from '../../lib/types'
const id=ref(''),item=ref<Memory|null>(null),loading=ref(true),error=ref(''),deleting=ref(false)
onLoad(o=>{id.value=String(o?.id||'')});onShow(load)
async function load(){if(!ensureAuth()||!id.value)return;loading.value=true;error.value='';item.value=null;try{await refreshContext();item.value=await api<Memory>(`/memories/${encodeURIComponent(id.value)}`)}catch(e){error.value=message(e)}finally{loading.value=false}}
function preview(index:number){uni.previewImage({current:index,urls:item.value!.photos.map(p=>photoUrl(p.url))})}
function edit(){uni.navigateTo({url:`/pages/memory/edit?id=${encodeURIComponent(id.value)}`})}
function openTrip(){uni.navigateTo({url:`/pages/trips/detail?id=${encodeURIComponent(item.value!.trip_id!)}`})}
async function remove(){if(deleting.value||!await confirm('删除这篇手记？','删除后将无法在手记和地图中查看。'))return;deleting.value=true;try{await api(`/memories/${encodeURIComponent(id.value)}`,'DELETE');toast('手记已删除');uni.switchTab({url:'/pages/timeline/index'})}catch(e){error.value=message(e)}finally{deleting.value=false}}
</script>
<style scoped>.story-photo{width:100%;border-radius:20rpx;margin-bottom:22rpx;background:#EAF0F3}.story-content{font-size:32rpx;line-height:1.95;margin-top:36rpx}</style>
