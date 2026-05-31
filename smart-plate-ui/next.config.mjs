/** @type {import('next').NextConfig} */
const nextConfig = {
  // 静态导出到 out/，供 FastAPI 同源托管，打包成桌面 app。
  output: "export",
  // file://-style 资源加载更稳：每个路由生成独立目录 + index.html。
  trailingSlash: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
