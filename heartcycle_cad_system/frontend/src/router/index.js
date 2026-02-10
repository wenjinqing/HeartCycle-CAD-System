import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Monitor from '../views/Monitor.vue'
import History from '../views/History.vue'

const routes = [
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
    path: '/train',
    name: 'TrainModel',
    component: () => import('../views/TrainModel.vue')
  },
  {
    path: '/train-h5-auto',
    name: 'TrainH5Auto',
    component: () => import('../views/TrainH5Auto.vue')
  },
  {
    path: '/h5-converter',
    name: 'H5Converter',
    component: () => import('../views/H5Converter.vue')
  },
  {
    path: '/history',
    name: 'History',
    component: History
  },
  {
    path: '/batch-predict',
    name: 'BatchPredict',
    component: () => import('../views/BatchPredict.vue')
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

