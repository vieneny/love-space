import { createApp } from 'vue'
import { ElAlert, ElButton, ElConfigProvider, ElDialog, ElDrawer, ElIcon, ElInput, ElLoading, ElOption, ElPagination, ElSelect, ElSkeleton, ElSkeletonItem, ElSwitch, ElTable, ElTableColumn, ElTag } from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './styles.css'

const app = createApp(App)
for (const component of [ElAlert, ElButton, ElConfigProvider, ElDialog, ElDrawer, ElIcon, ElInput, ElOption, ElPagination, ElSelect, ElSkeleton, ElSkeletonItem, ElSwitch, ElTable, ElTableColumn, ElTag]) {
  app.component(component.name!, component)
}
app.use(router).use(ElLoading).mount('#app')
