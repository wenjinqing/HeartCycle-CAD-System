<template>
  <div id="app">
    <el-container>
      <el-header>
        <div class="header-content">
          <div class="logo">
            <el-icon><FirstAidKit /></el-icon>
            <span>HeartCycle 冠心病风险预测系统</span>
          </div>
          <el-menu
            :default-active="activeIndex"
            class="header-menu"
            mode="horizontal"
            router
          >
            <el-menu-item index="/">首页</el-menu-item>
            <el-menu-item index="/monitor">监测分析</el-menu-item>
            <el-sub-menu index="/train">
              <template #title>模型训练</template>
              <el-menu-item index="/train-h5-auto">H5快速训练（推荐）</el-menu-item>
              <el-menu-item index="/train">完整训练流程</el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/batch-predict">批量预测</el-menu-item>
            <el-menu-item index="/history">历史记录</el-menu-item>
            <el-menu-item index="/dashboard">性能监控</el-menu-item>
          </el-menu>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <el-footer>
        <div class="footer-content">
          <p>© 2024 HeartCycle CAD System. 仅供学术研究使用。</p>
        </div>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { FirstAidKit } from '@element-plus/icons-vue'

export default {
  name: 'App',
  components: {
    FirstAidKit
  },
  setup() {
    const route = useRoute()
    const activeIndex = computed(() => route.path)
    
    return {
      activeIndex
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  background: #f5f7fa;
}

.el-header {
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 0;
  height: 60px !important;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
  cursor: pointer;
  transition: color 0.3s;
}

.logo:hover {
  color: #66b1ff;
}

.logo .el-icon {
  font-size: 26px;
  margin-right: 10px;
}

.header-menu {
  border-bottom: none;
}

.el-main {
  padding: 20px;
  min-height: calc(100vh - 120px);
}

.el-footer {
  background: #fff;
  text-align: center;
  line-height: 60px;
  height: 60px !important;
  border-top: 1px solid #e4e7ed;
}

.footer-content {
  color: #909399;
  font-size: 14px;
}
</style>

