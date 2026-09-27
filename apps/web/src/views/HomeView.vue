<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { login, userInfo, type UserInfoResp } from '@gozero-monorepo/api-client'
import { formatDateTime } from '@gozero-monorepo/shared-utils'

const form = reactive({ username: 'admin', password: '' })
const error = ref('')
const loading = ref(false)
const profile = ref<UserInfoResp | null>(null)
const loggedInAt = ref(0)

onMounted(async () => {
  if (localStorage.getItem('token')) {
    await loadProfile()
  }
})

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const resp = await login({ username: form.username, password: form.password })
    localStorage.setItem('token', resp.token)
    loggedInAt.value = Date.now()
    await loadProfile()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function loadProfile() {
  try {
    profile.value = await userInfo()
  } catch {
    logout()
  }
}

function logout() {
  localStorage.removeItem('token')
  profile.value = null
}
</script>

<template>
  <section v-if="profile" class="card">
    <h2>Logged in</h2>
    <p>id: {{ profile.id }}</p>
    <p>username: {{ profile.username }}</p>
    <p>email: {{ profile.email }}</p>
    <p v-if="loggedInAt">since: {{ formatDateTime(loggedInAt) }}</p>
    <button @click="logout">Logout</button>
  </section>

  <section v-else class="card">
    <h2>Login</h2>
    <form @submit.prevent="submit">
      <label>
        username
        <input v-model.trim="form.username" autocomplete="username" required />
      </label>
      <label>
        password
        <input
          v-model="form.password"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>
      <button type="submit" :disabled="loading">
        {{ loading ? 'Signing in...' : 'Sign in' }}
      </button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
    <p class="hint">demo credentials: admin / admin123</p>
  </section>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 8px;
  padding: 24px;
}
label {
  display: block;
  margin-bottom: 12px;
}
input {
  display: block;
  width: 100%;
  margin-top: 4px;
  padding: 8px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
}
button {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #1f6feb;
  color: #fff;
  cursor: pointer;
}
.error {
  color: #cf222e;
}
.hint {
  color: #6e7781;
  font-size: 13px;
}
</style>
