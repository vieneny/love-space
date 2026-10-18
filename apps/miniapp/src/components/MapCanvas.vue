<template>
  <view class="map-frame">
    <!-- #ifdef MP-WEIXIN -->
    <map id="footprint-map" class="native-map" :latitude="center.latitude" :longitude="center.longitude" :scale="visible.length===1?10:3" :markers="markers" :polyline="lines" :include-points="fitPoints" :show-location="false" @tap="nativeTap" @markertap="markerTap" />
    <!-- #endif -->
    <!-- #ifdef H5 -->
    <view class="atlas" @tap="atlasTap">
      <view class="atlas-graticule" />
      <text class="axis north">90°N</text><text class="axis west">180°W</text><text class="axis east">180°E</text><text class="axis equator">赤道</text>
      <view v-for="(item,index) in points" :key="item.id" class="atlas-pin" :style="pinStyle(item)" @tap.stop="emit('select',item)"><text>{{index+1}}</text></view>
      <view v-if="pickPoint" class="atlas-pin picked" :style="{left:`${(pickPoint.longitude+180)/360*100}%`,top:`${(90-pickPoint.latitude)/180*100}%`}"><text>＋</text></view>
      <view v-if="!points.length&&!pickPoint" class="atlas-empty">{{pickable?'轻点坐标网格，补上这一站':'把走过的地方，慢慢连成我们的故事'}}</view>
    </view>
    <view class="map-note">地点分布示意 · 不是导航底图。微信端使用原生地图。</view>
    <!-- #endif -->
    <view v-if="pickable" class="map-instruction">点按地图标记位置；也可以在下方填写经纬度。</view>
    <view v-if="hiddenCount" class="map-note">{{hiddenCount}} 个原始 GPS 地点等待坐标校验，手记已保留。</view>
    <view v-if="showOrder&&crossesDateLine" class="map-note">跨日期变更线的地点保留，地点连线分段显示。</view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref, getCurrentInstance } from 'vue'
import type { Memory } from '../lib/types'
const props = withDefaults(defineProps<{ points: Memory[]; pickable?: boolean; showOrder?: boolean; pickPoint?: { latitude:number; longitude:number } | null }>(),{pickable:false,showOrder:false,pickPoint:null})
const emit = defineEmits<{ select:[item:Memory]; pick:[point:{latitude:number;longitude:number}] }>()
// Native WeChat's documented CRS is GCJ-02. Do not blindly offset imported WGS84
// points in China. Abroad, preserve originals and verify real-device rendering.
const visible = computed(()=>props.points.filter(p=>p.place?.coordinate_system==='gcj02'||(p.place?.coordinate_system==='wgs84'&&p.place.country_code&&!['CN','CHN'].includes(p.place.country_code.toUpperCase()))))
const hiddenCount=computed(()=>props.points.length-visible.value.length)
const center=computed(()=>props.pickPoint||{latitude:visible.value[0]?.place?.latitude??30,longitude:visible.value[0]?.place?.longitude??105})
const fitPoints=computed(()=>props.pickPoint?[props.pickPoint]:visible.value.map(p=>({latitude:Number(p.place!.latitude),longitude:Number(p.place!.longitude)})))
const markers=computed(()=>[...visible.value.map((m,i)=>({id:i+1,latitude:Number(m.place!.latitude),longitude:Number(m.place!.longitude),iconPath:'/static/pin-sea.png',width:28,height:36,callout:{content:`${i+1} · ${m.title}`,display:'BYCLICK',color:'#233F4B',bgColor:'#FFFFFF',padding:10,borderRadius:8}})),...(props.pickPoint?[{id:0,latitude:props.pickPoint.latitude,longitude:props.pickPoint.longitude,iconPath:'/static/pin-sea.png',width:28,height:36,callout:{content:'选中的位置',display:'ALWAYS',color:'#233F4B',bgColor:'#FFFFFF',padding:8,borderRadius:8}}]:[])])
const crossesDateLine=computed(()=>fitPoints.value.some((point,index)=>index>0&&Math.abs(point.longitude-fitPoints.value[index-1].longitude)>180))
const lines=computed(()=>{
  if(!props.showOrder)return []
  const segments:{points:{latitude:number;longitude:number}[];color:string;width:number;dottedLine:boolean}[]=[]
  for(let i=1;i<fitPoints.value.length;i++){
    const previous=fitPoints.value[i-1],current=fitPoints.value[i]
    if(Math.abs(current.longitude-previous.longitude)>180)continue
    segments.push({points:[previous,current],color:'#477A68AA',width:3,dottedLine:true})
  }
  return segments
})
function markerTap(e:{detail:{markerId:number}}){const item=visible.value[e.detail.markerId-1];if(item)emit('select',item)}
function nativeTap(e:{detail:{latitude?:number;longitude?:number}}){if(props.pickable&&typeof e.detail.latitude==='number'&&typeof e.detail.longitude==='number')emit('pick',{latitude:e.detail.latitude,longitude:e.detail.longitude})}
function pinStyle(m:Memory){return{left:`${(Number(m.place?.longitude)+180)/360*100}%`,top:`${(90-Number(m.place?.latitude))/180*100}%`}}
const tapping=ref(false)
const instance=getCurrentInstance()
function atlasTap(e:any){
  if(!props.pickable||tapping.value)return
  tapping.value=true
  uni.createSelectorQuery().in(instance?.proxy as any).select('.atlas').boundingClientRect((rect:any)=>{
    tapping.value=false;if(!rect)return
    const x=e.detail?.x??e.changedTouches?.[0]?.clientX??e.touches?.[0]?.clientX
    const y=e.detail?.y??e.changedTouches?.[0]?.clientY??e.touches?.[0]?.clientY
    if(typeof x!=='number'||typeof y!=='number')return
    emit('pick',{longitude:Number((Math.max(0,Math.min(1,(x-rect.left)/rect.width))*360-180).toFixed(6)),latitude:Number((90-Math.max(0,Math.min(1,(y-rect.top)/rect.height))*180).toFixed(6))})
  }).exec()
}
</script>
<style scoped>
.map-frame{border-radius:24rpx;overflow:hidden;background:#E8F0F3;border:1rpx solid #D8E5EB}.native-map{width:100%;height:590rpx}.atlas{height:490rpx;position:relative;overflow:hidden;background:#E7F0F3}.atlas-graticule{position:absolute;inset:0;background-image:linear-gradient(to right,rgba(36,100,122,.1) 1px,transparent 1px),linear-gradient(to bottom,rgba(36,100,122,.1) 1px,transparent 1px);background-size:16.666% 25%}.atlas-graticule::after{content:'';position:absolute;top:50%;left:0;right:0;border-top:1rpx dashed #94B6C3}.axis{position:absolute;font-size:17rpx;color:#88A5B2}.north{top:12rpx;left:12rpx}.west{left:12rpx;bottom:12rpx}.east{right:12rpx;bottom:12rpx}.equator{left:12rpx;top:51%}.atlas-empty{position:absolute;top:44%;left:15%;right:15%;text-align:center;color:#648692;font-size:25rpx;background:rgba(245,248,250,.8);padding:20rpx;border-radius:12rpx}.atlas-pin{position:absolute;transform:translate(-50%,-50%);width:46rpx;height:46rpx;border-radius:50% 50% 50% 5%;background:#24647A;box-shadow:0 3rpx 10rpx #769CAC;color:white;text-align:center;line-height:46rpx;font-size:22rpx;z-index:2}.picked{background:#E2917D}.map-note,.map-instruction{padding:14rpx 20rpx;color:#708D9A;background:#EDF4F6;font-size:22rpx}.map-instruction{color:#24647A}
</style>
