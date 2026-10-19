<template>
  <div class="app">
    <nav class="navbar">
      <div class="nav-brand">
        <h1>AI-GEMPA BMKG</h1>
      </div>
      <ul class="nav-menu">
        <li>
          <RouterLink to="/pipeline-builder" class="nav-link" active-class="active">
            Pipeline Builder
          </RouterLink>
        </li>
        <li>
          <RouterLink to="/billing" class="nav-link" active-class="active">
            Billing
          </RouterLink>
        </li>
      </ul>
    </nav>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  background: #1f2937;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.nav-brand h1 {
  margin: 0;
  font-size: 1.5rem;
}

.nav-menu {
  display: flex;
  list-style: none;
  gap: 2rem;
  margin: 0;
  padding: 0;
}

.nav-link {
  color: white;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
}

.nav-link.active {
  background: #3b82f6;
}

.main-content {
  flex: 1;
  background: #f3f4f6;
}
</style>
