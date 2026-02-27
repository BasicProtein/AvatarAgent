import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            name: 'Home',
            component: () => import('../views/HomeView.vue'),
        },
        {
            path: '/voices',
            name: 'Voices',
            component: () => import('../views/VoicesView.vue'),
        },
        {
            path: '/avatars',
            name: 'Avatars',
            component: () => import('../views/AvatarsView.vue'),
        },
        {
            path: '/assets',
            name: 'Assets',
            component: () => import('../views/AssetsView.vue'),
        },
        {
            path: '/tasks',
            name: 'Tasks',
            component: () => import('../views/TasksView.vue'),
        },
        {
            path: '/accounts',
            name: 'Accounts',
            component: () => import('../views/AccountsView.vue'),
        },
        {
            path: '/profile',
            name: 'Profile',
            component: () => import('../views/ProfileView.vue'),
        },
        {
            path: '/settings',
            name: 'Settings',
            component: () => import('../views/SettingsView.vue'),
        },
        {
            path: '/help',
            name: 'Help',
            component: () => import('../views/HelpView.vue'),
        },
    ],
})

export default router
