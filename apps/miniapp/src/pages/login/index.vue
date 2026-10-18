<template>
  <view class="page login-page">
    <image class="brand-mark" src="/static/brand-avatar.png" mode="aspectFit" aria-label="共赴山海手记品牌图标" />
    <text class="eyebrow">给两个人的旅行手记</text><view class="title login-title">共赴山海手记</view>
    <view class="login-quote serif">世界很大，<br/>想把和你走过的，<br/>都好好记住。</view>
    <view class="login-rule"/><view class="subtitle">地图里的每一站，都是时间里的某一天。</view>
    <view v-if="error" class="error">{{error}}</view>
    <!-- #ifdef MP-WEIXIN -->
    <button class="primary space-top" :loading="busy" :disabled="busy||NEEDS_API_CONFIG" @tap="wechatLogin">微信登录，开始记录</button>
    <!-- #endif -->
    <!-- #ifdef H5 -->
    <view v-if="!DEV_LOGIN_ENABLED" class="card space-top">请在微信小程序中登录，继续记录共同的旅行与日常。</view>
    <!-- #endif -->
    <view v-if="DEV_LOGIN_ENABLED" class="card dev-card">
      <text class="caption">本地开发体验</text><view class="help">使用不同标识创建两位体验者，可验证邀请绑定与共享手记。</view>
      <view class="field space-top"><text class="label">体验者标识</text><input v-model="identity" class="input" placeholder="输入固定标识，下次用它登录" maxlength="100" /></view>
      <view class="field"><text class="label">怎么称呼你</text><input v-model="nickname" class="input" placeholder="你的昵称" maxlength="40" /></view>
      <button class="primary" :loading="busy" :disabled="busy||!identity.trim()" @tap="devLogin">进入我的手记</button>
    </view>
    <view v-if="NEEDS_API_CONFIG" class="error">服务地址尚未配置，当前页面仅展示界面。</view>
    <text class="login-foot">默认只属于自己。邀请对方以后，再决定哪些一起看。</text>
  </view>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { api, rememberToken, refreshContext, state, message, DEV_LOGIN_ENABLED, NEEDS_API_CONFIG } from '../../lib/api'
import type { User } from '../../lib/types'
const identity=ref(''),nickname=ref(''),error=ref(''),busy=ref(false)
onShow(()=>{if(state.token)uni.switchTab({url:'/pages/map/index'})})
async function login(path:string,data:unknown){busy.value=true;error.value='';try{const result=await api<{access_token:string;user:User}>(path,'POST',data);rememberToken(result.access_token);await refreshContext();uni.switchTab({url:'/pages/map/index'})}catch(e){error.value=message(e)}finally{busy.value=false}}
function devLogin(){if(DEV_LOGIN_ENABLED&&identity.value.trim())login('/auth/dev-login',{identity:identity.value.trim(),nickname:nickname.value.trim()||undefined})}
function wechatLogin(){busy.value=true;error.value='';uni.login({provider:'weixin',success:r=>{if(!r.code){busy.value=false;error.value='微信未返回登录凭证，请重试';return}login('/auth/wechat-login',{code:r.code})},fail:()=>{busy.value=false;error.value='微信登录未完成，请重试'}})}
</script>
<style scoped>
.login-page{padding-top:90rpx}.brand-mark{display:block;width:116rpx;height:116rpx;margin-bottom:42rpx;border-radius:28rpx}.login-title{font-size:76rpx;margin:20rpx 0 34rpx;letter-spacing:8rpx}.login-quote{font-size:42rpx;line-height:1.75}.login-rule{width:70rpx;height:3rpx;background:#E2917D;margin:36rpx 0}.dev-card{margin-top:48rpx}.login-foot{display:block;margin-top:30rpx;color:#7E929C;font-size:23rpx;text-align:center}
</style>
