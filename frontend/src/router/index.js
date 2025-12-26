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
    path: '/history',
    name: 'History',
    component: History
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

