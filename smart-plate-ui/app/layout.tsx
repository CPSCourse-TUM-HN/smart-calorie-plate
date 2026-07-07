import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Smart Plate',
  description: 'AI-powered nutrition and calorie management with image recognition',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark bg-zinc-950">
      <body className="font-sans antialiased bg-zinc-950 text-zinc-100">
        {/* Fallback error overlay: when hydration fails in an old WebView
            (e.g. PyWebView's WKWebView), the real error is shown at the
            bottom of the page even without dev tools, which makes
            "button does nothing" issues debuggable. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){function show(m){var d=document.getElementById('__err')||document.createElement('div');d.id='__err';d.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:99999;max-height:50vh;overflow:auto;background:#7f1d1d;color:#fff;font:12px/1.5 ui-monospace,monospace;padding:12px;white-space:pre-wrap';d.textContent='[JS ERROR] '+m;document.body.appendChild(d);}window.addEventListener('error',function(e){show((e.error&&e.error.stack)||e.message||String(e));});window.addEventListener('unhandledrejection',function(e){show('Promise: '+((e.reason&&e.reason.stack)||e.reason));});})();`,
          }}
        />
        {children}
      </body>
    </html>
  )
}
