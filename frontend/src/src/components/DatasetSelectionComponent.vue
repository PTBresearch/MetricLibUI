<template>
  <div class="overlay-container">
    <div class="header-row">
      <h3>Select a dataset</h3>
      <button class="close-button" @click="$emit('cancel')">Cancel</button>
    </div>

    <div class="list-container">
      <div
        v-for="(file, idx) in files"
        :key="idx"
        class="file-item"
        @click="select(file)"
        :title="file"
      >
        <span class="file-icon">📄</span>
        <span class="file-name">{{ file }}</span>
      </div>
    </div>

    <div v-if="loadingError" class="error-text">{{ loadingError }}</div>
  </div>
</template>

<script>
export default {
  name: 'DatasetSelectionComponent',
  emits: ['cancel', 'select', 'loading'],
  data() {
    return {
      files: [],
      loadingError: '',
    };
  },
  mounted() {
    this.fetchFiles();
  },
  methods: {
    async fetchFiles() {
      this.$emit('loading', true);
      this.loadingError = '';
      try {
        const resp = await fetch('/api/files', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });
        if (!resp.ok) {
          throw new Error(`Server responded ${resp.status}`);
        }
        const data = await resp.json();
        if (Array.isArray(data) && data.length > 0) {
          this.files = data;
        } else {
          this.files = [];
          this.loadingError = 'No CSV files found.';
        }
      } catch (e) {
        console.error('Failed to load files:', e);
        this.loadingError = 'Failed to load files.';
      } finally {
        this.$emit('loading', false);
      }
    },
    select(file) {
      this.$emit('select', file);
    },
  },
};
</script>

<style scoped>
.overlay-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background-color: #1e1e1e;
  padding: 40px 48px;
  border-radius: 20px;
  color: #f5f6fa;
  min-width: 420px;
  max-width: 860px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

h3 {
  font-size: 1.1em;
  margin: 0;
}

.close-button {
  padding: 10px 16px;
  background: linear-gradient(90deg, #e74c3c 60%, #c0392b 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}
.close-button:hover {
  background: linear-gradient(90deg, #c0392b 60%, #e74c3c 100%);
}

.list-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 55vh;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: #121212;
  border: 1px solid #353b48;
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background-color 0.15s ease-in-out, border-color 0.15s ease-in-out;
}
.file-item:hover {
  background-color: #1c1c1c;
  border-color: #4a5a6a;
}

.file-icon {
  font-size: 18px;
}

.file-name {
  font-size: 14px;
  color: #e1e6f0;
}

.error-text {
  color: #ff6b6b;
  font-size: 13px;
}
</style>
