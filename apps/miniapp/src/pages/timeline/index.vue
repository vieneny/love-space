<template>
  <view class="page">
    <view class="header"><view><text class="eyebrow">共赴山海手记 / JOURNAL</text><view class="title">日子有迹可循。</view><text class="subtitle">旅行、大事、平凡的一天，都值得一页。</text></view></view>
    <ScopeSwitch @change="load" />
    <view class="chips space-bottom"><view v-for="k in kinds" :key="k.value" class="chip" :class="{active:kind===k.value}" @tap="kind=k.value;load()">{{k.label}}</view></view>
    <view class="form-row"><view class="field"><input v-model="year" class="input" placeholder="年份，如 2026" type="number" maxlength="4" @confirm="load"/></view><view class="field"><input v-model="country" class="input" placeholder="国家代码，如 CN" maxlength="3" @confirm="load"/></view><button class="small ghost filter-button" :disabled="loading" @tap="load">筛选</button></view>
    <view v-if="error" class="error">{{error}}<text class="link" @tap="load"> · 重试</text></view>
    <view v-if="loading" class="loading">正在翻开手记…</view>
    <MemoryCard v-for="item in items" :key="item.id" :item="item"/>
    <view v-if="!loading&&!items.length&&!error" class="empty"><view class="empty-title">这一页，留给值得记住的事</view><text>写下发生的日期，放进当时的照片。<br/>也可以先只写一句话。</text><button class="primary small" @tap="add">写第一篇手记</button></view>
    <button class="primary fab" @tap="add">＋ 写手记</button>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import ScopeSwitch from '../../components/ScopeSwitch.vue'
import MemoryCard from '../../components/MemoryCard.vue'
import { api, ensureAuth, refreshContext, state, query, message } from '../../lib/api'
import type { Memory, List } from '../../lib/types'
const items=ref<Memory[]>([]),loading=ref(false),error=ref(''),year=ref(''),kind=ref(''),country=ref('')
const kinds=[{value:'',label:'全部'},{value:'travel',label:'旅行'},{value:'milestone',label:'重要时刻'},{value:'daily',label:'日常'}]
let generation=0
async function load(){if(!ensureAuth())return;const g=++generation;loading.value=true;error.value='';try{await refreshContext();const r=await api<List<Memory>>('/memories'+query({scope:state.scope,year:year.value,kind:kind.value,country:country.value.trim().toUpperCase()}));if(g===generation)items.value=r.items.sort((a,b)=>b.occurred_on.localeCompare(a.occurred_on))}catch(e){if(g===generation){items.value=[];error.value=message(e)}}finally{if(g===generation)loading.value=false;uni.stopPullDownRefresh()}}
function add(){uni.navigateTo({url:'/pages/memory/edit'})}
onShow(load);onPullDownRefresh(load)
</script>
<style scoped>.filter-button{height:86rpx;flex-shrink:0;align-self:flex-start;margin-left:4rpx}</style>
