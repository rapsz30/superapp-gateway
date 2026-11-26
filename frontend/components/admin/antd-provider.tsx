'use client'
import type { ReactNode } from 'react'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { App, ConfigProvider } from 'antd'
import idID from 'antd/locale/id_ID'
import 'dayjs/locale/id'
export function AntdProvider({ children }: { children: ReactNode }) {
  return <AntdRegistry><ConfigProvider
    locale={idID}
    theme={{
      token: {
        colorPrimary: '#2858e8',
        colorInfo: '#2858e8',
        colorSuccess: '#0f9d8a',
        colorWarning: '#d97706',
        colorError: '#dc2626',
        colorBgLayout: '#f7f9fc',
        colorBgContainer: '#ffffff',
        colorText: '#172744',
        colorTextSecondary: '#667594',
        colorBorder: '#e1e7f0',
        colorBorderSecondary: '#edf1f6',
        borderRadius: 10,
        borderRadiusLG: 16,
        controlHeight: 40,
        fontFamily: "'Inter', 'Segoe UI', sans-serif",
      },
      components: {
        Layout: { headerBg: '#ffffff', siderBg: '#ffffff', bodyBg: '#f7f9fc' },
        Card: { borderRadiusLG: 16, headerHeight: 62, bodyPadding: 22 },
        Button: { controlHeight: 38, borderRadius: 9, fontWeight: 600 },
        Input: { controlHeight: 40, activeBorderColor: '#2858e8', activeShadow: '0 0 0 3px rgba(40, 88, 232, 0.12)' },
        Select: { controlHeight: 40 },
        Table: { headerBg: '#f7f9fc', headerColor: '#52617a', rowHoverBg: '#f8faff', borderColor: '#edf1f6' },
        Menu: { itemBorderRadius: 9, itemSelectedBg: '#eaf0ff', itemSelectedColor: '#2858e8', itemHoverBg: '#f5f7fb' },
        Tag: { borderRadiusSM: 999 },
      },
    }}
  ><App>{children}</App></ConfigProvider></AntdRegistry>
}
