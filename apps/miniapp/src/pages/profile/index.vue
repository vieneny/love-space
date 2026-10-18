<template>
  <view class="page"><text class="eyebrow">共赴山海手记 / OUR SPACE</text><view class="title">我们，慢慢来。</view><view v-if="error" class="error">{{error}}<text class="link" @tap="load"> · 重新读取</text></view><view v-if="loading" class="loading">正在打开空间…</view>
    <view v-if="state.user" class="card row"><view class="avatar serif">{{state.user.nickname.slice(0,1)||'我'}}</view><view class="grow"><view class="section-title user-name">{{state.user.nickname}}</view><text class="muted">每一段时光，都可以从今天开始记录。</text></view></view>
    <view v-if="!loading&&!state.space">
      <view class="card"><text class="caption">把两个人的时光，收在一起</text><view class="section-title serif">创建你们的双人空间</view><view class="field"><text class="label">空间名称</text><input v-model="spaceTitle" class="input" placeholder="比如：我们的山海手记" maxlength="120"/></view><view class="field"><text class="label">故事开始的日期（选填）</text><picker mode="date" :value="startDate||undefined" @change="startDate=$event.detail.value"><view class="picker">{{startDate||'先留空，之后慢慢补齐'}}</view></picker></view><button class="primary" :loading="working" :disabled="working||!spaceTitle.trim()" @tap="saveSpace">创建空间</button><view class="help">创建后生成邀请码，把它交给想一起记录的人。</view></view>
      <view class="card"><view class="section-title">已经收到邀请？</view><view class="field"><input v-model="joinCode" class="input" placeholder="输入对方的邀请码" maxlength="64"/></view><button class="secondary" :loading="working" :disabled="working||!joinCode.trim()" @tap="join">加入对方的空间</button></view>
    </view>
    <view v-if="!loading&&state.space" class="card space-card"><text class="caption">我们的双人空间</text><view class="space-title serif">{{state.space.title}}</view><view v-if="state.space.start_date" class="muted">故事从 {{state.space.start_date.replace(/-/g,'.')}} 开始</view><view class="members"><view v-for="member in state.space.members" :key="member.id" class="member"><view class="avatar member-avatar serif">{{member.nickname.slice(0,1)}}</view><text>{{member.nickname}}</text></view><view v-if="state.space.members.length<2" class="member awaiting"><view class="avatar member-avatar">＋</view><text>等你来</text></view></view>
      <button v-if="state.space.members.length<2" class="primary" :loading="working" :disabled="working" @tap="invite">生成一次性邀请码</button>
      <view v-if="invitation" class="invitation"><text class="caption">把这串邀请码交给对方</text><view class="invite-code serif">{{invitation.code}}</view><view v-if="invitationExpiry" class="help">有效期至 {{invitationExpiry}}（手机本地时间）</view><view class="help">一次性使用，生成后 30 分钟内有效。</view><button class="small ghost space-top" @tap="copyInvite">复制邀请码</button></view>
      <view class="divider"/><view class="row between"><text class="link" @tap="editingSpace=!editingSpace">{{editingSpace?'收起设置':'编辑空间'}}</text><text class="muted" @tap="unbind">解除绑定</text></view>
      <view v-if="editingSpace" class="space-top"><view class="field"><text class="label">空间名称</text><input v-model="spaceTitle" class="input" maxlength="120"/></view><view class="field"><text class="label">故事开始的日期</text><picker mode="date" :value="startDate||undefined" @change="startDate=$event.detail.value"><view class="picker">{{startDate||'选择日期'}}</view></picker><text v-if="startDate" class="help link" @tap="startDate=null">清除日期</text></view><button class="primary" :loading="working" :disabled="working||!spaceTitle.trim()" @tap="saveSpace">保存空间设置</button></view>
    </view>
    <view class="card privacy-card"><text class="caption">关于手记的可见范围</text><view class="privacy-line"><text class="privacy-dot"/><text>「仅自己」的记录只有作者可以查看。</text></view><view class="privacy-line"><text class="privacy-dot shared-dot"/><text>「共享」的记录对当前双人空间的两位成员可见。</text></view><view class="privacy-line"><text class="privacy-dot"/><text>解绑后保留自己写下的内容，对方的内容不再可见；新的故事会使用新的空间。</text></view></view>
    <view class="card"><view class="section-title">有个想法，想说给我们听</view><textarea v-model="feedback" class="textarea" placeholder="哪里不顺手，或下一次希望记录什么？" maxlength="5000"/><button class="ghost space-top" :loading="working" :disabled="working||!feedback.trim()" @tap="sendFeedback">发送反馈</button></view>
    <button class="ghost" :disabled="working" @tap="signOut">退出登录</button><view class="version serif">共赴山海手记 · v0.1.0</view>
  </view>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { api, state, ensureAuth, refreshContext, message, toast, confirm, logout, setScope } from '../../lib/api'
const loading=ref(false),working=ref(false),error=ref(''),spaceTitle=ref('我们的旅行手记'),startDate=ref<string|null>(null),joinCode=ref(''),editingSpace=ref(false),feedback=ref(''),invitation=ref<{code:string;expires_at:string}|null>(null)
const invitationExpiry=computed(()=>{
  const raw=invitation.value?.expires_at?.trim();if(!raw)return ''
  // The API's naive timestamps are UTC, not the phone's local wall time.
  const iso=raw.replace(' ','T').replace(/(\.\d{3})\d+/,'$1')
  const date=new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso)?iso:`${iso}Z`)
  if(Number.isNaN(date.getTime()))return ''
  const pad=(n:number)=>String(n).padStart(2,'0')
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
})
async function load(){if(!ensureAuth())return;loading.value=true;error.value='';invitation.value=null;try{await refreshContext();spaceTitle.value=state.space?.title||'我们的旅行手记';startDate.value=state.space?.start_date||null}catch(e){error.value=message(e)}finally{loading.value=false}}
async function perform(action:()=>Promise<void>){if(working.value)return;working.value=true;error.value='';try{await action()}catch(e){error.value=message(e)}finally{working.value=false}}
async function saveSpace(){await perform(async()=>{await api(state.space?'/spaces/current':'/spaces',state.space?'PATCH':'POST',{title:spaceTitle.value.trim(),start_date:startDate.value});await refreshContext();editingSpace.value=false;toast('空间已保存')})}
async function join(){await perform(async()=>{await api('/spaces/join','POST',{code:joinCode.value.trim()});joinCode.value='';await load();setScope('shared');toast('已经加入，开始一起记录吧')})}
async function invite(){await perform(async()=>{invitation.value=await api('/spaces/invitations','POST')})}
function copyInvite(){if(invitation.value)uni.setClipboardData({data:invitation.value.code,fail:()=>toast('复制未完成，请手动复制邀请码')})}
async function unbind(){if(working.value||!await confirm('解除双人空间绑定？','这会归档整个空间并解除双方绑定。你仍可查看自己写的内容，对方的内容将不再可见。之后的新关系会创建新的空间。'))return;await perform(async()=>{await api('/spaces/unbind','POST');setScope('personal');invitation.value=null;await load();toast('双人空间已归档并解除绑定')})}
async function sendFeedback(){await perform(async()=>{await api('/feedback','POST',{content:feedback.value.trim()});feedback.value='';toast('反馈已收到，谢谢你')})}
async function signOut(){if(await confirm('退出当前账号？','手记保存在服务端，下次登录后可继续查看。'))logout()}onShow(load)
</script>
<style scoped>
.avatar{width:88rpx;height:88rpx;background:#E8F0F3;color:#24647A;display:flex;justify-content:center;align-items:center;font-size:38rpx;border-radius:50%;flex-shrink:0}.user-name{margin:0 0 8rpx}.space-card{padding:34rpx}.space-title{font-size:43rpx;line-height:1.4;margin:15rpx 0}.members{display:flex;justify-content:center;gap:80rpx;padding:36rpx 0}.member{display:flex;flex-direction:column;align-items:center;gap:12rpx;font-size:25rpx}.member-avatar{width:100rpx;height:100rpx}.awaiting{color:#7E929C}.awaiting .avatar{background:#F4F7F8;border:1rpx dashed #C6D9E1}.invitation{background:#F2F7F8;border-radius:18rpx;padding:28rpx;text-align:center;margin-top:22rpx}.invite-code{font-size:49rpx;letter-spacing:5rpx;color:#24647A;overflow-wrap:anywhere;margin:18rpx 0}.privacy-line{display:flex;gap:16rpx;align-items:baseline;font-size:25rpx;margin-top:22rpx;color:#6E838D}.privacy-dot{width:10rpx;height:10rpx;display:inline-block;border-radius:50%;background:#E2917D;flex-shrink:0}.shared-dot{background:#477A68}.version{margin:35rpx 0 15rpx;text-align:center;color:#92A4AC;font-size:25rpx;letter-spacing:3rpx}
</style>
