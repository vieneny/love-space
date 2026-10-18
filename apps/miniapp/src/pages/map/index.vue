<template>
  <view class="page">
    <view class="header"><view><text class="eyebrow">共赴山海手记 / FOOTPRINTS</text><view class="title">把时光，<br/>留在走过的地方。</view><text class="subtitle">{{state.space?.title||'从一个值得记住的地方开始'}}</text></view><text class="stamp">旅行手记</text></view>
    <ScopeSwitch @change="load" />
    <view class="row filters"><input v-model="year" class="input year-input" type="number" maxlength="4" placeholder="全部年份" @confirm="load"/><button class="small ghost" :disabled="loading" @tap="load">查看</button></view>
    <view v-if="error" class="error">{{error}}<text class="link" @tap="load"> · 重试</text></view>
    <view v-if="loading" class="loading">正在展开这张地图…</view>
    <MapCanvas :points="ordered" :show-order="showOrder" @select="selected=$event" />
    <view class="row between order-row"><view><text class="strong">地点顺序</text><view class="help">按记录日期连接，不代表实际行程轨迹。</view></view><switch :checked="showOrder" color="#477A68" @change="setOrder" /></view>
    <view v-if="stats" class="stats card"><view><text class="stat-number serif">{{stats.countries}}</text><text>国家 / 地区</text></view><view><text class="stat-number serif">{{stats.cities}}</text><text>城市</text></view><view><text class="stat-number serif">{{stats.places}}</text><text>地点</text></view><view><text class="stat-number serif">{{stats.visits}}</text><text>到访记录</text></view></view>
    <view v-if="selected" class="card selected-place" @tap="openMemory(selected.id)"><view class="row"><image v-if="selected.photos?.length" class="place-photo" :src="photoUrl(selected.photos[0].url)" mode="aspectFill"/><view class="grow"><text class="caption">{{selected.occurred_on}} · {{selected.place?.country_name||selected.place?.country_code}}</text><view class="section-title selected-title serif">{{selected.title}}</view><text class="muted">{{selected.place?.name||selected.place?.city}} →</text></view></view></view>
    <view v-if="!loading&&!items.length&&!error" class="empty"><view class="empty-title">下一站，从这里开始</view><text>给回忆添加地点，它就会出现在地图上。<br/>过去的旅行，也可以慢慢补齐。</text><button class="primary small" @tap="add">记录一个地方</button></view>
    <view v-if="items.length" class="section-title">地图上的手记</view>
    <view v-for="item in ordered" :key="item.id" class="footprint-row" @tap="openMemory(item.id)"><view class="footprint-date serif">{{item.occurred_on.slice(5).replace('-', '/')}}</view><view class="grow"><text class="strong">{{item.title}}</text><view class="muted">{{[item.place?.country_name,item.place?.city,item.place?.name].filter(Boolean).join(' · ')}}</view></view><text class="muted">↗</text></view>
    <button class="primary fab" @tap="add">＋ 记一站</button>
  </view>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import ScopeSwitch from '../../components/ScopeSwitch.vue'
import MapCanvas from '../../components/MapCanvas.vue'
import { api, ensureAuth, refreshContext, state, query, message, openMemory, photoUrl } from '../../lib/api'
import type { Memory, Footprints } from '../../lib/types'
const loading=ref(false),error=ref(''),year=ref(''),showOrder=ref(false),items=ref<Memory[]>([]),stats=ref<Footprints['stats']|null>(null),selected=ref<Memory|null>(null)
const ordered=computed(()=>[...items.value].sort((a,b)=>a.occurred_on.localeCompare(b.occurred_on)))
let generation=0
async function load(){if(!ensureAuth())return;const g=++generation;loading.value=true;error.value='';try{await refreshContext();const result=await api<Footprints>('/map/footprints'+query({scope:state.scope,year:year.value}));if(g!==generation)return;items.value=result.items;stats.value=result.stats;selected.value=null}catch(e){if(g===generation){items.value=[];stats.value=null;selected.value=null;error.value=message(e)}}finally{if(g===generation)loading.value=false}}
function add(){uni.navigateTo({url:'/pages/memory/edit?kind=travel'})}
function setOrder(event:any){showOrder.value=event.detail.value}
onShow(load)
</script>
<style scoped>
.filters{margin-bottom:22rpx}.year-input{height:68rpx;width:200rpx;font-size:24rpx;background:white}.order-row{margin:22rpx 0}.stats{display:flex;padding:28rpx 12rpx;justify-content:space-around}.stats>view{display:flex;align-items:center;flex-direction:column;color:#7E929C;font-size:21rpx}.stat-number{font-size:45rpx;color:#24647A;line-height:1.1;margin-bottom:8rpx}.selected-place{border-color:#D4E4E9}.place-photo{width:145rpx;height:160rpx;border-radius:12rpx}.selected-title{margin:8rpx 0;font-size:33rpx}.footprint-row{display:flex;align-items:center;gap:20rpx;padding:24rpx 0;border-bottom:1rpx solid #DFE9ED}.footprint-date{font-size:32rpx;color:#477A68;width:100rpx}
</style>
