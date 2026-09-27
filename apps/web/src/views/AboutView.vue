<template>
  <section class="card">
    <h2>About</h2>
    <p>
      Traffic flow: Vue SPA -> OpenResty gateway (/api, JWT verified, rate
      limited) -> go-zero user-api. This route is served by the gateway's
      try_files fallback for history-mode routing.
    </p>
  </section>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #e4e7eb;
  border-radius: 8px;
  padding: 24px;
}
</style>
