<template>
  <div id="app">
    <!-- 登录页面不显示导航 -->
    <template v-if="isLoginPage">
      <router-view />
    </template>

    <!-- 其他页面显示完整布局 -->
    <template v-else>
      <el-container>
        <el-header>
          <div class="header-content">
            <div class="logo" @click="$router.push('/')">
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
              <el-sub-menu index="/train" v-if="canTrain">
                <template #title>模型训练</template>
                <el-menu-item index="/train-h5-auto">H5快速训练（推荐）</el-menu-item>
                <el-menu-item index="/train">完整训练流程</el-menu-item>
                <el-menu-item index="/train-deep-learning">深度学习训练</el-menu-item>
                <el-menu-item index="/train-multimodal">多模态融合训练</el-menu-item>
                <el-menu-item index="/h5-visualize">H5信号可视化</el-menu-item>
              </el-sub-menu>
              <el-menu-item index="/batch-predict" v-if="isLoggedIn">批量预测</el-menu-item>
              <el-menu-item index="/patients" v-if="canManagePatients">患者管理</el-menu-item>
              <el-menu-item index="/reports" v-if="canAccessReports">报告管理</el-menu-item>
              <el-menu-item index="/model-versions" v-if="canManageModels">模型版本</el-menu-item>
              <el-menu-item index="/thesis-experiment" v-if="canAccessExperiment">
                <el-icon><Document /></el-icon>
                论文实验
              </el-menu-item>
              <el-menu-item index="/history">历史记录</el-menu-item>
              <el-sub-menu index="/admin" v-if="isAdmin">
                <template #title>系统管理</template>
                <el-menu-item index="/dashboard">性能监控</el-menu-item>
                <el-menu-item index="/system-monitor">系统监控</el-menu-item>
                <el-menu-item index="/admin/users">用户管理</el-menu-item>
                <el-menu-item index="/admin/audit-logs">审计日志</el-menu-item>
              </el-sub-menu>
            </el-menu>

            <!-- 用户菜单 -->
            <div class="user-menu">
              <template v-if="isLoggedIn">
                <el-space :size="12">
                  <el-dropdown @command="handleUserCommand">
                    <span class="user-dropdown">
                      <el-avatar :size="32" :src="user?.avatar_url">
                        {{ user?.full_name?.charAt(0) || user?.username?.charAt(0) }}
                      </el-avatar>
                      <span class="username">{{ user?.full_name || user?.username }}</span>
                      <el-icon><ArrowDown /></el-icon>
                    </span>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="profile">
                          <el-icon><User /></el-icon>
                          个人资料
                        </el-dropdown-item>
                        <el-dropdown-item divided command="logout">
                          <el-icon><SwitchButton /></el-icon>
                          退出登录
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                  <el-button type="danger" size="small" @click="handleUserCommand('logout')">
                    <el-icon><SwitchButton /></el-icon>
                    退出
                  </el-button>
                </el-space>
              </template>
              <template v-else>
                <el-button type="primary" @click="$router.push('/login')">登录</el-button>
              </template>
            </div>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
        <el-footer>
          <div class="footer-content">
            <p>© 2026 HeartCycle CAD System. 仅供学术研究使用。</p>
          </div>
        </el-footer>
      </el-container>
    </template>
  </div>
</template>

<script>
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FirstAidKit, ArrowDown, User, SwitchButton, Document } from '@element-plus/icons-vue'
import { authApi } from '@/services/api'

export default {
  name: 'App',
  components: {
    FirstAidKit,
    ArrowDown,
    User,
    SwitchButton,
    Document
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const user = ref(null)

    const activeIndex = computed(() => route.path)
    const isLoginPage = computed(() => route.path === '/login')
    const isLoggedIn = computed(() => !!localStorage.getItem('access_token'))

    const isAdmin = computed(() => user.value?.role === 'admin')
    const canTrain = computed(() => {
      if (!user.value) return false
      return ['admin', 'doctor', 'researcher'].includes(user.value.role)
    })
    const canManagePatients = computed(() => {
      if (!user.value) return false
      return ['admin', 'doctor'].includes(user.value.role)
    })
    const canAccessReports = computed(() => {
      if (!user.value) return false
      return ['admin', 'doctor', 'researcher'].includes(user.value.role)
    })
    const canManageModels = computed(() => {
      if (!user.value) return false
      return ['admin', 'researcher'].includes(user.value.role)
    })
    const canAccessExperiment = computed(() => {
      if (!user.value) return false
      return ['admin', 'researcher'].includes(user.value.role)
    })

    const loadUser = () => {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        try {
          user.value = JSON.parse(userStr)
        } catch (e) {
          user.value = null
        }
      } else {
        user.value = null
      }
    }

    const handleUserCommand = async (command) => {
      if (command === 'profile') {
        router.push('/profile')
      } else if (command === 'logout') {
        try {
          await authApi.logout()
        } catch (error) {
          // 忽略登出错误
        }

        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        user.value = null

        ElMessage.success('已退出登录')
        router.push('/login')
      }
    }

    // 监听路由变化，更新用户信息
    watch(() => route.path, () => {
      loadUser()
    })

    onMounted(() => {
      loadUser()
    })

    return {
      activeIndex,
      isLoginPage,
      isLoggedIn,
      isAdmin,
      canTrain,
      canManagePatients,
      canAccessReports,
      canManageModels,
      canAccessExperiment,
      user,
      handleUserCommand
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
  background: linear-gradient(165deg, #eef2f7 0%, #f5f7fa 42%, #f0f4f8 100%);
  background-attachment: fixed;
}

.el-header {
  background: linear-gradient(180deg, #ffffff 0%, #fafbfc 100%);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.06), 0 4px 20px rgba(15, 23, 42, 0.04);
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
  flex: 1;
  margin-left: 40px;
}

.user-menu {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #606266;
}

.user-dropdown:hover {
  color: #409eff;
}

.user-dropdown .username {
  margin: 0 8px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.el-main {
  padding: 16px 18px 28px;
  min-height: calc(100vh - 120px);
}

@media (min-width: 900px) {
  .el-main {
    padding: 20px 24px 32px;
  }
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
