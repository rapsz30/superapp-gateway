'use client'
import type { ReactNode } from 'react'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { App, ConfigProvider } from 'antd'
import idID from 'antd/locale/id_ID'
import 'dayjs/locale/id'
export function AntdProvider({ children }: { children: ReactNode }) {
  return <AntdRegistry><ConfigProvider locale={idID} theme={{ token: { colorPrimary: '#2858e8', borderRadius: 8, fontFamily: "'Roboto', sans-serif" } }}><App>{children}</App></ConfigProvider></AntdRegistry>
}
