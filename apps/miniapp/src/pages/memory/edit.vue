<template>
  <view class="page">
    <text class="eyebrow">一页手记 / {{id?'编辑回忆':'新的记录'}}</text><view class="title">把那天，写下来。</view>
    <view v-if="loading" class="loading">正在读取手记…</view>
    <view v-if="error" class="error">{{error}}</view>
    <view v-if="!loading" class="card">
      <view class="field"><text class="label">标题</text><input v-model="form.title" class="input" placeholder="给这一天一个名字" maxlength="120"/></view>
      <view class="form-row"><view class="field"><text class="label">发生日期</text><picker mode="date" :value="form.occurred_on" @change="form.occurred_on=$event.detail.value"><view class="picker">{{form.occurred_on}}</view></picker></view><view class="field"><text class="label">这一页属于</text><picker :range="kindLabels" :value="kindIndex" @change="form.kind=kindValues[Number($event.detail.value)]"><view class="picker">{{kindLabels[kindIndex]}}</view></picker></view></view>
      <view class="field"><text class="label">当时的故事</text><textarea v-model="form.content" class="textarea" placeholder="还记得那天的天气、说过的话，或一件很小的事吗？" maxlength="20000"/></view>
      <view class="field"><view class="row between"><text class="label">照片 · {{photos.length}} / 9</text><text class="caption">只放真实发生的瞬间</text></view><view class="photos"><view v-for="(photo,index) in photos" :key="photo.id" class="photo-cell"><image :src="photoUrl(photo.url)" mode="aspectFill" @tap="preview(index)"/><view class="remove-photo" @tap="photos.splice(index,1)">×</view></view><view v-if="photos.length<9" class="photo-add" @tap="choosePhotos"><text>{{uploading?'上传中…':'＋'}}</text><text v-if="!uploading">添加照片</text></view></view></view>
      <view class="field"><text class="label">谁可以看</text><view class="chips"><view class="chip" :class="{active:form.visibility==='private'}" @tap="visibility('private')">仅自己</view><view class="chip" :class="{active:form.visibility==='shared'}" @tap="visibility('shared')">与对方共享</view></view><view class="help">{{form.visibility==='private'?'这一页只出现在你的个人手记里。':'这一页对当前双人空间的两位成员可见。'}}</view></view>
      <view class="field"><text class="label">关联旅行</text><picker :range="tripOptions" range-key="title" :value="tripIndex" @change="form.trip_id=tripOptions[Number($event.detail.value)].id"><view class="picker">{{tripOptions[tripIndex]?.title||'不关联旅行'}}</view></picker></view>
      <view class="row between field"><view><text class="label">给回忆一个地点</text><text class="help">支持过去的旅行和海外地点补录</text></view><switch :checked="hasPlace" color="#477A68" @change="setHasPlace"/></view>
      <view v-if="hasPlace">
        <view class="field"><text class="label">地点名称</text><input v-model="place.name" class="input" placeholder="可以是小店、山顶，或你们自己的称呼" maxlength="200"/></view>
        <view class="form-row"><view class="field"><text class="label">国家 / 地区名称</text><input v-model="place.country_name" class="input" placeholder="如：中国 / 日本" maxlength="100"/></view><view class="field"><text class="label">国家 / 地区代码</text><input v-model="place.country_code" class="input" placeholder="如 CN / JP / US" maxlength="3"/></view></view>
        <view class="field"><text class="label">城市</text><input v-model="place.city" class="input" placeholder="城市名称" maxlength="100"/></view>
        <MapCanvas :points="[]" pickable :pick-point="pickPoint" @pick="pick"/>
        <view class="form-row space-top"><view class="field"><text class="label">纬度（−90 至 90）</text><input v-model="latitude" class="input" placeholder="例如 35.681236"/></view><view class="field"><text class="label">经度（−180 至 180）</text><input v-model="longitude" class="input" placeholder="例如 139.767125"/></view></view>
        <view class="field"><text class="label">坐标来源</text><view class="chips"><view class="chip" :class="{active:place.coordinate_system==='gcj02'}" @tap="place.coordinate_system='gcj02'">GCJ-02 · 微信 / 国内地图</view><view class="chip" :class="{active:place.coordinate_system==='wgs84'}" @tap="place.coordinate_system='wgs84'">WGS84 · GPS / 海外</view></view><view class="help">保留原始坐标。国内 GPS 坐标需要校验后再上地图；海外点位请核对地图显示。</view></view>
        <view class="field"><text class="label">地点时区（选填）</text><input v-model="place.timezone" class="input" placeholder="如 Asia/Tokyo、Europe/Paris" maxlength="80"/><text class="help">发生日期按你填写的当地日期保存，不会改成上传日期。</text></view>
      </view>
      <view class="actions"><button class="ghost" :disabled="saving||uploading" @tap="back">取消</button><button class="primary" :loading="saving" :disabled="saving||uploading||!form.title.trim()" @tap="save">保存这篇手记</button></view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import MapCanvas from '../../components/MapCanvas.vue'
import { api, ensureAuth, refreshContext, state, today, query, message, toast, photoUrl, upload } from '../../lib/api'
import type { Memory, Trip, List, Photo, Place, Visibility } from '../../lib/types'
const id=ref(''),loading=ref(true),error=ref(''),saving=ref(false),uploading=ref(false),hasPlace=ref(false),photos=ref<Photo[]>([]),trips=ref<Trip[]>([]),latitude=ref(''),longitude=ref('')
const form=reactive({title:'',content:'',occurred_on:today(),kind:'daily' as Memory['kind'],visibility:'private' as Visibility,trip_id:null as string|null})
const place=reactive<Place>({name:'',country_code:'',country_name:'',city:'',coordinate_system:'gcj02',timezone:''})
const kindLabels=['旅行','重要时刻','日常'],kindValues:Memory['kind'][]=['travel','milestone','daily']
const kindIndex=computed(()=>kindValues.indexOf(form.kind))
const tripOptions=computed(()=>[{id:null as string|null,title:'不关联旅行'},...trips.value.filter(t=>t.visibility===form.visibility).map(t=>({id:t.id,title:t.title}))])
const tripIndex=computed(()=>Math.max(0,tripOptions.value.findIndex(t=>t.id===form.trip_id)))
const pickPoint=computed(()=>latitude.value.trim()&&longitude.value.trim()&&Number.isFinite(Number(latitude.value))&&Number.isFinite(Number(longitude.value))?{latitude:Number(latitude.value),longitude:Number(longitude.value)}:null)
onLoad(async options=>{if(!ensureAuth())return;id.value=String(options?.id||'');try{await refreshContext();const mine=await api<List<Trip>>('/trips?scope=personal');let all=mine.items;if(state.space){const shared=await api<List<Trip>>('/trips?scope=shared');all=[...all,...shared.items]};trips.value=[...new Map(all.map(t=>[t.id,t])).values()];if(id.value){const m=await api<Memory>(`/memories/${encodeURIComponent(id.value)}`);if(m.author_id!==state.user?.id)throw new Error('只有作者可以编辑这篇手记');Object.assign(form,{title:m.title,content:m.content,occurred_on:m.occurred_on,kind:m.kind,visibility:m.visibility,trip_id:m.trip_id});photos.value=m.photos||[];if(m.place){hasPlace.value=true;Object.assign(place,m.place);latitude.value=m.place.latitude==null?'':String(m.place.latitude);longitude.value=m.place.longitude==null?'':String(m.place.longitude)}}else{if(kindValues.includes(options?.kind as Memory['kind']))form.kind=options!.kind as Memory['kind'];if(options?.trip_id){const t=trips.value.find(t=>t.id===options.trip_id);if(t){form.trip_id=t.id;form.visibility=t.visibility;form.kind='travel'}}}}catch(e){error.value=message(e)}finally{loading.value=false}})
function visibility(value:Visibility){if(value==='shared'&&!state.space){toast('先到「我们」创建或加入双人空间');return};form.visibility=value;if(!trips.value.some(t=>t.id===form.trip_id&&t.visibility===value))form.trip_id=null}
function setHasPlace(event:any){hasPlace.value=event.detail.value}
function pick(p:{latitude:number;longitude:number}){latitude.value=String(p.latitude);longitude.value=String(p.longitude)
  // #ifdef MP-WEIXIN
  place.coordinate_system='gcj02'
  // #endif
  // #ifdef H5
  place.coordinate_system='wgs84'
  // #endif
}
function preview(index:number){uni.previewImage({current:index,urls:photos.value.map(p=>photoUrl(p.url))})}
function choosePhotos(){if(uploading.value)return;uni.chooseImage({count:9-photos.value.length,sizeType:['original'],sourceType:['album','camera'],success:async r=>{uploading.value=true;error.value='';try{for(const path of r.tempFilePaths)photos.value.push(await upload(path))}catch(e){error.value=message(e)}finally{uploading.value=false}}})}
async function save(){if(saving.value||uploading.value)return;error.value='';let p:Place|null=null;if(hasPlace.value){if(Boolean(latitude.value.trim())!==Boolean(longitude.value.trim())){error.value='经度和纬度需要一起填写，或同时留空';return};p={...place,country_code:place.country_code.trim().toUpperCase()};if(latitude.value.trim()){const lat=Number(latitude.value),lng=Number(longitude.value);if(!Number.isFinite(lat)||!Number.isFinite(lng)||lat< -90||lat>90||lng< -180||lng>180){error.value='请填写有效的经纬度';return};p.latitude=lat;p.longitude=lng}else{p.latitude=null;p.longitude=null};if(!p.name.trim()&&!p.city.trim()&&p.latitude==null){error.value='请填写地点名称、城市或地图坐标';return}}
  saving.value=true;try{const m=await api<Memory>(id.value?`/memories/${encodeURIComponent(id.value)}`:'/memories',id.value?'PATCH':'POST',{...form,title:form.title.trim(),place:p,photo_ids:photos.value.map(p=>p.id)});toast('手记已保存');uni.redirectTo({url:`/pages/memory/detail?id=${encodeURIComponent(m.id)}`})}catch(e){error.value=message(e)}finally{saving.value=false}}
function back(){uni.navigateBack({fail:()=>uni.switchTab({url:'/pages/timeline/index'})})}
</script>
<style scoped>
.photos{display:flex;gap:14rpx;flex-wrap:wrap}.photo-cell,.photo-add{width:175rpx;height:175rpx;position:relative;border-radius:14rpx;overflow:hidden}.photo-cell image{width:100%;height:100%}.remove-photo{position:absolute;top:5rpx;right:5rpx;background:#233F4BAA;color:white;width:38rpx;height:38rpx;line-height:34rpx;text-align:center;border-radius:50%;font-size:30rpx}.photo-add{display:flex;align-items:center;justify-content:center;flex-direction:column;background:#F0F5F7;border:1rpx dashed #BDD2DC;color:#7E929C;font-size:22rpx}.photo-add>text:first-child{font-size:42rpx;color:#24647A}
</style>
