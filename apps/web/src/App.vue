<script setup lang="ts">
</script>

<template>
  <header class="topbar">
    <span class="brand">gozero monorepo</span>
    <nav>
      <RouterLink to="/">Home</RouterLink>
      <RouterLink to="/about">About</RouterLink>
    </nav>
  </header>
  <main class="page">
    <RouterView />
  </main>
</template>

<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto,
    'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: #f6f7f9;
  color: #1f2328;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #1f2328;
  color: #fff;
}
.brand {
  font-weight: 600;
}
.topbar nav a {
  color: #9dadc6;
  margin-left: 16px;
  text-decoration: none;
}
.topbar nav a.router-link-active {
  color: #fff;
}
.page {
  max-width: 720px;
  margin: 32px auto;
  padding: 0 16px;
}
</style>
