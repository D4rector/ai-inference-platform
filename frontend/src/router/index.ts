import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
    },
    {
      path: '/',
      component: () => import('../views/Layout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
        { path: 'tasks', name: 'Tasks', component: () => import('../views/Tasks.vue') },
        { path: 'models', name: 'Models', component: () => import('../views/Models.vue') },
      ],
    },
  ],
})

// 路由守卫：未登录跳登录页
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
