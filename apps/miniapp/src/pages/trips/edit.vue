<template>
  <view class="page"><text class="eyebrow">TRAVEL NOTES / {{id?'编辑旅行':'准备出发'}}</text><view class="title">一段旅行的开始。</view><view v-if="error" class="error">{{error}}</view><view v-if="loading" class="loading">正在读取旅行…</view><view v-else class="card">
    <view class="field"><text class="label">旅行名称</text><input v-model="form.title" class="input" placeholder="这一程，想去哪里？" maxlength="120"/></view><view class="field"><text class="label">行前的小小期待</text><textarea v-model="form.description" class="textarea" placeholder="想看的一片海，想一起吃的一顿饭…" maxlength="10000"/></view>
    <view class="form-row"><view class="field"><text class="label">出发日期（选填）</text><picker mode="date" :value="form.start_date||undefined" @change="form.start_date=$event.detail.value"><view class="picker">{{form.start_date||'还没决定'}}</view></picker><text v-if="form.start_date" class="link help" @tap="form.start_date=null">清除日期</text></view><view class="field"><text class="label">结束日期（选填）</text><picker mode="date" :value="form.end_date||undefined" @change="form.end_date=$event.detail.value"><view class="picker">{{form.end_date||'还没决定'}}</view></picker><text v-if="form.end_date" class="link help" @tap="form.end_date=null">清除日期</text></view></view>
    <view class="field"><text class="label">谁可以看这段旅行</text><view class="chips"><view class="chip" :class="{active:form.visibility==='private'}" @tap="form.visibility='private'">仅自己</view><view class="chip" :class="{active:form.visibility==='shared'}" @tap="shared">与对方共享</view></view><view class="help">旅行和关联的手记需要使用相同的可见范围。</view></view>
    <view class="actions"><button class="ghost" :disabled="saving" @tap="back">取消</button><button class="primary" :loading="saving" :disabled="saving||!form.title.trim()" @tap="save">保存旅行</button></view>
  </view></view>
</template>
<script setup lang="ts">
import { ref, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api, state, ensureAuth, refreshContext, message, toast } from '../../lib/api'
import type { Trip, Visibility } from '../../lib/types'
const id=ref(''),loading=ref(true),saving=ref(false),error=ref(''),form=reactive({title:'',description:'',start_date:null as string|null,end_date:null as string|null,visibility:'private' as Visibility})
onLoad(async o=>{if(!ensureAuth())return;id.value=String(o?.id||'');try{await refreshContext();if(id.value){const t=await api<Trip>(`/trips/${encodeURIComponent(id.value)}`);if(t.author_id!==state.user?.id)throw new Error('只有创建者可以编辑这段旅行');Object.assign(form,{title:t.title,description:t.description,start_date:t.start_date,end_date:t.end_date,visibility:t.visibility})}}catch(e){error.value=message(e)}finally{loading.value=false}})
function shared(){if(!state.space){toast('先到「我们」创建或加入双人空间');return};form.visibility='shared'}
async function save(){if(saving.value)return;if(form.start_date&&form.end_date&&form.end_date<form.start_date){error.value='结束日期不能早于出发日期';return};saving.value=true;error.value='';try{const t=await api<Trip>(id.value?`/trips/${encodeURIComponent(id.value)}`:'/trips',id.value?'PATCH':'POST',{...form,title:form.title.trim()});toast('旅行已保存');uni.redirectTo({url:`/pages/trips/detail?id=${encodeURIComponent(t.id)}`})}catch(e){error.value=message(e)}finally{saving.value=false}}
function back(){uni.navigateBack({fail:()=>uni.switchTab({url:'/pages/trips/index'})})}
</script>
