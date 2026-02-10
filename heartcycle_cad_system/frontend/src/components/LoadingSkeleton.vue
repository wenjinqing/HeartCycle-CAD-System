<template>
  <div class="loading-skeleton">
    <div v-if="type === 'card'" class="skeleton-card">
      <el-skeleton :rows="3" animated />
    </div>
    <div v-else-if="type === 'table'" class="skeleton-table">
      <el-skeleton :rows="5" animated />
    </div>
    <div v-else-if="type === 'list'" class="skeleton-list">
      <el-skeleton-item
        v-for="i in count"
        :key="i"
        variant="text"
        :style="{ width: '100%', marginBottom: '10px' }"
      />
    </div>
    <el-skeleton v-else :rows="rows" animated />
  </div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'card', 'table', 'list'].includes(value)
  },
  rows: {
    type: Number,
    default: 3
  },
  count: {
    type: Number,
    default: 5
  }
})
</script>

<style scoped>
.loading-skeleton {
  padding: 20px;
}

.skeleton-card {
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.skeleton-table {
  padding: 20px;
}
</style>

