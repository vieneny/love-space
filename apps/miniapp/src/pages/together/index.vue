<template>
  <view class="page">
    <text class="eyebrow">共赴山海手记 / EVERYDAY TOGETHER</text><view class="title">一起，过好小日子。</view><text class="subtitle">把在乎放进日常，把想做的事慢慢实现。</text>
    <scroll-view scroll-x class="life-scroll"><view class="life-tabs"><view v-for="tab in tabs" :key="tab.key" class="life-tab" :class="{chosen:pane===tab.key}" @tap="change(tab.key)">{{tab.label}}</view></view></scroll-view>
    <view v-if="error" class="error">{{error}}<text class="link" @tap="load"> · 重试</text></view><view v-if="loading" class="loading">正在打开日常…</view>
    <view v-if="!loading&&!state.space&&pane!=='moods'" class="empty"><view class="empty-title">这些小事，想和你一起</view><text>创建或加入双人空间，<br/>就可以一起记纪念日、许愿和回答每日一问。</text><button class="primary small" @tap="profile">去邀请对方</button></view>
    <view v-if="!loading&&(state.space||pane==='moods')">
      <view v-if="pane==='anniversaries'">
        <view class="row between section-title"><text>值得记住的日子</text><button class="small primary" @tap="newEntry">＋ 新增</button></view>
        <view v-for="item in anniversaries" :key="item.id" class="card"><text class="caption">{{item.repeat_yearly?'每年的这一天':'只此一天'}}</text><view class="anniversary-date serif">{{item.date.replace(/-/g,'.')}}</view><view class="section-title anniversary-title serif">{{item.title}}</view><view class="row"><button class="small ghost" @tap="editAnniversary(item)">编辑</button><button class="small danger" :disabled="working" @tap="remove('anniversaries',item.id)">删除</button></view></view>
        <view v-if="!anniversaries.length&&!editor&&!error" class="empty"><view class="empty-title">第一次见面、牵手、出发…</view><text>有些日子，值得一直记得。</text></view>
      </view>
      <view v-if="pane==='wishes'">
        <view class="row between section-title"><text>想一起做的事</text><button class="small primary" @tap="newEntry">＋ 许个愿</button></view>
        <view v-for="item in wishes" :key="item.id" class="card wish-row"><button class="wish-check" :class="{done:item.completed}" :disabled="working" @tap="complete(item)">{{item.completed?'✓':'○'}}</button><view class="grow"><view class="strong" :class="{'wish-done':item.completed}">{{item.title}}</view><view v-if="item.description" class="muted content">{{item.description}}</view><view class="row space-top"><text class="link" @tap="editWish(item)">编辑</text><text class="muted" @tap="remove('wishes',item.id)">删除</text></view></view></view>
        <view v-if="!wishes.length&&!editor&&!error" class="empty"><view class="empty-title">有空的话，一起去…</view><text>愿望不必很大，一顿早餐也很好。</text></view>
      </view>
      <view v-if="editor" class="card editor-card">
        <view class="section-title">{{editingId?'编辑':'新增'}}{{pane==='anniversaries'?'纪念日':'愿望'}}</view>
        <view class="field"><text class="label">名称</text><input v-model="entry.title" class="input" :placeholder="pane==='anniversaries'?'给这个日子一个名字':'写下一件想一起做的事'" maxlength="120"/></view>
        <view v-if="pane==='anniversaries'"><view class="field"><text class="label">日期</text><picker mode="date" :value="entry.date" @change="entry.date=$event.detail.value"><view class="picker">{{entry.date}}</view></picker></view><view class="row between"><text>每年纪念这一天</text><switch :checked="entry.repeat_yearly" color="#477A68" @change="setRepeat"/></view></view>
        <view v-else class="field"><text class="label">小小的补充（选填）</text><textarea v-model="entry.description" class="textarea" placeholder="想怎么实现，有什么要准备的？" maxlength="2000"/></view>
        <view class="actions"><button class="ghost" :disabled="working" @tap="editor=false">取消</button><button class="primary" :loading="working" :disabled="working||!entry.title.trim()" @tap="saveEntry">保存</button></view>
      </view>
      <view v-if="pane==='questions'">
        <view v-if="question" class="card question-card"><text class="eyebrow">今天，听听你的想法</text><view class="question serif">{{question.question}}</view><view class="question-line"/>
          <view class="field"><text class="label">我的回答</text><textarea v-model="answer" class="textarea" placeholder="认真想一想，写给对方看。" maxlength="5000"/></view><button class="primary" :loading="working" :disabled="working||!answer.trim()" @tap="saveAnswer">{{question.my_answer?'更新我的回答':'写下我的回答'}}</button>
          <view class="divider"/><text class="caption">对方的回答</text><view v-if="question.both_answered" class="answer content serif">{{question.partner_answer}}</view><view v-else class="muted space-top">{{question.my_answer?'你的回答已收好，等对方也回答后一起揭晓。':'你们都回答以后，才会看到彼此的答案。'}}</view>
        </view>
        <view v-else-if="!error" class="empty"><view class="empty-title">今天的问题还在准备中</view><text>晚一点再来，一起聊点不一样的。</text><button class="ghost small" @tap="load">重新查看</button></view>
      </view>
      <view v-if="pane==='moods'">
        <ScopeSwitch @change="load"/>
        <view class="card"><text class="caption">今天的你，是什么天气？</text><view class="mood-options"><view v-for="m in moodOptions" :key="m.value" class="mood-option" :class="{selected:mood===m.value}" @tap="mood=m.value"><text class="mood-icon">{{m.icon}}</text><text>{{m.value}}</text></view></view><textarea v-model="moodNote" class="textarea" placeholder="想多说两句吗？" maxlength="2000"/><view class="chips space-top"><view class="chip" :class="{active:moodVisibility==='private'}" @tap="moodVisibility='private'">仅自己</view><view class="chip" :class="{active:moodVisibility==='shared'}" @tap="shareMood">与对方共享</view></view><button class="primary space-top" :disabled="working||!mood" :loading="working" @tap="saveMood">记下此刻的心情</button></view>
        <view v-for="item in moods" :key="item.id" class="card"><view class="row between"><text class="strong">{{item.author_name}} · {{item.mood}}</text><text class="muted">{{item.day}}</text></view><view v-if="item.note" class="content space-top">{{item.note}}</view><text class="help">{{item.visibility==='private'?'仅自己可见':'当前空间共享'}}</text></view>
        <view v-if="!moods.length&&!error" class="muted">还没有心情记录，今天可以从一个词开始。</view>
      </view>
      <view v-if="pane==='habits'">
        <view class="section-title">想一起坚持的事</view><view class="card"><view class="row"><input v-model="habitTitle" class="input grow" placeholder="一起散步、早点睡、每天读书…" maxlength="120"/><button class="small primary" :disabled="working||!habitTitle.trim()" :loading="working" @tap="createHabit">添加</button></view></view>
        <view v-for="item in habits" :key="item.id" class="card row between"><view class="grow"><view class="strong">{{item.title}}</view><view class="muted">{{item.checked_today?'今天也做到了':'慢慢来，今天做一点点也很好'}}</view></view><button class="small" :class="item.checked_today?'secondary':'primary'" :disabled="working||item.checked_today" @tap="checkin(item)">{{item.checked_today?'今日已完成':'今日打卡'}}</button></view>
        <view v-if="!habits.length&&!error" class="empty"><view class="empty-title">让一点点，变成每一天</view><text>从一件容易坚持的小事开始。</text></view>
      </view>
    </view>
  </view>
</template>
<script setup lang="ts">
import { ref, reactive } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import ScopeSwitch from '../../components/ScopeSwitch.vue'
import { api, state, ensureAuth, refreshContext, message, query, today, confirm, toast } from '../../lib/api'
import type { Anniversary, Wish, Question, Mood, Habit, List, Visibility } from '../../lib/types'
type Pane='anniversaries'|'wishes'|'questions'|'moods'|'habits'
const tabs:{key:Pane;label:string}[]=[{key:'anniversaries',label:'纪念日'},{key:'wishes',label:'心愿清单'},{key:'questions',label:'每日一问'},{key:'moods',label:'心情'},{key:'habits',label:'习惯'}]
const pane=ref<Pane>('anniversaries'),loading=ref(false),working=ref(false),error=ref(''),editor=ref(false),editingId=ref(''),answer=ref(''),habitTitle=ref('')
const anniversaries=ref<Anniversary[]>([]),wishes=ref<Wish[]>([]),question=ref<Question|null>(null),moods=ref<Mood[]>([]),habits=ref<Habit[]>([])
const entry=reactive({title:'',date:today(),repeat_yearly:true,description:''})
const mood=ref(''),moodNote=ref(''),moodVisibility=ref<Visibility>('private'),moodOptions=[{value:'晴朗',icon:'☀'},{value:'平静',icon:'≈'},{value:'想念',icon:'✉'},{value:'低落',icon:'☁'},{value:'有点累',icon:'☾'}]
let generation=0
function clear(){anniversaries.value=[];wishes.value=[];question.value=null;moods.value=[];habits.value=[]}
async function load(){if(!ensureAuth())return;const g=++generation;loading.value=true;error.value='';clear();try{await refreshContext();if(!state.space&&pane.value!=='moods')return;const current=pane.value;if(current==='questions'){const q=await api<Question|null>('/interaction/today');if(g===generation){question.value=q;answer.value=q?.my_answer||''}}else{const r=await api<List<Anniversary|Wish|Mood|Habit>>('/'+current+(current==='moods'?query({scope:state.scope}):''));if(g!==generation)return;if(current==='anniversaries')anniversaries.value=r.items as Anniversary[];if(current==='wishes')wishes.value=r.items as Wish[];if(current==='moods')moods.value=r.items as Mood[];if(current==='habits')habits.value=r.items as Habit[]}}catch(e){if(g===generation)error.value=message(e)}finally{if(g===generation)loading.value=false}}
function change(value:Pane){if(working.value)return;pane.value=value;editor.value=false;load()}
function newEntry(){editingId.value='';Object.assign(entry,{title:'',date:today(),repeat_yearly:true,description:''});editor.value=true}
function setRepeat(event:any){entry.repeat_yearly=event.detail.value}
function editAnniversary(a:Anniversary){editingId.value=a.id;Object.assign(entry,{title:a.title,date:a.date,repeat_yearly:a.repeat_yearly,description:''});editor.value=true}
function editWish(w:Wish){editingId.value=w.id;Object.assign(entry,{title:w.title,description:w.description});editor.value=true}
async function perform(action:()=>Promise<void>){if(working.value)return;working.value=true;error.value='';try{await action();await load()}catch(e){error.value=message(e)}finally{working.value=false}}
async function saveEntry(){await perform(async()=>{const data=pane.value==='anniversaries'?{title:entry.title.trim(),date:entry.date,repeat_yearly:entry.repeat_yearly}:{title:entry.title.trim(),description:entry.description};await api(`/${pane.value}${editingId.value?'/'+encodeURIComponent(editingId.value):''}`,editingId.value?'PATCH':'POST',data);editor.value=false;toast('已保存')})}
async function remove(resource:string,id:string){if(!await confirm('删除这条记录？','删除后，双方都无法再看到这条记录。'))return;await perform(async()=>{await api(`/${resource}/${encodeURIComponent(id)}`,'DELETE');toast('已删除')})}
async function complete(w:Wish){await perform(async()=>{await api(`/wishes/${encodeURIComponent(w.id)}`,'PATCH',{completed:!w.completed});toast(w.completed?'愿望已重新打开':'又实现了一个愿望')})}
async function saveAnswer(){if(!question.value)return;await perform(async()=>{await api('/interaction/answers','POST',{question_id:question.value!.id,answer:answer.value.trim()});toast('回答已保存')})}
function shareMood(){if(!state.space){toast('先到「我们」创建或加入双人空间');return};moodVisibility.value='shared'}
async function saveMood(){await perform(async()=>{await api('/moods','POST',{mood:mood.value,note:moodNote.value,visibility:moodVisibility.value});moodNote.value='';mood.value='';toast('心情已保存')})}
async function createHabit(){await perform(async()=>{await api('/habits','POST',{title:habitTitle.value.trim()});habitTitle.value='';toast('习惯已添加')})}
async function checkin(h:Habit){await perform(async()=>{await api(`/habits/${encodeURIComponent(h.id)}/checkins`,'POST',{});toast('今天已打卡')})}
function profile(){uni.switchTab({url:'/pages/profile/index'})}onShow(load)
</script>
<style scoped>
.life-scroll{white-space:nowrap;margin:34rpx 0 24rpx}.life-tabs{display:flex;gap:12rpx;padding-bottom:14rpx}.life-tab{display:inline-block;flex-shrink:0;padding:14rpx 26rpx;background:#E8F0F3;border-radius:100rpx;color:#7E929C;font-size:25rpx}.life-tab.chosen{background:#24647A;color:white}.anniversary-date{font-size:49rpx;color:#24647A;margin:16rpx 0}.anniversary-title{margin:0 0 22rpx}.wish-row{display:flex;gap:20rpx}.wish-check{padding:0;flex-shrink:0;width:50rpx;height:50rpx;border-radius:50%;background:#F3F7F8;color:#7E929C;font-size:35rpx;line-height:50rpx}.wish-check.done{background:#EAF3EE;color:#477A68}.wish-done{text-decoration:line-through;color:#7E929C}.editor-card{border-color:#C9DDE6}.question-card{padding:38rpx 30rpx}.question{font-size:44rpx;line-height:1.6;margin:24rpx 0 30rpx}.question-line{width:60rpx;height:3rpx;background:#E2917D;margin-bottom:35rpx}.answer{font-size:32rpx;margin-top:20rpx;line-height:1.9}.mood-options{display:flex;gap:12rpx;margin:26rpx 0}.mood-option{flex:1;text-align:center;padding:18rpx 0;background:#F3F7F8;border:1rpx solid transparent;border-radius:14rpx;font-size:22rpx;color:#7E929C}.mood-option.selected{border-color:#477A68;color:#477A68;background:#EAF3EE}.mood-icon{display:block;font-size:40rpx;line-height:1.1;margin-bottom:12rpx}
</style>
