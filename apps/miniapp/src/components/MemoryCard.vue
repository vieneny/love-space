<template>
  <view class="memory-card" role="button" @tap="openMemory(item.id)">
    <view class="memory-side"><text class="day serif">{{item.occurred_on.slice(8)}}</text><text class="month">{{item.occurred_on.slice(0,7).replace('-', '.')}}</text><view class="memory-dot" /></view>
    <view class="card memory-body"><image v-if="item.photos?.length" class="cover memory-cover" :src="photoUrl(item.photos[0].url)" mode="aspectFill" /><view class="row between"><text class="caption">{{kindNames[item.kind]}}</text><text v-if="item.visibility==='private'" class="muted">仅自己</text></view><view class="memory-title serif">{{item.title}}</view><view v-if="item.content" class="memory-content">{{item.content}}</view><view class="row between memory-meta"><text class="muted">{{item.place?.name || item.place?.city || '尚未添加地点'}}</text><text class="muted">{{item.author_name}}</text></view></view>
  </view>
</template>
<script setup lang="ts">
import { kindNames, photoUrl, openMemory } from '../lib/api'
import type { Memory } from '../lib/types'
defineProps<{ item: Memory }>()
</script>
<style scoped>
.memory-card{display:flex;gap:20rpx}.memory-side{width:90rpx;flex-shrink:0;text-align:center;position:relative;padding-top:6rpx}.memory-side::after{content:'';position:absolute;top:130rpx;bottom:0;left:44rpx;width:1rpx;background:#D8E5E9}.day{display:block;font-size:52rpx;line-height:1.1;color:#24647A}.month{font-size:19rpx;color:#7E929C;display:block;margin-top:10rpx}.memory-dot{width:12rpx;height:12rpx;border-radius:50%;background:#E2917D;margin:22rpx auto}.memory-body{flex:1;min-width:0}.memory-cover{height:300rpx;margin-bottom:20rpx}.memory-title{font-size:36rpx;font-weight:600;margin:12rpx 0}.memory-content{color:#6E838D;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;font-size:26rpx}.memory-meta{margin-top:22rpx;gap:10rpx}
</style>
