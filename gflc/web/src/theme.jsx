/* antd ConfigProvider 苹果白主题（v7l 对齐）。
   单一事实源：theme.css 的 CSS 变量 + 这里的 antd token。 */
export const gflcTheme = {
  token: {
    colorPrimary: '#0071E3',
    colorBgBase: '#F5F5F7',
    colorBgContainer: '#FFFFFF',
    colorText: '#1D1D1F',
    colorTextSecondary: '#6E6E73',
    colorTextTertiary: '#86868B',
    colorBorder: 'rgba(0,0,0,.07)',
    colorBorderSecondary: 'rgba(0,0,0,.045)',
    borderRadius: 10,
    borderRadiusLG: 12,
    borderRadiusSM: 8,
    fontSize: 12.5,
    fontSizeLG: 13,
    fontSizeSM: 11,
    controlHeight: 32,
    fontFamily: '"PingFang SC","Microsoft YaHei UI","Microsoft YaHei","Noto Sans CJK SC",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
  },
  components: {
    Button: {
      borderRadius: 8,
      primaryShadow: 'none',
      fontWeight: 500,
    },
    Card: {
      borderRadiusLG: 12,
    },
    Modal: {
      borderRadiusLG: 16,
    },
    Table: {
      headerBg: '#F5F5F7',
      headerColor: '#86868B',
      fontSize: 12,
    },
    Tabs: {
      fontSize: 12,
    },
    Select: {
      borderRadius: 8,
    },
    Input: {
      borderRadius: 8,
    },
  },
};

export const gflcDarkTheme = {
  token: {
    ...gflcTheme.token,
    colorPrimary: '#2997FF',
    colorBgBase: '#0F0F10',
    colorBgContainer: '#1C1C1E',
    colorText: '#F5F5F7',
    colorTextSecondary: '#B8B8BC',
    colorTextTertiary: '#8E8E93',
    colorBorder: 'rgba(255,255,255,.10)',
    colorBorderSecondary: 'rgba(255,255,255,.06)',
  },
  components: {
    ...gflcTheme.components,
    Table: {
      ...gflcTheme.components.Table,
      headerBg: '#232326',
      headerColor: '#8E8E93',
    },
  },
};
