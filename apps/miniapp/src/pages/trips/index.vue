<template>
  <view class="page"><text class="eyebrow">共赴山海手记 / TRAVEL NOTES</text><view class="title">下一次，<br/>还想和你出发。</view><text class="subtitle">从出发的念头，到沿途的每一个瞬间。</text><ScopeSwitch @change="load"/>
    <view v-if="error" class="error">{{error}}<text class="link" @tap="load"> · 重试</text></view><view v-if="loading" class="loading">正在整理行囊…</view>
    <view v-for="(trip,index) in items" :key="trip.id" class="trip-card card" @tap="open(trip.id)"><view class="row between"><text class="caption">旅行手记</text><text class="badge">{{trip.visibility==='private'?'仅自己':'双人共享'}}</text></view><view class="trip-name serif">{{trip.title}}</view><view class="trip-date serif">{{trip.start_date?.replace(/-/g,'.')||'出发日待定'}}<text v-if="trip.end_date"> — {{trip.end_date.replace(/-/g,'.')}}</text></view><view v-if="trip.description" class="trip-description">{{trip.description}}</view><view class="ticket-line"/><view class="row between"><text class="muted">{{trip.memory_count}} 篇回忆</text><text class="link">翻开这段旅行 ↗</text></view></view>
    <view v-if="!loading&&!items.length&&!error" class="empty"><view class="empty-title">给下一段旅行留个位置</view><text>还没定好出发日也没关系。<br/>先写下想去哪里，往后再补齐。</text><button class="primary small" @tap="add">新建一段旅行</button></view>
    <button class="primary fab" @tap="add">＋ 一起出发</button>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import ScopeSwitch from '../../components/ScopeSwitch.vue'
import { api, ensureAuth, refreshContext, state, message, query } from '../../lib/api'
import type { Trip, List } from '../../lib/types'
const items=ref<Trip[]>([]),loading=ref(false),error=ref('');let generation=0
async function load(){if(!ensureAuth())return;const g=++generation;loading.value=true;error.value='';try{await refreshContext();const r=await api<List<Trip>>('/trips'+query({scope:state.scope}));if(g===generation)items.value=r.items}catch(e){if(g===generation){items.value=[];error.value=message(e)}}finally{if(g===generation)loading.value=false}}
function open(id:string){uni.navigateTo({url:`/pages/trips/detail?id=${encodeURIComponent(id)}`})}function add(){uni.navigateTo({url:'/pages/trips/edit'})}onShow(load)
</script>
<style scoped>.trip-card{padding:30rpx 32rpx;position:relative;overflow:hidden}.trip-card::before{content:'';position:absolute;width:9rpx;left:0;top:0;bottom:0;background:#477A68}.trip-name{font-size:44rpx;line-height:1.35;margin:24rpx 0 16rpx;font-weight:600}.trip-date{color:#477A68;font-size:26rpx}.trip-description{font-size:26rpx;color:#7E929C;margin-top:20rpx;white-space:pre-wrap}.ticket-line{border-top:1rpx dashed #C9DCE4;margin:30rpx -12rpx 23rpx}</style>
