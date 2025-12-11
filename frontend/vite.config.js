import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // Change this if your backend runs on a different port
        changeOrigin: true,
      },
    },
  },
});
