const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      }
    },
    client: {
      overlay: {
        runtimeErrors: (error) => {
          // 忽略ResizeObserver错误（这是常见的浏览器警告，不影响功能）
          if (error.message === 'ResizeObserver loop completed with undelivered notifications.') {
            return false
          }
          return true
        }
      }
    }
  },
  publicPath: process.env.NODE_ENV === 'production' ? './' : '/'
})

