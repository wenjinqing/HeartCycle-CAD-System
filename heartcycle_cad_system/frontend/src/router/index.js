import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Monitor from '../views/Monitor.vue'
import History from '../views/History.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/monitor',
    name: 'Monitor',
    component: Monitor
  },
  {
    path: '/predict',
    redirect: (to) => ({ path: '/monitor', query: to.query })
  },
  {
    path: '/train',
    name: 'TrainModel',
    component: () => import('../views/TrainModel.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/train-h5-auto',
    name: 'TrainH5Auto',
    component: () => import('../views/TrainH5Auto.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/train-deep-learning',
    name: 'TrainDeepLearning',
    component: () => import('../views/TrainDeepLearning.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/h5-converter',
    name: 'H5Converter',
    component: () => import('../views/H5Converter.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/history',
    name: 'History',
    component: History,
    meta: { requiresAuth: true }
  },
  {
    path: '/batch-predict',
    name: 'BatchPredict',
    component: () => import('../views/BatchPredict.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: () => import('../views/admin/Users.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/admin/audit-logs',
    name: 'AdminAuditLogs',
    component: () => import('../views/admin/AuditLogs.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/patients',
    name: 'PatientList',
    component: () => import('../views/PatientList.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor'] }
  },
  {
    path: '/patients/:id',
    name: 'PatientDetail',
    component: () => import('../views/PatientDetail.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor'] }
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('../views/Reports.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/thesis-experiment',
    name: 'ThesisExperiment',
    component: () => import('../views/ThesisExperiment.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'researcher'] }
  },
  {
    path: '/model-versions',
    name: 'ModelVersions',
    component: () => import('../views/ModelVersions.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'researcher'] }
  },
  {
    path: '/system-monitor',
    name: 'SystemMonitor',
    component: () => import('../views/SystemMonitor.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/models/:id',
    name: 'ModelDetail',
    component: () => import('../views/ModelDetail.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/h5-visualize',
    name: 'H5Visualize',
    component: () => import('../views/H5Visualize.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  },
  {
    path: '/train-multimodal',
    name: 'TrainMultiModal',
    component: () => import('../views/TrainMultiModal.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'doctor', 'researcher'] }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const userStr = localStorage.getItem('user')
  const user = userStr ? JSON.parse(userStr) : null

  // 如果是访客页面（如登录页），已登录用户跳转到首页
  if (to.meta.guest && token) {
    return next({ name: 'Home' })
  }

  // 如果需要认证
  if (to.meta.requiresAuth) {
    if (!token) {
      // 未登录，跳转到登录页
      return next({
        name: 'Login',
        query: { redirect: to.fullPath }
      })
    }

    // 检查角色权限
    if (to.meta.roles && user) {
      if (!to.meta.roles.includes(user.role)) {
        // 权限不足
        return next({ name: 'Home' })
      }
    }
  }

  next()
})

export default router
