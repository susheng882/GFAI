/**
 * GFLC v8 · 前端 mock 数据源
 * 硬约束：所有页面一律从这里取数，禁止 import '../api.js'，不发起任何后端请求。
 * 当前批次：登录（Auth）、概览（Dashboard）。
 */

/** 用户档案 */
export const profile = {
  id: 'u_1001',
  name: '苏胜',
  initial: 'S',
  school: '浙江水利水电学院',
  major: '软件工程',
  klass: 'zb23-1',
  exam: '考研 11408',
  targetScore: 380,
  examDate: '2026-12-19',
  daysLeft: 22,
};

/** 登录页演示凭据（mock 校验，不发请求） */
export const authDemo = {
  email: 'su.sheng@gflc.app',
  password: 'gflc2026',
  name: '苏胜',
};

/** 登录页左侧品牌区 */
export const authBrand = {
  product: 'GFLC',
  productCn: '成长向前',
  tagline: '把教材、视频、题目收进一条学习闭环。',
  highlights: [
    '资料解析成笔记与卡片，按章节归档，不用手动整理。',
    '今日该复习什么由遗忘曲线决定，打开就知道做什么。',
    '刷题、背诵、错题三处联动，进度与掌握度实时可见。',
  ],
  stats: [
    { label: '已坚持学习', value: '128 天' },
    { label: '在背卡片', value: '1,240 张' },
    { label: '目标总分', value: '380 分' },
  ],
  footer: '本地部署 · 数据只存在你的电脑里',
};

/** 概览 · 四指标带 */
export const dashboardKpis = [
  { key: 'due', label: '今日复习', value: 42, unit: '张', hint: '较昨日 +8 张', tone: 'ink' },
  { key: 'mastery', label: '掌握率', value: 68, unit: '%', hint: '近 7 天 +3.2%', tone: 'ok' },
  { key: 'streak', label: '连续学习', value: 23, unit: '天', hint: '历史最长 31 天', tone: 'ink' },
  { key: 'goal', label: '目标进度', value: 61, unit: '%', hint: '距 380 分目标', tone: 'brand' },
];

/** 概览 · 周目标条 */
export const weeklyGoal = {
  label: '本周目标',
  done: 148,
  total: 240,
  unit: '题',
  range: '11-23 至 11-29',
  daysLeft: 2,
  perDayLeft: 46,
};

/** 概览 · 最近学习（视频 / 笔记 / 题库动态） */
export const recentLearnings = [
  {
    id: 'r1',
    kind: 'video',
    kindLabel: '视频',
    title: '操作系统 第 4 讲 · 进程调度与上下文切换',
    meta: '已转写 46 分钟 · 生成 12 张卡片',
    time: '昨天 21:40',
    progress: 86,
    to: '/video',
  },
  {
    id: 'r2',
    kind: 'note',
    kindLabel: '笔记',
    title: '408 计算机网络 · TCP 拥塞控制四算法对比',
    meta: '3 处双链 · 引用《计算机网络 第 8 版》',
    time: '今天 09:12',
    progress: 100,
    to: '/notes',
  },
  {
    id: 'r3',
    kind: 'bank',
    kindLabel: '题库',
    title: '2026 数学一 真题卷（二）',
    meta: '32 题 · 正确率 72%',
    time: '今天 08:40',
    progress: 72,
    to: '/banks',
  },
  {
    id: 'r4',
    kind: 'video',
    kindLabel: '视频',
    title: '英语一 阅读长难句拆解 03',
    meta: '待转写 · 队列排在第 2 位',
    time: '昨天 19:05',
    progress: 0,
    to: '/video',
  },
];

/** 概览 · 卡片分布（按科目） */
export const deckDistribution = [
  { label: '408 计算机', cards: 386, mastery: 72, tone: 'brand' },
  { label: '数学一', cards: 412, mastery: 64, tone: 'ok' },
  { label: '英语一', cards: 268, mastery: 58, tone: 'warn' },
  { label: '政治', cards: 174, mastery: 41, tone: 'ink' },
];

export const deckDistributionTotal = deckDistribution.reduce((s, d) => s + d.cards, 0);

/** 概览 · 学习热力图：近 12 周 × 7 天，level 0–4 */
function buildHeatmap() {
  const weeks = 12;
  const rows = [];
  for (let w = 0; w < weeks; w += 1) {
    const cells = [];
    for (let d = 0; d < 7; d += 1) {
      const seed = (w * 7 + d * 3 + w * d) % 11;
      let level = 0;
      if (seed <= 1) level = 4;
      else if (seed <= 3) level = 3;
      else if (seed <= 5) level = 2;
      else if (seed <= 7) level = 1;
      cells.push({ d, level, minutes: level === 0 ? 0 : level * 28 + (seed % 5) * 6 });
    }
    rows.push({ week: w, cells });
  }
  return rows;
}

export const heatmap = buildHeatmap();

export const heatmapSummary = {
  weeks: 12,
  activeDays: 61,
  totalMinutes: 3480,
  avgPerDay: 57,
  legend: ['无记录', '1–30 分钟', '31–60 分钟', '61–90 分钟', '90 分钟以上'],
};

/** 概览 · 今日可继续（刷题 / 背诵入口） */
export const studyEntries = [
  { key: 'quiz', title: '刷题', value: 32, unit: '道待做', hint: '408 真题卷 2019–2021', to: '/study' },
  { key: 'recite', title: '背诵', value: 18, unit: '张到期', hint: '操作系统 · 内存管理', to: '/review' },
];

/** 概览 · 快速上传 */
export const quickUploads = [
  { key: 'pdf', title: '上传 PDF 资料', sub: '教材 / 讲义 / 论文', hint: '单个 ≤ 200 MB' },
  { key: 'video', title: '导入视频链接', sub: 'B 站 / 本地文件', hint: '自动转写并生成笔记' },
  { key: 'paper', title: '导入试卷', sub: '真题 / 模拟卷', hint: '按题型自动抽题' },
];

/** 概览 · 系统信息卡 */
export const systemInfo = {
  status: { text: '运行正常', tone: 'ok' },
  rows: [
    { label: '解析队列', value: '3 待处理' },
    { label: '转写并发', value: '2 / 5' },
    { label: '今日调用', value: '128 次' },
    { label: '平均延迟', value: '86 ms' },
  ],
  updatedAt: '09:42 同步',
};

/** 概览 · AI 用量卡（近 7 天） */
export const aiUsage = {
  unit: '次',
  today: 28,
  weekTotal: 128,
  tokenLabel: '42.6 万 token',
  days: [
    { label: '五', date: '11-21', value: 12 },
    { label: '六', date: '11-22', value: 9 },
    { label: '日', date: '11-23', value: 18 },
    { label: '一', date: '11-24', value: 24 },
    { label: '二', date: '11-25', value: 21 },
    { label: '三', date: '11-26', value: 16 },
    { label: '四', date: '11-27', value: 28 },
  ],
};

/** 通知红点数量 */
export const notificationCount = 3;

/** 命令面板：「前往 X 页面」便捷项由 AppShell 依据导航生成，这里只放 3 个动作 */
export const paletteActions = [
  { key: 'act-recite', label: '开始背诵', hint: '动作', to: '/review' },
  { key: 'act-train', label: '继续训练', hint: '动作', to: '/study' },
  { key: 'act-video', label: '解析视频', hint: '动作', to: '/video' },
];

/* ================= 资料（Documents） ================= */

export const docSubjects = ['全部', '408 计算机', '数学一', '英语一', '政治'];

export const docKinds = ['全部', '教材', '讲义', '真题卷', '视频'];

export const documents = [
  { id: 'd1', title: '数据结构（C语言版）', subject: '408 计算机', kind: '教材', pages: 368, size: '24.6 MB', mastery: 82, cards: 118, questions: 46, updated: '今天 09:12', status: '已解析', statusTone: 'ok' },
  { id: 'd2', title: '操作系统概念（第 9 版）', subject: '408 计算机', kind: '教材', pages: 862, size: '48.2 MB', mastery: 68, cards: 214, questions: 96, updated: '今天 08:20', status: '已解析', statusTone: 'ok' },
  { id: 'd3', title: '计算机组成原理（第 2 版）', subject: '408 计算机', kind: '教材', pages: 428, size: '31.4 MB', mastery: 54, cards: 96, questions: 38, updated: '昨天 22:04', status: '解析中', statusTone: 'warn' },
  { id: 'd4', title: '计算机网络（第 8 版）', subject: '408 计算机', kind: '教材', pages: 512, size: '36.8 MB', mastery: 61, cards: 132, questions: 52, updated: '昨天 20:36', status: '已解析', statusTone: 'ok' },
  { id: 'd5', title: '数学一 考研数学复习全书', subject: '数学一', kind: '教材', pages: 736, size: '62.1 MB', mastery: 64, cards: 186, questions: 120, updated: '11-25 21:18', status: '已解析', statusTone: 'ok' },
  { id: 'd6', title: '英语一 历年真题 2015–2025', subject: '英语一', kind: '真题卷', pages: 284, size: '18.9 MB', mastery: 58, cards: 74, questions: 168, updated: '11-25 09:42', status: '已解析', statusTone: 'ok' },
  { id: 'd7', title: '肖秀荣 1000 题', subject: '政治', kind: '真题卷', pages: 196, size: '12.4 MB', mastery: 41, cards: 48, questions: 240, updated: '11-24 19:05', status: '已解析', statusTone: 'ok' },
  { id: 'd8', title: '408 真题精讲 2019–2025', subject: '408 计算机', kind: '讲义', pages: 244, size: '16.2 MB', mastery: 72, cards: 88, questions: 132, updated: '11-24 10:30', status: '已解析', statusTone: 'ok' },
  { id: 'd9', title: '数学一 660 题精练', subject: '数学一', kind: '讲义', pages: 168, size: '10.7 MB', mastery: 47, cards: 36, questions: 96, updated: '11-23 15:50', status: '待解析', statusTone: 'neutral' },
  { id: 'd10', title: '操作系统 第 4 讲 · 进程调度（视频）', subject: '408 计算机', kind: '视频', pages: 0, size: '486 MB', mastery: 86, cards: 12, questions: 0, updated: '昨天 21:40', status: '已转写', statusTone: 'brand' },
  { id: 'd11', title: '高等数学 同济版（上）', subject: '数学一', kind: '教材', pages: 448, size: '42.5 MB', mastery: 66, cards: 158, questions: 88, updated: '11-23 14:20', status: '已解析', statusTone: 'ok' },
  { id: 'd12', title: '线性代数 同济版', subject: '数学一', kind: '教材', pages: 316, size: '28.3 MB', mastery: 51, cards: 92, questions: 54, updated: '11-23 11:05', status: '已解析', statusTone: 'ok' },
  { id: 'd13', title: '概率论与数理统计 浙大版', subject: '数学一', kind: '教材', pages: 402, size: '35.7 MB', mastery: 43, cards: 76, questions: 62, updated: '11-22 19:40', status: '解析中', statusTone: 'warn' },
  { id: 'd14', title: '考研英语 单词词根词缀速记', subject: '英语一', kind: '讲义', pages: 128, size: '8.6 MB', mastery: 39, cards: 64, questions: 0, updated: '11-22 09:18', status: '已解析', statusTone: 'ok' },
  { id: 'd15', title: '英语一 作文模板与范文 30 篇', subject: '英语一', kind: '讲义', pages: 96, size: '6.4 MB', mastery: 52, cards: 28, questions: 0, updated: '11-21 20:32', status: '待解析', statusTone: 'neutral' },
  { id: 'd16', title: '政治 徐涛核心考案', subject: '政治', kind: '教材', pages: 388, size: '33.9 MB', mastery: 36, cards: 104, questions: 72, updated: '11-21 15:46', status: '已解析', statusTone: 'ok' },
  { id: 'd17', title: '408 真题卷 2020–2024 合集', subject: '408 计算机', kind: '真题卷', pages: 356, size: '22.8 MB', mastery: 69, cards: 96, questions: 214, updated: '11-20 18:22', status: '已解析', statusTone: 'ok' },
  { id: 'd18', title: '计算机网络 第 5 讲 · 应用层（视频）', subject: '408 计算机', kind: '视频', pages: 0, size: '512 MB', mastery: 74, cards: 16, questions: 0, updated: '11-20 10:08', status: '已转写', statusTone: 'brand' },
];

export const docQueue = [
  { id: 'q1', name: '计算机组成原理（第 2 版）', stage: '章节切分', progress: 62, tone: 'brand' },
  { id: 'q2', name: '数学一 660 题精练', stage: '排队中', progress: 0, tone: 'ink' },
  { id: 'q3', name: '肖秀荣 1000 题 · 补充页', stage: 'OCR 识别', progress: 34, tone: 'warn' },
];

export const docStats = {
  total: documents.length,
  parsed: documents.filter((d) => d.status === '已解析' || d.status === '已转写').length,
  cards: documents.reduce((s, d) => s + d.cards, 0),
  questions: documents.reduce((s, d) => s + d.questions, 0),
  size: '1.4 GB',
  weekNew: 3,
};

/** 存储占用分布（按资料类型），用于「存储占用」区块 */
export const docStorage = {
  total: '1.4 GB',
  used: '1.4 GB',
  usedPercent: 92,
  items: [
    { key: '教材', label: '教材', value: '624 MB', pct: 45, tone: 'brand' },
    { key: '视频', label: '视频', value: '498 MB', pct: 36, tone: 'warn' },
    { key: '真题卷', label: '真题卷', value: '168 MB', pct: 12, tone: 'ok' },
    { key: '讲义', label: '讲义', value: '96 MB', pct: 7, tone: 'ink' },
  ],
};

/** 从「S4 文档类来源」跳转 /docs?doc=d2&page=128 时抽屉里的原文切片 */
export const docReader = {
  chapter: '第 6 章 同步',
  lines: [
    { n: 126, text: '6.3 信号量（Semaphore）是 Dijkstra 于 1965 年提出的同步原语，' },
    { n: 127, text: '用一个整型变量与一个等待队列共同描述资源的可用数量。' },
    { n: 128, text: 'P 操作（wait）将信号量减一，若结果小于零则阻塞；V 操作（signal）加一，', hit: true },
    { n: 129, text: '若结果不大于零则唤醒一个等待进程。' },
    { n: 130, text: '两者必须成对出现，否则会造成死锁或资源竞争。' },
  ],
};

/* ================= 资料详情（DocumentDetail） ================= */

export const documentDetail = {
  id: 'd2',
  title: '操作系统概念（第 9 版）',
  subject: '408 计算机',
  kind: '教材',
  pages: 862,
  size: '48.2 MB',
  parsedAt: '今天 09:05',
  updated: '今天 08:20',
  mastery: 68,
  masteredPages: 586,
  cards: 214,
  dueCards: 18,
  questions: 96,
  accuracy: 72,
  chapters: [
    { id: 'c1', name: '第 1 章 导论', pages: 68, mastery: 86, cards: 22, questions: 12 },
    { id: 'c2', name: '第 3 章 进程', pages: 96, mastery: 79, cards: 38, questions: 18 },
    { id: 'c3', name: '第 5 章 CPU 调度', pages: 84, mastery: 71, cards: 32, questions: 16 },
    { id: 'c4', name: '第 6 章 同步', pages: 112, mastery: 58, cards: 44, questions: 24 },
    { id: 'c5', name: '第 8 章 内存管理', pages: 104, mastery: 64, cards: 40, questions: 14 },
    { id: 'c6', name: '第 10 章 文件系统', pages: 88, mastery: 42, cards: 38, questions: 12 },
  ],
  notes: [
    { id: 'n1', title: '信号量与 PV 操作的直觉理解', excerpt: 'P 是申请，V 是归还；负值代表等待队列长度。', time: '今天 09:12', links: 3 },
    { id: 'n2', title: '银行家算法安全性检查流程', excerpt: 'Work/Finish 两个向量，逐步找可满足进程。', time: '昨天 22:30', links: 2 },
    { id: 'n3', title: '页面置换算法 LRU 与 Clock 对比', excerpt: 'Clock 用访问位近似 LRU，开销更低。', time: '昨天 20:18', links: 4 },
    { id: 'n4', title: '进程与线程的资源差异', excerpt: '进程独立地址空间，线程共享代码段与堆。', time: '11-25 21:04', links: 1 },
    { id: 'n5', title: '死锁四个必要条件速记', excerpt: '互斥、占有并等待、非抢占、循环等待。', time: '11-24 18:46', links: 2 },
  ],
  deckGroups: [
    { label: '同步与互斥', cards: 44, due: 8, mastery: 58 },
    { label: 'CPU 调度', cards: 32, due: 4, mastery: 71 },
    { label: '内存管理', cards: 40, due: 6, mastery: 64 },
    { label: '文件系统', cards: 38, due: 0, mastery: 42 },
  ],
  questionTypes: [
    { label: '选择题', total: 60, accuracy: 78 },
    { label: '综合应用题', total: 24, accuracy: 61 },
    { label: '真题改编', total: 12, accuracy: 55 },
  ],
  reconcile: {
    source: 'GFLC 解析 v8 · 章节权重模型',
    desc: '预览只读，确认后仅回写掌握度字段，不改动笔记、卡片与题目记录。',
    items: [
      { label: '第 1 章 导论', before: 86, after: 88 },
      { label: '第 3 章 进程', before: 79, after: 79 },
      { label: '第 5 章 CPU 调度', before: 71, after: 74 },
      { label: '第 6 章 同步', before: 58, after: 63 },
      { label: '第 8 章 内存管理', before: 64, after: 62 },
      { label: '第 10 章 文件系统', before: 42, after: 47 },
    ],
    before: 68,
    after: 70,
  },
};

/* ================= 笔记（Notes） ================= */

export const noteFolders = [
  { id: 'f1', name: '全部笔记', depth: 0, count: 128 },
  { id: 'f2', name: '408 计算机', depth: 0, count: 46 },
  { id: 'f3', name: '操作系统', depth: 1, count: 18 },
  { id: 'f4', name: '计算机网络', depth: 1, count: 14 },
  { id: 'f5', name: '数据结构', depth: 1, count: 9 },
  { id: 'f6', name: '数学一', depth: 0, count: 32 },
  { id: 'f7', name: '英语一', depth: 0, count: 27 },
  { id: 'f8', name: '政治', depth: 0, count: 23 },
];

export const noteList = [
  { id: 'n1', title: '信号量与 PV 操作的直觉理解', excerpt: 'P 是申请，V 是归还；负值代表等待队列长度。', folder: '操作系统', words: 862, links: 3, updated: '09:12' },
  { id: 'n2', title: '银行家算法安全性检查流程', excerpt: 'Work/Finish 两个向量，逐步找可满足进程。', folder: '操作系统', words: 1240, links: 2, updated: '昨天 22:30' },
  { id: 'n3', title: '页面置换算法 LRU 与 Clock 对比', excerpt: 'Clock 用访问位近似 LRU，开销更低。', folder: '操作系统', words: 638, links: 4, updated: '昨天 20:18' },
  { id: 'n4', title: '进程与线程的资源差异', excerpt: '进程独立地址空间，线程共享代码段与堆。', folder: '操作系统', words: 420, links: 1, updated: '11-25 21:04' },
  { id: 'n5', title: '死锁四个必要条件速记', excerpt: '互斥、占有并等待、非抢占、循环等待。', folder: '操作系统', words: 316, links: 2, updated: '11-24 18:46' },
  { id: 'n6', title: 'TCP 拥塞控制四算法对比', excerpt: '慢启动、拥塞避免、快重传、快恢复。', folder: '计算机网络', words: 980, links: 5, updated: '11-24 09:20' },
  { id: 'n7', title: '三次握手为什么不是两次', excerpt: '防止失效连接请求突然到达服务端。', folder: '计算机网络', words: 512, links: 2, updated: '11-23 21:10' },
  { id: 'n8', title: '红黑树插入的三种修正情形', excerpt: '变色、左旋、右旋的组合判断。', folder: '数据结构', words: 748, links: 3, updated: '11-22 16:32' },
  { id: 'n9', title: '二重积分换元法的雅可比行列式', excerpt: '极坐标下 r 就是雅可比行列式的值。', folder: '数学一', words: 604, links: 1, updated: '11-22 10:08' },
  { id: 'n10', title: '英语一 阅读长难句拆解 03', excerpt: '定语从句嵌套时的主干剥离方法。', folder: '英语一', words: 386, links: 2, updated: '11-21 19:44' },
  { id: 'n11', title: 'B 树与 B+ 树在磁盘索引中的取舍', excerpt: 'B+ 树非叶结点只存索引，扇出更大、范围查询更友好。', folder: '数据结构', words: 856, links: 3, updated: '11-21 09:02' },
  { id: 'n12', title: '矩阵相似对角化与特征值重数的关系', excerpt: '几何重数等于代数重数才是充要条件。', folder: '数学一', words: 528, links: 2, updated: '11-20 21:16' },
  { id: 'n13', title: '唯物史观两大基本规律背诵口诀', excerpt: '生产力决定生产关系，经济基础决定上层建筑。', folder: '政治', words: 342, links: 1, updated: '11-20 16:40' },
  { id: 'n14', title: '浮点数规格化与舍入误差的来源', excerpt: '阶码溢出与尾数舍入是误差两大主因。', folder: '408 计算机', words: 690, links: 2, updated: '11-19 20:08' },
  { id: 'n15', title: '英语一 完形填空上下文信号词', excerpt: '转折、因果、递进三类信号词锁定答案。', folder: '英语一', words: 458, links: 1, updated: '11-18 22:34' },
];

/** 笔记页 · 最近编辑时间线 */
export const notesRecent = [
  { id: 'nr1', title: '信号量与 PV 操作的直觉理解', folder: '操作系统', time: '今天 09:12', action: '编辑正文' },
  { id: 'nr2', title: 'TCP 拥塞控制四算法对比', folder: '计算机网络', time: '今天 09:02', action: '补充双链' },
  { id: 'nr3', title: '页面置换算法 LRU 与 Clock 对比', folder: '操作系统', time: '昨天 22:30', action: 'AI 补写' },
  { id: 'nr4', title: '红黑树插入的三种修正情形', folder: '数据结构', time: '昨天 20:18', action: '调整大纲' },
];

/** 笔记页 · 右侧统计卡 */
export const noteStats = {
  total: noteList.length,
  words: noteList.reduce((s, n) => s + n.words, 0),
  links: noteList.reduce((s, n) => s + n.links, 0),
  weekNew: 4,
  dist: [
    { label: '操作系统', value: 5, tone: 'brand' },
    { label: '计算机网络', value: 3, tone: 'ok' },
    { label: '数据结构', value: 3, tone: 'warn' },
    { label: '数学一', value: 3, tone: 'ink' },
  ],
};

export const noteOpen = {
  id: 'n1',
  title: '信号量与 PV 操作的直觉理解',
  folder: '408 计算机 / 操作系统',
  updated: '今天 09:12',
  words: 862,
  readMinutes: 4,
  tags: ['同步', '信号量', '高频考点'],
  source: '来源《操作系统概念（第 9 版）》第 6 章 · 页码 128',
  blocks: [
    { type: 'p', text: '把信号量理解成「一张有固定名额的票台」：名额用整型变量 S 表示，排队的人组成等待队列。' },
    { type: 'h2', text: '一、P 操作（wait）' },
    { type: 'p', text: 'S 减一；若 S < 0，说明名额已发完，当前进程进入等待队列并阻塞。因此 S 的负值绝对值就是等待队列长度，这一点在 [[银行家算法安全性检查流程]] 里也用到。' },
    { type: 'h2', text: '二、V 操作（signal）' },
    { type: 'p', text: 'S 加一；若 S ≤ 0，说明还有进程在等，需要唤醒其中一个。P、V 必须成对出现，漏掉 V 会死锁，漏掉 P 会让互斥失效。' },
    { type: 'quote', text: '易错点：S 的初值等于可用资源数，而不是进程数；互斥信号量初值为 1。' },
    { type: 'p', text: '对比 [[进程与线程的资源差异]]：信号量保护的是临界资源，不是线程本身，跨进程同样适用。' },
  ],
  backlinks: [
    { id: 'bl1', title: '死锁四个必要条件速记', time: '11-24' },
    { id: 'bl2', title: '银行家算法安全性检查流程', time: '昨天' },
    { id: 'bl3', title: '页面置换算法 LRU 与 Clock 对比', time: '昨天' },
  ],
  aiActions: ['续写本节小结', '生成 5 张卡片', '补一个例题'],
};

/* ================= 题库（QuestionBanks） ================= */

export const bankTree = {
  subjects: [
    { id: 'b1', name: '408 计算机', count: 6 },
    { id: 'b2', name: '数学一', count: 4 },
    { id: 'b3', name: '英语一', count: 3 },
    { id: 'b4', name: '政治', count: 3 },
  ],
  years: [
    { id: 'y1', name: '2026', count: 4 },
    { id: 'y2', name: '2025', count: 4 },
    { id: 'y3', name: '2024', count: 3 },
    { id: 'y4', name: '更早年份', count: 5 },
  ],
  kinds: [
    { id: 'k1', name: '真题', count: 4 },
    { id: 'k2', name: '模拟', count: 3 },
    { id: 'k3', name: '章节', count: 4 },
    { id: 'k4', name: '错题', count: 2 },
  ],
};

export const questionBanks = [
  { id: 'qb1', name: '408 真题卷 2025', subject: '408 计算机', year: '2025', kind: '真题', questions: 47, accuracy: 74, last: '今天 08:40', due: 12 },
  { id: 'qb2', name: '408 模拟卷（三）', subject: '408 计算机', year: '2026', kind: '模拟', questions: 47, accuracy: 68, last: '昨天 21:15', due: 0 },
  { id: 'qb3', name: '操作系统 章节题 · 内存管理', subject: '408 计算机', year: '2026', kind: '章节', questions: 32, accuracy: 81, last: '昨天 19:30', due: 6 },
  { id: 'qb4', name: '计算机网络 章节题 · 传输层', subject: '408 计算机', year: '2026', kind: '章节', questions: 28, accuracy: 63, last: '11-25 22:02', due: 4 },
  { id: 'qb5', name: '数学一 真题卷 2025', subject: '数学一', year: '2025', kind: '真题', questions: 23, accuracy: 66, last: '11-25 16:48', due: 8 },
  { id: 'qb6', name: '数学一 660 题 · 高数上', subject: '数学一', year: '2026', kind: '章节', questions: 180, accuracy: 59, last: '11-24 20:10', due: 0 },
  { id: 'qb7', name: '英语一 阅读真题 2024', subject: '英语一', year: '2024', kind: '真题', questions: 20, accuracy: 72, last: '11-24 09:36', due: 2 },
  { id: 'qb8', name: '政治 肖八 选择题', subject: '政治', year: '2026', kind: '模拟', questions: 100, accuracy: 48, last: '11-23 21:20', due: 10 },
  { id: 'qb9', name: '408 错题重练 · 同步与死锁', subject: '408 计算机', year: '2026', kind: '错题', questions: 24, accuracy: 57, last: '11-23 18:04', due: 3 },
];

export const bankStats = {
  folders: 16,
  total: questionBanks.reduce((s, b) => s + b.questions, 0),
  banks: questionBanks.length,
  accuracy: 67,
  weekNew: 2,
  importedPdf: 5,
};

/** 题库页 · 题库概览（右栏统计卡） */
export const bankOverview = {
  banks: questionBanks.length,
  questions: questionBanks.reduce((s, b) => s + b.questions, 0),
  parsed: 7,
  pending: 2,
  chapters: 42,
  accuracy: 67,
  dist: [
    { label: '408 计算机', value: 6, tone: 'brand' },
    { label: '数学一', value: 4, tone: 'ok' },
    { label: '英语一', value: 3, tone: 'warn' },
    { label: '政治', value: 3, tone: 'ink' },
  ],
};

/** 题库页 · 解析队列 */
export const bankQueue = {
  processing: 2,
  queued: 1,
  items: [
    { id: 'bq1', name: '408 真题卷 2026（扫描版）', stage: '切题中', progress: 62, tone: 'brand' },
    { id: 'bq2', name: '数学一 冲刺押题卷（三）', stage: 'OCR 识别', progress: 34, tone: 'warn' },
    { id: 'bq3', name: '政治 时政选择题 12 月', stage: '排队中', progress: 0, tone: 'ink' },
  ],
};

/* ================= 卡包（Decks） ================= */

export const deckSubjects = ['全部', '408 计算机', '数学一', '英语一', '政治'];

/** 章节卡包网格：正面标题 / 张数 / 掌握度 / 到期数 */
export const deckChapters = [
  { id: 'dk1', title: '操作系统 · 内存管理', subject: '408 计算机', cards: 86, mastery: 64, due: 18, front: '虚拟内存解决了什么问题？', last: '今天 09:40' },
  { id: 'dk2', title: '操作系统 · 进程与同步', subject: '408 计算机', cards: 74, mastery: 71, due: 8, front: 'P、V 操作的语义与负值含义？', last: '今天 08:12' },
  { id: 'dk3', title: '数据结构 · 树与图', subject: '408 计算机', cards: 92, mastery: 58, due: 12, front: '红黑树插入后如何修正？', last: '昨天 22:10' },
  { id: 'dk4', title: '计算机网络 · 传输层', subject: '408 计算机', cards: 68, mastery: 66, due: 6, front: 'TCP 拥塞控制的四个算法？', last: '昨天 20:34' },
  { id: 'dk5', title: '数学一 · 高数 极限与连续', subject: '数学一', cards: 124, mastery: 62, due: 9, front: '等价无穷小替换成立的条件？', last: '11-25 21:04' },
  { id: 'dk6', title: '数学一 · 线代 特征值', subject: '数学一', cards: 58, mastery: 47, due: 4, front: '相似对角化的充要条件？', last: '11-25 19:20' },
  { id: 'dk7', title: '英语一 · 阅读长难句', subject: '英语一', cards: 96, mastery: 55, due: 3, front: '定语从句嵌套时如何剥离主干？', last: '11-24 20:16' },
  { id: 'dk8', title: '政治 · 马原 辩证法', subject: '政治', cards: 112, mastery: 41, due: 5, front: '矛盾普遍性与特殊性的关系？', last: '11-24 09:02' },
];

/** 熟练度筛选档位 */
export const deckProficiency = ['全部', '生疏', '一般', '熟练', '已掌握'];

/** 卡片浏览器表格行 */
export const deckCards = [
  { id: 'dc1', front: '页表项中通常包含哪些字段？', chapter: '操作系统 · 内存管理', level: '一般', due: '今天', reviews: 7, tags: ['内存管理', '定义'] },
  { id: 'dc2', front: '虚拟内存与交换区的区别是什么？', chapter: '操作系统 · 内存管理', level: '生疏', due: '今天', reviews: 3, tags: ['内存管理', '易错点'] },
  { id: 'dc3', front: 'LRU 与 Clock 算法的时间开销对比？', chapter: '操作系统 · 内存管理', level: '熟练', due: '明天', reviews: 11, tags: ['置换算法', '对比'] },
  { id: 'dc4', front: 'P 操作中信号量为负值代表什么？', chapter: '操作系统 · 进程与同步', level: '已掌握', due: '3 天后', reviews: 16, tags: ['信号量', '高频考点'] },
  { id: 'dc5', front: '死锁成立的四个必要条件？', chapter: '操作系统 · 进程与同步', level: '一般', due: '今天', reviews: 8, tags: ['死锁', '定义'] },
  { id: 'dc6', front: '红黑树插入修正的三种情形？', chapter: '数据结构 · 树与图', level: '生疏', due: '今天', reviews: 2, tags: ['红黑树', '高频考点'] },
  { id: 'dc7', front: '拓扑排序的两种实现与复杂度？', chapter: '数据结构 · 树与图', level: '一般', due: '明天', reviews: 6, tags: ['图', '对比'] },
  { id: 'dc8', front: 'TCP 拥塞控制四个算法的触发条件？', chapter: '计算机网络 · 传输层', level: '熟练', due: '今天', reviews: 12, tags: ['TCP', '高频考点'] },
  { id: 'dc9', front: '等价无穷小替换不成立的典型场景？', chapter: '数学一 · 高数 极限与连续', level: '生疏', due: '今天', reviews: 4, tags: ['极限', '易错点'] },
  { id: 'dc10', front: '相似对角化与特征值重数的关系？', chapter: '数学一 · 线代 特征值', level: '一般', due: '3 天后', reviews: 5, tags: ['线代', '公式'] },
];

export const deckStats = {
  packs: deckChapters.length,
  cards: deckChapters.reduce((s, d) => s + d.cards, 0),
  due: deckChapters.reduce((s, d) => s + d.due, 0),
  mastery: 58,
  newToday: 6,
  syncAt: '今天 09:40',
};

/** 新建 / 编辑卡片弹窗的字段与选项 */
export const deckEditor = {
  newTitle: '新建卡片',
  editTitle: '编辑卡片',
  chapterOptions: deckChapters.map((d) => d.title),
  tagOptions: ['高频考点', '易错点', '定义', '公式', '对比', '真题'],
  draft: {
    front: '页表项中通常包含哪些字段？',
    back: '页框号、有效位、访问位、脏位、保护位；缺页时由有效位判定并触发缺页中断。',
    chapter: '操作系统 · 内存管理',
    tags: ['高频考点', '定义'],
  },
};

/* ================= 学习（Study） ================= */

export const studyModes = [
  { key: 'quiz', label: '刷题', count: 32, hint: '408 真题卷 2025 · 进行中' },
  { key: 'recite', label: '背诵', count: 18, hint: '5 个卡包 · 今日到期 18 张' },
  { key: 'exam', label: '模考', count: 3, hint: '3 套卷未完成 · 最近 96 分' },
  { key: 'wrong', label: '错题', count: 26, hint: '本周新增 6 道 · 待重做 26 道' },
];

/** 刷题区 */
export const quizSession = {
  bank: '408 真题卷 2025 · 操作系统',
  index: 12,
  total: 20,
  difficulty: '中等',
  spent: '01:12',
  kind: '单项选择题',
  stem: '在页式存储管理中，页面大小为 4 KB。若某进程的逻辑地址为 0x2A1F，则该地址对应的页号与页内偏移分别为（　）。',
  options: [
    { key: 'A', text: '页号 2，页内偏移 0xA1F' },
    { key: 'B', text: '页号 2，页内偏移 0x21F' },
    { key: 'C', text: '页号 10，页内偏移 0xA1F' },
    { key: 'D', text: '页号 10，页内偏移 0x21F' },
  ],
  picked: 'A',
  answer: 'B',
  explain: [
    '页内偏移取逻辑地址低 12 位（4 KB = 2^12），0x2A1F 的低 12 位为 0x21F；剩余高位 0x2 即页号，故答案为 B。',
    '易错点：把 4 KB 误当 2^10，会算成页号 10、偏移 0xA1F，即选项 C。',
  ],
  tags: ['内存管理', '页式存储'],
  card: [
    'right', 'right', 'wrong', 'right', 'right',
    'right', 'wrong', 'right', 'right', 'wrong',
    'right', 'cur', 'todo', 'todo', 'todo',
    'todo', 'todo', 'todo', 'todo', 'todo',
  ],
  stats: { done: 11, right: 8, wrong: 3, left: 9 },
  settings: [
    { label: '只做未做', value: '开启' },
    { label: '错题自动加入', value: '开启' },
    { label: '计时上限', value: '90 秒 / 题' },
  ],
};

/** 刷题 · 同类真题推荐 */
export const quizRelated = [
  { id: 'qr1', tag: '2021 · 408', stem: '段式存储管理中，段表项通常不包含哪个字段？', difficulty: '简单', from: '408 真题卷 2021' },
  { id: 'qr2', tag: '2020 · 408', stem: '引入快表（TLB）后，有效访存时间如何计算？', difficulty: '中等', from: '408 真题卷 2020' },
  { id: 'qr3', tag: '2019 · 408', stem: '请求分页系统中，缺页中断由硬件还是软件产生？', difficulty: '简单', from: '408 真题卷 2019' },
  { id: 'qr4', tag: '章节题', stem: '页面大小从 4 KB 增到 8 KB，页内偏移占几位？', difficulty: '中等', from: '操作系统 章节题' },
];

/** 刷题 · 本题选项分布 */
export const quizOptionStats = [
  { key: 'A', pct: 32, tone: 'brand' },
  { key: 'B', pct: 28, tone: 'ok' },
  { key: 'C', pct: 24, tone: 'warn' },
  { key: 'D', pct: 16, tone: 'ink' },
];

/** 刷题 · 相关知识点 chip */
export const quizRelatedPoints = ['页式存储', '页内偏移计算', '逻辑地址拆分', '缺页中断', '快表 TLB', '段页式对比'];

/** 背诵区：卡包分组 */
export const reciteGroups = [
  { id: 'rg1', label: '操作系统 · 内存管理', cards: 86, due: 18, mastery: 64 },
  { id: 'rg2', label: '操作系统 · 进程与同步', cards: 74, due: 8, mastery: 71 },
  { id: 'rg3', label: '数据结构 · 树与图', cards: 92, due: 12, mastery: 58 },
  { id: 'rg4', label: '数学一 · 高数 极限与连续', cards: 124, due: 9, mastery: 62 },
  { id: 'rg5', label: '政治 · 马原 辩证法', cards: 112, due: 5, mastery: 41 },
];

/** 背诵区：卡片墙（每张都是一整块知识点） */
export const reciteCards = [
  {
    id: 'rc1',
    chapter: '操作系统 · 内存管理',
    front: '虚拟内存解决了什么问题？',
    point: [
      '① 逻辑地址空间可大于物理内存，按需调页，程序不必整体装入。',
      '② 每个进程拥有独立地址空间，页表做隔离，越界访问即缺页异常。',
      '③ 以页为单位换入换出，减少 I/O 次数，提高内存利用率。',
      '④ 支持共享页与写时复制，fork 时无需复制全部数据。',
    ],
    tip: '易错：虚拟内存不等于外存，交换区只是后备存储，访问仍要经过页表。',
    tags: ['内存管理', '高频考点'],
    level: '一般',
    reviews: 7,
  },
  {
    id: 'rc2',
    chapter: '操作系统 · 内存管理',
    front: '缺页中断的处理流程？',
    point: [
      '① 地址变换时有效位为 0，硬件陷入缺页中断，保存现场。',
      '② 操作系统在交换区找到该页，选择空闲页框；无空闲则执行置换算法。',
      '③ 若被换出页脏位为 1，先写回磁盘，再读入目标页。',
      '④ 修改页表与快表，恢复现场，重新执行触发指令。',
    ],
    tip: '缺页中断属于内中断，指令会重新执行；而 I/O 中断是外中断。',
    tags: ['缺页', '流程'],
    level: '生疏',
    reviews: 3,
  },
  {
    id: 'rc3',
    chapter: '操作系统 · 内存管理',
    front: 'LRU / Clock / FIFO 三种置换算法对比？',
    point: [
      '① FIFO：按装入顺序淘汰，实现简单，会出现 Belady 异常。',
      '② LRU：淘汰最久未使用页，命中率最好，但需栈或时间戳，开销大。',
      '③ Clock：用访问位近似 LRU，指针扫描并清零访问位，开销接近 FIFO。',
      '④ 改进型 Clock 同时看访问位与脏位，优先淘汰未访问且干净页。',
    ],
    tip: '只有 FIFO 会出现 Belady 异常：页框增多而缺页率上升。',
    tags: ['置换算法', '对比'],
    level: '熟练',
    reviews: 11,
  },
  {
    id: 'rc4',
    chapter: '操作系统 · 进程与同步',
    front: '信号量 P、V 操作的语义与负值含义？',
    point: [
      '① P(wait)：S 减 1；若 S < 0，进程阻塞并进入等待队列。',
      '② V(signal)：S 加 1；若 S ≤ 0，唤醒一个等待进程。',
      '③ S 的负值绝对值等于等待队列长度；互斥信号量初值为 1。',
      '④ P、V 必须成对出现，漏 V 死锁，漏 P 互斥失效。',
    ],
    tip: 'S 初值等于可用资源数，不是进程数。',
    tags: ['信号量', '高频考点'],
    level: '已掌握',
    reviews: 16,
  },
  {
    id: 'rc5',
    chapter: '操作系统 · 进程与同步',
    front: '死锁的四个必要条件？',
    point: [
      '① 互斥：资源一次只能被一个进程占用。',
      '② 占有并等待：持有资源的同时申请新资源。',
      '③ 非抢占：资源只能由持有者主动释放。',
      '④ 循环等待：存在进程与资源的环形等待链。',
    ],
    tip: '四个条件同时成立才可能死锁；破坏任一条件即可预防。',
    tags: ['死锁', '定义'],
    level: '一般',
    reviews: 8,
  },
  {
    id: 'rc6',
    chapter: '数据结构 · 树与图',
    front: '红黑树插入后的修正情形？',
    point: [
      '① 父结点为黑：无需修正，插入完成。',
      '② 父红且叔红：父与叔变黑、祖父变红，指针上移两层继续判断。',
      '③ 父红且叔黑，当前结点为内侧：先旋转父结点转为外侧。',
      '④ 父红且叔黑，外侧情形：父变黑、祖父变红，对祖父旋转。',
    ],
    tip: '修正只需旋转 ≤ 2 次、变色 O(log n) 次，这是红黑树优于 AVL 的地方。',
    tags: ['红黑树', '高频考点'],
    level: '生疏',
    reviews: 2,
  },
  {
    id: 'rc7',
    chapter: '数据结构 · 树与图',
    front: '拓扑排序的两种实现与复杂度？',
    point: [
      '① Kahn 算法：反复取入度为 0 的顶点入队，删除其出边。',
      '② DFS 算法：后序逆序输出，需检测回边判断有环。',
      '③ 两者时间复杂度均为 O(V + E)，空间 O(V)。',
      '④ 拓扑序不唯一，说明图中存在并行分支。',
    ],
    tip: '输出顶点数少于 V 即有环，这是判环的常用手段。',
    tags: ['图', '对比'],
    level: '一般',
    reviews: 6,
  },
  {
    id: 'rc8',
    chapter: '计算机网络 · 传输层',
    front: 'TCP 三次握手为什么不是两次？',
    point: [
      '① 防止失效的历史连接请求突然到达，服务端误开连接。',
      '② 两次握手无法让双方都确认对方的收发能力。',
      '③ 第三次 ACK 携带序号，保证初始序号同步。',
      '④ 三次是满足可靠同步的最小次数。',
    ],
    tip: 'SYN 洪泛攻击利用的正是半连接队列，可用 SYN Cookie 缓解。',
    tags: ['TCP', '高频考点'],
    level: '熟练',
    reviews: 13,
  },
  {
    id: 'rc9',
    chapter: '计算机网络 · 传输层',
    front: 'TCP 拥塞控制四个算法的触发条件？',
    point: [
      '① 慢启动：cwnd 从 1 起按指数增长，至 ssthresh 结束。',
      '② 拥塞避免：cwnd 线性加 1，每个 RTT 增 1 个 MSS。',
      '③ 快重传：收到 3 个重复 ACK 立即重传丢失段。',
      '④ 快恢复：ssthresh 与 cwnd 减半，直接进入拥塞避免。',
    ],
    tip: '超时重传时 cwnd 回到 1，与快恢复的减半处理不同。',
    tags: ['TCP', '对比'],
    level: '一般',
    reviews: 9,
  },
  {
    id: 'rc10',
    chapter: '数学一 · 高数 极限与连续',
    front: '等价无穷小替换成立的条件？',
    point: [
      '① 只能在乘除因子中直接替换，加减项需通分或泰勒展开。',
      '② 替换后极限必须存在，且替换不改变主部阶数。',
      '③ 常用：sin x ~ x、ln(1+x) ~ x、1-cos x ~ x²/2。',
      '④ 加减替换需保证低阶项不相互抵消。',
    ],
    tip: '典型反例：x→0 时 (sin x - x)/x³ 不能把 sin x 换成 x。',
    tags: ['极限', '易错点'],
    level: '生疏',
    reviews: 4,
  },
  {
    id: 'rc11',
    chapter: '数学一 · 线代 特征值',
    front: '相似对角化的充要条件？',
    point: [
      '① n 阶矩阵有 n 个线性无关的特征向量。',
      '② 每个特征值的几何重数等于代数重数。',
      '③ 有 n 个互不相同的特征值是充分条件，不是必要条件。',
      '④ 实对称矩阵一定可以正交对角化，A = QΛQᵀ。',
    ],
    tip: '可对角化与可逆无关：奇异矩阵同样可能可对角化。',
    tags: ['线代', '公式'],
    level: '一般',
    reviews: 5,
  },
  {
    id: 'rc12',
    chapter: '政治 · 马原 辩证法',
    front: '矛盾普遍性与特殊性的关系？',
    point: [
      '① 普遍性即共性，特殊性即个性，二者相互联结而存在。',
      '② 共性寓于个性之中，个性中包含共性。',
      '③ 矛盾普遍性与特殊性是矛盾问题的精髓。',
      '④ 方法论：具体问题具体分析，把一般原理与具体实际结合。',
    ],
    tip: '常见考点：中国特色社会主义体现普遍性与特殊性的统一。',
    tags: ['马原', '定义'],
    level: '生疏',
    reviews: 3,
  },
];

/** 模考区 */
export const examPaper = {
  title: '408 计算机 模拟卷（三）',
  subject: '408 计算机',
  questions: 47,
  minutes: 180,
  full: 150,
  openedAt: '今天 09:00',
  deadline: '今天 12:00',
  status: '待开始',
  types: [
    { label: '单项选择题', count: 40, score: 80 },
    { label: '综合应用题', count: 7, score: 70 },
  ],
  subjects: [
    { label: '数据结构', count: 12, score: 40 },
    { label: '计算机组成原理', count: 11, score: 35 },
    { label: '操作系统', count: 12, score: 40 },
    { label: '计算机网络', count: 12, score: 35 },
  ],
  rules: [
    '闭卷计时 180 分钟，中途退出本次成绩作废。',
    '提交后客观题即时批改，主观题 24 小时内复核。',
    '错题自动进入错题本，按遗忘曲线排期重做。',
  ],
};

export const examHistory = [
  { id: 'eh1', name: '408 模拟卷（二）', date: '11-24', score: 96, full: 150, minutes: 172, accuracy: 61 },
  { id: 'eh2', name: '408 真题卷 2025', date: '11-22', score: 112, full: 150, minutes: 168, accuracy: 74 },
  { id: 'eh3', name: '408 模拟卷（一）', date: '11-19', score: 88, full: 150, minutes: 180, accuracy: 58 },
  { id: 'eh4', name: '数学一 模拟卷（二）', date: '11-17', score: 92, full: 150, minutes: 175, accuracy: 66 },
  { id: 'eh5', name: '408 真题卷 2024', date: '11-14', score: 104, full: 150, minutes: 170, accuracy: 70 },
  { id: 'eh6', name: '政治 肖八 选择题', date: '11-12', score: 38, full: 50, minutes: 42, accuracy: 76 },
  { id: 'eh7', name: '英语一 真题 2024', date: '11-10', score: 61, full: 100, minutes: 165, accuracy: 72 },
];

/** 错题本 */
export const wrongList = [
  { id: 'w1', stem: '页式存储中逻辑地址 0x2A1F 的页号与偏移？', from: '408 真题卷 2025', chapter: '内存管理', times: 3, last: '今天 09:12', reason: '页大小与位数换算', level: '生疏' },
  { id: 'w2', stem: 'Clock 算法中被置换页的访问位如何处理？', from: '408 模拟卷（三）', chapter: '内存管理', times: 2, last: '今天 08:50', reason: '算法细节模糊', level: '一般' },
  { id: 'w3', stem: '银行家算法安全性检查的结束条件？', from: '操作系统 章节题', chapter: '进程与同步', times: 2, last: '昨天 22:04', reason: 'Finish 向量判定', level: '一般' },
  { id: 'w4', stem: '红黑树插入后最多需要几次旋转？', from: '408 真题卷 2024', chapter: '树与图', times: 4, last: '昨天 21:30', reason: '修正情形记混', level: '生疏' },
  { id: 'w5', stem: '拓扑排序输出顶点数少于 n 说明什么？', from: '数据结构 章节题', chapter: '树与图', times: 1, last: '昨天 20:12', reason: '判环结论遗忘', level: '熟练' },
  { id: 'w6', stem: 'TCP 快恢复与超时重传的 cwnd 差异？', from: '408 真题卷 2025', chapter: '传输层', times: 3, last: '11-25 21:46', reason: '两套处理混淆', level: '生疏' },
  { id: 'w7', stem: '加法项中能否直接使用等价无穷小替换？', from: '数学一 660 题', chapter: '极限与连续', times: 5, last: '11-25 19:38', reason: '未考虑主部抵消', level: '生疏' },
  { id: 'w8', stem: '几何重数与代数重数相等意味着什么？', from: '数学一 真题卷 2025', chapter: '特征值', times: 2, last: '11-24 20:22', reason: '充要条件表述不清', level: '一般' },
];

export const wrongStats = {
  total: wrongList.length,
  weekNew: 6,
  redo: 26,
  fixed: 14,
  dist: [
    { label: '内存管理', value: 8, tone: 'warn' },
    { label: '树与图', value: 6, tone: 'brand' },
    { label: '传输层', value: 5, tone: 'brand' },
    { label: '极限与连续', value: 4, tone: 'ok' },
  ],
};

/* ================= 复习（Review） ================= */

export const reviewQueue = {
  done: 3,
  total: 12,
  items: [
    { n: 1, chapter: '内存管理', state: 'done' },
    { n: 2, chapter: '内存管理', state: 'done' },
    { n: 3, chapter: '内存管理', state: 'done' },
    { n: 4, chapter: '内存管理', state: 'cur' },
    { n: 5, chapter: '进程与同步', state: 'todo' },
    { n: 6, chapter: '进程与同步', state: 'todo' },
    { n: 7, chapter: '内存管理', state: 'todo' },
    { n: 8, chapter: '树与图', state: 'todo' },
    { n: 9, chapter: '树与图', state: 'todo' },
    { n: 10, chapter: '传输层', state: 'todo' },
    { n: 11, chapter: '内存管理', state: 'todo' },
    { n: 12, chapter: '内存管理', state: 'todo' },
  ],
};

export const reviewCard = {
  id: 'rv4',
  chapter: '操作系统 · 内存管理',
  front: '请求分页系统中，一次缺页中断的完整处理流程是什么？',
  back: [
    '① 地址变换时页表项有效位为 0，硬件产生缺页中断并保存现场。',
    '② 操作系统检查地址合法性，越界则终止进程。',
    '③ 在交换区定位页面；若内存无空闲页框，按置换算法选择牺牲页。',
    '④ 牺牲页脏位为 1 时先写回磁盘，再调入目标页并更新页表与快表。',
    '⑤ 恢复现场，重新执行被中断的指令。',
  ],
  tip: '易错：缺页中断属于内中断，处理后指令重新执行；I/O 中断则继续执行下一条。',
  tags: ['缺页', '高频考点', '流程'],
  reviews: 9,
  lapses: 2,
  lastReview: '11-24 21:36',
  source: '《操作系统概念（第 9 版）》第 8 章 · P312',
  interval: '当前间隔 3 天 · 熟练度 一般',
};

export const reviewGrades = [
  { key: 'forgot', label: '忘记', hint: '明天', tone: 'bad' },
  { key: 'hard', label: '费力', hint: '3 天后', tone: 'warn' },
  { key: 'good', label: '记住', hint: '7 天后', tone: 'brand' },
  { key: 'easy', label: '秒懂', hint: '14 天后', tone: 'ok' },
];

export const reviewSnooze = [
  { key: 'tomorrow', label: '明天' },
  { key: '3d', label: '3 天后' },
  { key: '7d', label: '7 天后' },
];

export const reviewStats = {
  due: 42,
  todayTotal: 12,
  done: 3,
  left: 9,
  minutes: 12,
  avgPerCard: '4 分 10 秒',
  recall: 76,
  streak: 23,
  tomorrow: 42,
};

export const reviewToday = [
  { id: 'rt1', time: '09:42', chapter: '内存管理', front: '虚拟内存解决了什么问题？', grade: '记住' },
  { id: 'rt2', time: '09:38', chapter: '内存管理', front: 'LRU 与 Clock 的开销差异？', grade: '秒懂' },
  { id: 'rt3', time: '09:31', chapter: '内存管理', front: '页表项包含哪些字段？', grade: '费力' },
];

/** 记忆曲线预告：未来 7 天到期卡片 */
export const upcomingReviews = {
  total: 98,
  days: [
    { key: 'd0', label: '今天', value: 12 },
    { key: 'd1', label: '明天', value: 18 },
    { key: 'd2', label: '周三', value: 9 },
    { key: 'd3', label: '周四', value: 22 },
    { key: 'd4', label: '周五', value: 15 },
    { key: 'd5', label: '周六', value: 8 },
    { key: 'd6', label: '周日', value: 14 },
  ],
};

/* ===== 计划 Plans ===== */

export const planHeader = {
  week: '第 48 周 · 11/23 - 11/29',
  done: 18,
  total: 26,
  percent: 68,
  daysLeft: 2,
  streak: 12,
  hours: 21.5,
  focus: '本周重点：操作系统 内存管理 + 高数极限与导数',
};

export const planGoalBars = [
  { id: 'pg1', label: '数学一', detail: '高数强化 · 第 6 章 极限与导数', value: 6, total: 8, tone: 'brand' },
  { id: 'pg2', label: '408 专业课', detail: '操作系统 · 内存管理', value: 5, total: 8, tone: 'ok' },
  { id: 'pg3', label: '英语一', detail: '阅读真题 2018 Text2-3', value: 4, total: 6, tone: 'warn' },
  { id: 'pg4', label: '政治', detail: '肖秀荣1000题 · 马原单选', value: 3, total: 4, tone: 'ink' },
];

export const planTodayTasks = [
  { id: 'pt1', time: '08:00', title: '操作系统 · 内存管理 精读', subject: '408', minutes: 90, done: true },
  { id: 'pt2', time: '09:40', title: '高数 · 极限与导数 例题 12 道', subject: '数学一', minutes: 90, done: true },
  { id: 'pt3', time: '11:20', title: '复习卡片 40 张', subject: '复习', minutes: 40, done: true },
  { id: 'pt4', time: '14:00', title: '数据结构 · 树与二叉树', subject: '408', minutes: 90, done: false },
  { id: 'pt5', time: '16:50', title: '错题回看 6 题', subject: '错题', minutes: 40, done: false },
  { id: 'pt6', time: '20:40', title: '政治 · 马原单选 50 题', subject: '政治', minutes: 50, done: false },
];

export const planTemplates = [
  { id: 'tp1', name: '冲刺 30 天', detail: '每天 3 个任务 · 数学一 6 章全覆盖', days: 30, tasks: 90, tag: '热门', tone: 'brand' },
  { id: 'tp2', name: '408 四科轮转', detail: '每天 2 个任务 · OS / CN / CO / DS 轮转', days: 28, tasks: 56, tag: '推荐', tone: 'ok' },
  { id: 'tp3', name: '英语一真题精读', detail: '每周 3 篇阅读 + 生词卡片', days: 21, tasks: 42, tag: '阅读', tone: 'warn' },
  { id: 'tp4', name: '政治 1000 题打卡', detail: '每天 50 题 + 错题整理', days: 20, tasks: 20, tag: '刷题', tone: 'ink' },
];

export const planStats = {
  totalTasks: 26,
  doneTasks: 18,
  focusHours: 21.5,
  streak: 12,
  monthDone: 214,
  monthTotal: 268,
};

export const planMonth = {
  year: 2026,
  month: 11,
  label: '2026 年 11 月',
  today: 27,
  weekdays: ['一', '二', '三', '四', '五', '六', '日'],
  weeks: [
    { key: 'w1', days: [ { d: 26, m: 10, out: true, tasks: 0, today: false }, { d: 27, m: 10, out: true, tasks: 0, today: false }, { d: 28, m: 10, out: true, tasks: 0, today: false }, { d: 29, m: 10, out: true, tasks: 0, today: false }, { d: 30, m: 10, out: true, tasks: 0, today: false }, { d: 31, m: 10, out: true, tasks: 0, today: false }, { d: 1, m: 11, out: false, tasks: 0, today: false } ] },
    { key: 'w2', days: [ { d: 2, m: 11, out: false, tasks: 1, today: false }, { d: 3, m: 11, out: false, tasks: 4, today: false }, { d: 4, m: 11, out: false, tasks: 3, today: false }, { d: 5, m: 11, out: false, tasks: 2, today: false }, { d: 6, m: 11, out: false, tasks: 2, today: false }, { d: 7, m: 11, out: false, tasks: 3, today: false }, { d: 8, m: 11, out: false, tasks: 0, today: false } ] },
    { key: 'w3', days: [ { d: 9, m: 11, out: false, tasks: 4, today: false }, { d: 10, m: 11, out: false, tasks: 3, today: false }, { d: 11, m: 11, out: false, tasks: 2, today: false }, { d: 12, m: 11, out: false, tasks: 2, today: false }, { d: 13, m: 11, out: false, tasks: 3, today: false }, { d: 14, m: 11, out: false, tasks: 1, today: false }, { d: 15, m: 11, out: false, tasks: 0, today: false } ] },
    { key: 'w4', days: [ { d: 16, m: 11, out: false, tasks: 3, today: false }, { d: 17, m: 11, out: false, tasks: 2, today: false }, { d: 18, m: 11, out: false, tasks: 2, today: false }, { d: 19, m: 11, out: false, tasks: 3, today: false }, { d: 20, m: 11, out: false, tasks: 1, today: false }, { d: 21, m: 11, out: false, tasks: 4, today: false }, { d: 22, m: 11, out: false, tasks: 0, today: false } ] },
    { key: 'w5', days: [ { d: 23, m: 11, out: false, tasks: 2, today: false }, { d: 24, m: 11, out: false, tasks: 2, today: false }, { d: 25, m: 11, out: false, tasks: 3, today: false }, { d: 26, m: 11, out: false, tasks: 1, today: false }, { d: 27, m: 11, out: false, tasks: 4, today: true }, { d: 28, m: 11, out: false, tasks: 3, today: false }, { d: 29, m: 11, out: false, tasks: 0, today: false } ] },
    { key: 'w6', days: [ { d: 30, m: 11, out: false, tasks: 2, today: false }, { d: 1, m: 12, out: true, tasks: 0, today: false }, { d: 2, m: 12, out: true, tasks: 0, today: false }, { d: 3, m: 12, out: true, tasks: 0, today: false }, { d: 4, m: 12, out: true, tasks: 0, today: false }, { d: 5, m: 12, out: true, tasks: 0, today: false }, { d: 6, m: 12, out: true, tasks: 0, today: false } ] }
  ],
};

export const planWeek = {
  label: '11/23 - 11/29',
  days: [
    { key: 'mon', label: '周一', date: '11/23', today: false, blocks: [
      { id: 'wb1', time: '08:00', title: '高数 · 中值定理', subject: '数学一', tone: 'brand', done: true },
      { id: 'wb2', time: '14:00', title: '数据结构 · 树', subject: '408', tone: 'ok', done: true },
      { id: 'wb3', time: '20:00', title: '卡片 40 张', subject: '复习', tone: 'neutral', done: true },
    ] },
    { key: 'tue', label: '周二', date: '11/24', today: false, blocks: [
      { id: 'wb4', time: '08:30', title: '阅读 2018 Text1', subject: '英语一', tone: 'warn', done: true },
      { id: 'wb5', time: '14:00', title: '二叉树遍历', subject: '408', tone: 'ok', done: true },
      { id: 'wb6', time: '19:30', title: '马原 单选 50', subject: '政治', tone: 'neutral', done: true },
    ] },
    { key: 'wed', label: '周三', date: '11/25', today: false, blocks: [
      { id: 'wb7', time: '08:00', title: '高数 · 导数应用', subject: '数学一', tone: 'brand', done: true },
      { id: 'wb8', time: '14:00', title: '操作系统 · 页表', subject: '408', tone: 'ok', done: true },
      { id: 'wb9', time: '20:00', title: '错题 8 题', subject: '错题', tone: 'neutral', done: false },
    ] },
    { key: 'thu', label: '周四', date: '11/26', today: false, blocks: [
      { id: 'wb10', time: '08:00', title: '计算机组成 · 存储器', subject: '408', tone: 'ok', done: true },
      { id: 'wb11', time: '15:00', title: '计算机网络 · 传输层', subject: '408', tone: 'ok', done: true },
      { id: 'wb12', time: '19:00', title: '阅读 2018 Text2', subject: '英语一', tone: 'warn', done: true },
    ] },
    { key: 'fri', label: '周五', date: '11/27', today: true, blocks: [
      { id: 'wb13', time: '08:00', title: '操作系统 · 内存管理', subject: '408', tone: 'ok', done: false },
      { id: 'wb14', time: '09:40', title: '高数 · 极限与导数', subject: '数学一', tone: 'brand', done: false },
      { id: 'wb15', time: '14:00', title: '树与二叉树', subject: '408', tone: 'ok', done: false },
      { id: 'wb16', time: '20:40', title: '马原 单选 50', subject: '政治', tone: 'neutral', done: false },
    ] },
    { key: 'sat', label: '周六', date: '11/28', today: false, blocks: [
      { id: 'wb17', time: '09:00', title: '数学一 真题 2019', subject: '数学一', tone: 'brand', done: false },
      { id: 'wb18', time: '14:00', title: '408 综合真题', subject: '408', tone: 'ok', done: false },
    ] },
    { key: 'sun', label: '周日', date: '11/29', today: false, blocks: [
      { id: 'wb19', time: '10:00', title: '本周错题回顾', subject: '错题', tone: 'neutral', done: false },
      { id: 'wb20', time: '20:00', title: '周复盘 + 下周计划', subject: '复盘', tone: 'brand', done: false },
    ] },
  ],
};

export const planDay = {
  label: '11 月 27 日 · 周五',
  summary: '今日 6 个任务 · 已用 3 小时 20 分 · 专注度 A',
  blocks: [
    { id: 'db1', start: '08:00', end: '09:30', title: '操作系统 · 内存管理 精读', subject: '408', book: 'Silberschatz《操作系统概念》', tone: 'ok', done: true },
    { id: 'db2', start: '09:40', end: '11:10', title: '高数 · 极限与导数 例题', subject: '数学一', book: '《数学一 考研数学复习全书》', tone: 'brand', done: true },
    { id: 'db3', start: '11:20', end: '12:00', title: '复习卡片 40 张', subject: '复习', book: 'Anki · 内存管理 / 树', tone: 'neutral', done: true },
    { id: 'db4', start: '14:00', end: '15:30', title: '数据结构 · 树与二叉树', subject: '408', book: '严蔚敏《数据结构（C语言版）》', tone: 'ok', done: false },
    { id: 'db5', start: '15:40', end: '16:40', title: '阅读 2018 Text3 精读', subject: '英语一', book: '《英语一 历年真题》', tone: 'warn', done: false },
    { id: 'db6', start: '16:50', end: '17:30', title: '错题回看 6 题', subject: '错题', book: '操作系统 分页 / 段页式', tone: 'neutral', done: false },
    { id: 'db7', start: '19:00', end: '20:30', title: '计算机网络 · 传输层', subject: '408', book: '谢希仁《计算机网络》', tone: 'ok', done: false },
    { id: 'db8', start: '20:40', end: '21:30', title: '政治 · 马原单选 50 题', subject: '政治', book: '肖秀荣《1000 题》', tone: 'neutral', done: false },
  ],
};

/* ===== 成长 Growth ===== */

export const growthLevel = {
  level: 12,
  name: '稳进者',
  next: '冲刺者',
  exp: 2480,
  nextExp: 3200,
  rank: '专业前 18%',
  days: 96,
  streak: 12,
  todayExp: 120,
};

export const growthDims = [
  { id: 'gd1', label: '记忆', value: 78, hint: '卡片 1,240 张 · 记住率 82%', tone: 'brand' },
  { id: 'gd2', label: '理解', value: 72, hint: '章节掌握 18 / 26 章', tone: 'brand' },
  { id: 'gd3', label: '输出', value: 65, hint: '笔记 46 篇 · 卡片 320 张', tone: 'ok' },
  { id: 'gd4', label: '速度', value: 70, hint: '真题均速 2 小时 48 分', tone: 'warn' },
  { id: 'gd5', label: '稳定', value: 61, hint: '连续打卡 12 天 · 断签 2 次', tone: 'warn' },
];

export const growthStats = {
  badgesDone: 9,
  badgesTotal: 14,
  hours: 21.5,
  totalHours: 386,
};

export const growthMilestones = [
  { id: 'gm1', name: '连续 7 天', desc: '连续打卡 7 天', glyph: '连', state: 'done', note: '11/05' },
  { id: 'gm2', name: '首次真题', desc: '完成数学一真题 1 套', glyph: '真', state: 'done', note: '10/12' },
  { id: 'gm3', name: '卡片 1000 张', desc: '复习卡片累计 1000 张', glyph: '卡', state: 'done', note: '11/18' },
  { id: 'gm4', name: '百小时', desc: '累计学习 100 小时', glyph: '时', state: 'done', note: '11/21' },
  { id: 'gm5', name: '错题清零', desc: '错题本当日清零', glyph: '错', state: 'done', note: '10/28' },
  { id: 'gm6', name: '周目标达成', desc: '周目标 100% 完成', glyph: '周', state: 'done', note: '11/24' },
  { id: 'gm7', name: '四小时专注', desc: '单日专注满 4 小时', glyph: '专', state: 'done', note: '11/16' },
  { id: 'gm8', name: '早起 7 天', desc: '7 天 07:30 前开始', glyph: '早', state: 'done', note: '10/22' },
  { id: 'gm9', name: '资料 20 份', desc: '上传资料满 20 份', glyph: '资', state: 'done', note: '11/09' },
  { id: 'gm10', name: '章节全 A', desc: '408 四科章节全 A', glyph: '章', state: 'doing', note: '差 1 章' },
  { id: 'gm11', name: '全勤 30 天', desc: '连续打卡 30 天', glyph: '勤', state: 'doing', note: '18 / 30' },
  { id: 'gm12', name: '模考 380', desc: '模考总分达到 380', glyph: '分', state: 'locked', note: '目标 380' },
  { id: 'gm13', name: '记忆大师', desc: '记忆维度 ≥ 85', glyph: '记', state: 'locked', note: '当前 78' },
  { id: 'gm14', name: '零欠账', desc: '复习队列零欠账 7 天', glyph: '零', state: 'locked', note: '未开启' },
];

export const growthTimeline = [
  { id: 'gt1', date: '11-27', text: '完成「操作系统 · 内存管理」单元测验 · A 级', delta: '+120' },
  { id: 'gt2', date: '11-26', text: '连续打卡达 12 天 · 触发稳定加成', delta: '+60' },
  { id: 'gt3', date: '11-24', text: '周目标达成 100%，解锁徽章「周目标达成」', delta: '+150' },
  { id: 'gt4', date: '11-21', text: '累计学习时长突破 100 小时', delta: '+200' },
  { id: 'gt5', date: '11-18', text: '复习卡片累计 1000 张 · 记忆 78', delta: '+90' },
];

/* ========================= 任务 Tasks ========================= */
export const taskStats = [
  { id: 'running', label: '进行中', value: 2, unit: '个', tone: 'brand', hint: '解析 1 · 生成卡片 1' },
  { id: 'queued', label: '排队中', value: 3, unit: '个', tone: 'ink', hint: '最长等待 2 分 18 秒' },
  { id: 'done', label: '今日完成', value: 18, unit: '个', tone: 'ok', hint: '含自动重试成功 2 个' },
  { id: 'failed', label: '今日失败', value: 2, unit: '个', tone: 'bad', hint: '其中 1 个可重试' },
  { id: 'avg', label: '平均耗时', value: '1.4', unit: '分钟', tone: 'ink', hint: '近 24 小时统计' },
];

export const taskRows = [
  {
    id: 'tk-1',
    type: '资料解析',
    target: '《操作系统概念》第 7 章 · PDF',
    subject: 'OS',
    status: 'running',
    progress: 64,
    elapsed: '1 分 12 秒',
    error: '',
    note: '正在抽取文本与公式',
  },
  {
    id: 'tk-2',
    type: '生成卡片',
    target: '计算机网络 · 谢希仁 第 4 章',
    subject: 'CN',
    status: 'running',
    progress: 38,
    elapsed: '48 秒',
    error: '',
    note: '已生成 26 / 68 张',
  },
  {
    id: 'tk-3',
    type: '资料解析',
    target: '《计算机组成原理》唐朔飞 · 扫描版',
    subject: 'CO',
    status: 'queued',
    progress: 0,
    elapsed: '等待 2 分 18 秒',
    error: '',
    note: '队列第 1 位',
  },
  {
    id: 'tk-4',
    type: '模拟卷',
    target: '数学一 · 2020 年真题出卷',
    subject: '数学',
    status: 'queued',
    progress: 0,
    elapsed: '等待 1 分 40 秒',
    error: '',
    note: '队列第 2 位',
  },
  {
    id: 'tk-5',
    type: '视频解析',
    target: '408 真题精讲 · 第 12 讲',
    subject: 'DS',
    status: 'queued',
    progress: 0,
    elapsed: '等待 36 秒',
    error: '',
    note: '队列第 3 位',
  },
  {
    id: 'tk-6',
    type: '资料解析',
    target: '《数据结构（C 语言版）》严蔚敏',
    subject: 'DS',
    status: 'success',
    progress: 100,
    elapsed: '2 分 05 秒',
    error: '',
    note: '312 页 · 生成笔记 18 条',
  },
  {
    id: 'tk-7',
    type: '生成卡片',
    target: '肖秀荣 1000 题 · 马原部分',
    subject: '政治',
    status: 'success',
    progress: 100,
    elapsed: '1 分 18 秒',
    error: '',
    note: '生成卡片 96 张',
  },
  {
    id: 'tk-8',
    type: '资料解析',
    target: '英语一 历年真题 2015-2024',
    subject: '英语',
    status: 'failed',
    progress: 42,
    elapsed: '56 秒',
    error: '文件已加密 · 无法抽取文本',
    note: '需先解除 PDF 密码后重试',
  },
  {
    id: 'tk-9',
    type: '视频解析',
    target: 'B 站 · 操作系统 PV 操作讲解',
    subject: 'OS',
    status: 'failed',
    progress: 12,
    elapsed: '31 秒',
    error: '上游超时 · retry 2/3 · id 7f2a…9c',
    note: '自动重试已用尽，可手动重试',
  },
];

export const taskSummary = {
  queue: 3,
  concurrency: '2 / 4',
  todayDone: 18,
  failed: 2,
  successRate: 90,
  avgTime: '1.4 分钟',
  retentionDays: 7,
  lastCleanup: '2026-11-20 09:12',
  oldFailed: 128,
  oldCanceled: 36,
  logCache: '1.8 GB',
};

export const taskCleanup = [
  { id: 'cf-1', label: '历史失败记录', count: '128 条', hint: '超过 7 天未重试，清理后不可恢复', tone: 'bad' },
  { id: 'cf-2', label: '已放弃任务', count: '36 条', hint: '手动放弃且已过保留期', tone: 'warn' },
  { id: 'cf-3', label: '解析日志缓存', count: '1.8 GB', hint: '仅缓存，不影响资料与卡片', tone: 'neutral' },
];

/* ========================= 问答 QA ========================= */
export const qaStrategies = [
  { id: 'smart', label: '智能', desc: '自动判断是否需要资料与联网', hint: '推荐', isDefault: true },
  { id: 'docs', label: '仅资料', desc: '只在已上传资料与笔记内检索', hint: '可溯源' },
  { id: 'web', label: '仅联网', desc: '抓取公开网页，不使用本地资料', hint: '时效强' },
  { id: 'model', label: '仅模型', desc: '不检索，直接由模型作答', hint: '最快' },
  { id: 'mix', label: '混合', desc: '资料 + 联网 + 模型推理组合', hint: '最全面' },
];

export const qaSessions = [
  { id: 'qs-1', title: '死锁的四个必要条件与检测避免的区别', strategy: '智能', turns: 6, time: '今天 14:22', active: true },
  { id: 'qs-2', title: '银行家算法手算步骤', strategy: '仅资料', turns: 4, time: '今天 10:05' },
  { id: 'qs-3', title: 'TCP 拥塞控制四个阶段对比', strategy: '混合', turns: 8, time: '昨天 21:40' },
  { id: 'qs-4', title: '浮点数规格化与舍入误差', strategy: '仅模型', turns: 3, time: '昨天 16:18' },
  { id: 'qs-5', title: '英语一 完形填空提速方法', strategy: '仅联网', turns: 5, time: '11-25 19:02' },
  { id: 'qs-6', title: '矩阵相似对角化判定条件', strategy: '智能', turns: 7, time: '11-24 20:31' },
  { id: 'qs-7', title: '唯物史观两大基本规律背诵口诀', strategy: '仅资料', turns: 4, time: '11-23 08:56' },
  { id: 'qs-8', title: 'B 树与 B+ 树在磁盘索引中的取舍', strategy: '混合', turns: 5, time: '11-22 15:47' },
];

export const qaQuestion = '死锁的四个必要条件是什么？检测和避免有什么区别？';

export const qaAnswer = {
  strategyId: 'smart',
  strategyLabel: '智能',
  totalMs: 4380,
  total: '4.4 秒',
  stages: [
    { id: 'st-1', label: '检索资料', detail: '命中 6 段 · 操作系统概念 p.268 / 笔记 2 条', ms: 1240 },
    { id: 'st-2', label: '联网补充', detail: '抓取 2 个页面 · 信源可信度 0.82', ms: 980 },
    { id: 'st-3', label: '组织回答', detail: '按 408 考点重排 · 生成 4 段', ms: 2160 },
  ],
  blocks: [
    '死锁的四个必要条件是：互斥、占有并等待、不可抢占、循环等待。四者同时成立才可能死锁，破坏任意一个就足以预防。',
    '「避免」与「检测」的分界：避免（如银行家算法）在真正分配前判断系统是否仍处于安全状态，本质是静态准入；检测（如资源分配图化简）允许系统进入不安全态，靠定期扫描发现环路再回滚。',
    '- 互斥 → 打印机类设备改用假脱机共享\n- 占有并等待 → 一次性申请全部资源\n- 不可抢占 → 允许剥夺并回滚已占用资源\n- 循环等待 → 按资源序号升序申请',
    '408 常考对比：预防的代价是资源利用率低；避免需要事先声明最大需求，银行家算法复杂度 O(n²m)；检测需保留资源分配图，恢复手段为终止进程或资源剥夺。',
  ],
  sources: [
    { id: 'sc-1', kind: 'doc', title: '操作系统概念 · 第 7 章 死锁', meta: 'PDF · p.268' },
    { id: 'sc-2', kind: 'doc', title: '笔记：死锁四条件与处理策略', meta: '笔记 · 11-19' },
    { id: 'sc-3', kind: 'doc', title: '408 题库 · OS 死锁 12 题', meta: '题库 · 正确率 67%' },
    { id: 'sc-4', kind: 'web', title: 'OSTEP · Deadlock', meta: 'remzi.com' },
  ],
  followups: ['银行家算法手算步骤怎么走？', '死锁与饥饿的区别？', '408 出现过哪些死锁真题？', '用资源分配图举例说明'],
};

export const qaHints = [
  { id: 'qh-1', text: '回答会标注来源，点击芯片可跳到原文段落' },
  { id: 'qh-2', text: '追问建议基于本轮上下文生成，可直接点选' },
  { id: 'qh-3', text: '仅资料模式不会联网，适合考前溯源复习' },
];

/** 空会话态的推荐问题 */
export const recommendedQuestions = [
  { id: 'rq-1', topic: '408 真题', text: '死锁的四个必要条件是什么？检测和避免有什么区别？' },
  { id: 'rq-2', topic: '数学', text: '等价无穷小替换在加减项中为什么不能直接用？' },
  { id: 'rq-3', topic: '408 真题', text: 'TCP 三次握手为什么不是两次？' },
  { id: 'rq-4', topic: '英语', text: '定语从句嵌套时如何快速剥离主干？' },
  { id: 'rq-5', topic: '复习方法', text: '还有 22 天，408 四科怎么安排冲刺节奏？' },
  { id: 'rq-6', topic: '数学', text: '相似对角化的充要条件是什么？' },
];

/* ===== 视频（Video）===== */

/** 左侧视频列表 */
export const videoList = [
  { id: 'v1', title: '数据结构 第7章 图 · 最短路径', chapter: '第 7 章 · 图', duration: '1:48:20', status: '已完成', progress: 100, current: true },
  { id: 'v2', title: '计算机组成原理 第3章 存储系统', chapter: '第 3 章 · 存储', duration: '2:06:14', status: '解析中', progress: 62, current: false },
  { id: 'v3', title: '操作系统 第5章 死锁', chapter: '第 5 章 · 并发', duration: '1:12:40', status: '已完成', progress: 100, current: false },
  { id: 'v4', title: '计算机网络 第4章 传输层', chapter: '第 4 章 · 传输层', duration: '1:56:02', status: '待解析', progress: 0, current: false },
  { id: 'v5', title: '数据结构 第8章 排序', chapter: '第 8 章 · 排序', duration: '1:33:15', status: '已完成', progress: 100, current: false },
  { id: 'v6', title: '操作系统 第6章 内存管理', chapter: '第 6 章 · 内存', duration: '1:41:58', status: '解析失败', progress: 38, current: false },
  { id: 'v7', title: '计算机网络 第5章 应用层', chapter: '第 5 章 · 应用层', duration: '1:22:31', status: '已完成', progress: 100, current: false },
];

/** 当前播放视频元信息 */
export const videoMeta = {
  id: 'v1',
  title: '数据结构 第7章 图 · 最短路径（Dijkstra / Floyd）',
  chapter: '第 7 章 · 图',
  source: '本地文件 · ds_ch7_graph.mp4',
  resolution: '1080p',
  size: '1.24 GB',
  duration: '01:48:20',
  watched: '00:24:06',
  progress: 22,
  speed: '1.0x',
  subtitle: '中文自动',
  figures: 5,
};

/** 右侧 Tab 定义 */
export const videoTabs = [
  { id: 'summary', label: '摘要' },
  { id: 'outline', label: '大纲' },
  { id: 'qa', label: '问答' },
  { id: 'figures', label: '图文' },
  { id: 'source', label: '视频源' },
  { id: 'transcript', label: '转写' },
  { id: 'notes', label: '笔记' },
  { id: 'pics', label: '配图' },
];

/** 摘要 Tab */
export const videoSummary = {
  text: '本节围绕单源最短路径展开：先把带权图抽象为邻接表，再分别用 Dijkstra 的贪心松弛与 Floyd 的区间 DP 求出最短距离，最后讨论负权边为何使 Dijkstra 失效。',
  points: [
    'Dijkstra 适用边权非负，复杂度 O(E log V)，可用堆优化。',
    'Floyd 三重循环 O(V³)，可处理负权但不能有负环。',
    '松弛条件 dist[v] > dist[u] + w(u,v) 是两类算法的公共核心。',
  ],
  keywords: ['松弛操作', '优先队列', '三层循环', '负权边', '稀疏图'],
};

/** 大纲 Tab */
export const videoOutline = [
  { id: 'o1', t: '00:00', title: '本节目标与前置知识', level: 1, dur: '4 min' },
  { id: 'o2', t: '04:12', title: '带权图与邻接表的存储', level: 1, dur: '9 min' },
  { id: 'o3', t: '13:36', title: 'Dijkstra 算法思想与图解', level: 2, dur: '18 min' },
  { id: 'o4', t: '31:48', title: '堆优化实现与复杂度分析', level: 2, dur: '14 min' },
  { id: 'o5', t: '45:52', title: 'Floyd 的三层循环与状态定义', level: 2, dur: '21 min' },
  { id: 'o6', t: '01:07:10', title: '负权边与负环的判定', level: 2, dur: '12 min' },
  { id: 'o7', t: '01:19:40', title: '真题：2021-408 第42题讲解', level: 1, dur: '16 min' },
  { id: 'o8', t: '01:36:05', title: '本节小结与作业', level: 1, dur: '6 min' },
];

/** 问答 Tab */
export const videoQA = [
  { id: 'q1', q: '为什么 Dijkstra 不能处理负权边？', a: '算法依赖「已确定集合中最短的点不会再有更短路径」这一贪心前提，负权边会破坏该单调性，使已确定的距离可能被再次更新。' },
  { id: 'q2', q: 'Floyd 的三层循环能交换顺序吗？', a: '不能。k 必须是最外层，代表「允许经过的前 k 个中转点」这一阶段，交换后状态含义被破坏，结果会错。' },
  { id: 'q3', q: '稀疏图该选哪个？', a: '选 Dijkstra + 堆，复杂度 O(E log V)；稠密图或需要全源最短路时用 Floyd，常数小且实现简单。' },
];

/** 配图（时间轴标记与图文/配图 Tab 共用） */
export const videoFigures = [
  { id: 'f1', t: '04:12', title: '邻接表结构示意', note: '图 7-1 · 带权图转邻接表' },
  { id: 'f2', t: '13:36', title: 'Dijkstra 松弛过程', note: '图 7-2 · 逐点确定最短距离' },
  { id: 'f3', t: '31:48', title: '优先队列堆结构', note: '图 7-3 · 堆优化取出最小点' },
  { id: 'f4', t: '45:52', title: 'Floyd 状态转移矩阵', note: '图 7-4 · 三层循环填表' },
  { id: 'f5', t: '01:07:10', title: '负环判定示意', note: '图 7-5 · 第 n 次仍可松弛' },
];

/** 时间轴刻度（12 格） */
export const videoTimeline = [
  '00:00', '09:02', '18:04', '27:16', '36:18', '45:20',
  '54:22', '01:03:24', '01:12:26', '01:21:28', '01:30:30', '01:48:20',
];

/** 视频源 Tab */
export const videoSources = [
  { id: 's1', label: '来源文件', value: 'ds_ch7_graph.mp4 · 1.24 GB' },
  { id: 's2', label: '解析模型', value: '本地转写 · 中文自动字幕' },
  { id: 's3', label: '入库时间', value: '2026-11-24 21:08' },
  { id: 's4', label: '关联资料', value: '《数据结构》第7章.pdf' },
];

/** 转写 Tab */
export const videoTranscript = [
  { id: 'r1', t: '00:00', text: '这一节我们讲图的最短路径，先回顾一下带权图怎么存。' },
  { id: 'r2', t: '04:12', text: '邻接表的好处是稀疏图上只存实际存在的边。' },
  { id: 'r3', t: '13:36', text: 'Dijkstra 的核心就是每次取当前距离最小的点，然后松弛它的出边。' },
  { id: 'r4', t: '31:48', text: '把找最小点换成堆，复杂度就从 O(V²) 降到 O(E log V)。' },
  { id: 'r5', t: '45:52', text: 'Floyd 用的是区间 DP，k 在外层表示允许经过前 k 个中转点。' },
  { id: 'r6', t: '01:07:10', text: '如果有负环，第 n 次循环还能继续松弛，这就是判定依据。' },
];

/** 笔记 Tab */
export const videoNotes = [
  { id: 'n1', t: '13:36', title: 'Dijkstra 的贪心前提', text: '已确定集合内的点距离不会再变小，因此负权边会破坏该前提。' },
  { id: 'n2', t: '31:48', title: '堆优化写法', text: '用 (dist, u) 入堆，出堆时判重；否则复杂度退化。' },
  { id: 'n3', t: '45:52', title: 'k 必须在最外层', text: '否则状态「允许经过前 k 个点」的含义被破坏。' },
  { id: 'n4', t: '01:07:10', title: '负环判定', text: '做 n 轮松弛，第 n 轮仍可松弛即存在负环。' },
];


/* ===================== 设置 Settings ===================== */

/** 设置页左侧分组导航（顺序固定） */
export const settingsGroups = [
  { id: 'account', label: '账号与工作区', desc: '身份信息、工作区配额与危险操作' },
  { id: 'providers', label: '模型供应商', desc: '接口地址、密钥与调用权重' },
  { id: 'models', label: '模型', desc: '可用模型、用途与默认路由' },
  { id: 'transcriber', label: '转录器', desc: '视频转写引擎与运行参数' },
  { id: 'cookie', label: '采集 Cookie', desc: 'B 站课程字幕与播放列表采集' },
  { id: 'notify', label: '通知', desc: '提醒渠道与触发条件' },
  { id: 'appearance', label: '外观', desc: '主题、密度与字号' },
  { id: 'backup', label: '数据备份', desc: '创建、校验、恢复与演练' },
  { id: 'diag', label: '诊断监控', desc: '延迟、队列与版本一致性' },
  { id: 'about', label: '关于', desc: '版本、更新日志与技术栈' },
];

/** 账号与工作区 */
export const settingsAccount = {
  user: {
    name: '苏胜',
    initial: 'S',
    email: 'su.sheng@gflc.app',
    school: '浙江水利水电学院',
    major: '软件工程',
    role: '工作区所有者',
  },
  workspace: {
    name: 'GFLC 个人工作区',
    plan: '内测版',
    seats: '1 / 1',
    createdAt: '2026-09-02',
    storage: '已用 1.8 GB / 20 GB',
    usedPercent: 9,
  },
  security: {
    lastLogin: '2026-11-27 08:12 · Windows · Chrome 131',
    devices: '2 台设备在线',
    twoFactor: '未开启两步验证',
  },
  danger: [
    { id: 'logout', title: '退出登录', desc: '清空本地会话并回到登录页，资料、笔记与卡片不受影响。', action: '退出登录' },
    { id: 'delete', title: '注销账号', desc: '删除账号与全部云端数据，30 天保留期后不可恢复。', action: '注销账号' },
  ],
};

/** 学习档案 */
export const accountProfile = [
  { key: 'grade', label: '年级', value: '专升本 23 级' },
  { key: 'major', label: '专业', value: '软件工程' },
  { key: 'target', label: '目标院校', value: '杭州电子科技大学' },
  { key: 'duration', label: '备考时长', value: '128 天' },
];

/** 数据统计 */
export const accountStats = [
  { key: 'days', label: '累计天数', value: 128, unit: '天' },
  { key: 'docs', label: '资料数', value: 18, unit: '份' },
  { key: 'cards', label: '卡片数', value: 1240, unit: '张' },
  { key: 'questions', label: '题目数', value: 862, unit: '道' },
];

/** 登录设备 */
export const accountDevices = [
  { id: 'dev-1', name: 'Windows 本机', detail: 'Chrome 131 · 浙江杭州', time: '当前设备 · 08:12', current: true },
  { id: 'dev-2', name: 'iPhone 15 Pro', detail: 'GFLC App 2.4 · 浙江杭州', time: '昨天 21:40', current: false },
  { id: 'dev-3', name: 'MacBook Air', detail: 'Safari 17 · 图书馆网络', time: '11-24 16:02', current: false },
];

/** 模型供应商（支持增删改） */
export const settingsProviders = [
  {
    id: 'p1',
    name: '阿里云百炼',
    kind: 'OpenAI 兼容',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    key: 'sk-bailian-••••3f7a',
    models: 4,
    status: 'ok',
    latency: '612 ms',
    weight: 60,
  },
  {
    id: 'p2',
    name: 'DeepSeek 官方',
    kind: 'OpenAI 兼容',
    baseUrl: 'https://api.deepseek.com/v1',
    key: 'sk-deepseek-••••9c21',
    models: 2,
    status: 'ok',
    latency: '884 ms',
    weight: 30,
  },
  {
    id: 'p3',
    name: '火山方舟',
    kind: 'OpenAI 兼容',
    baseUrl: 'https://ark.cn-beijing.volces.com/api/v3',
    key: 'ak-ark-••••55d0',
    models: 3,
    status: 'warn',
    latency: '1.9 s',
    weight: 10,
  },
  {
    id: 'p4',
    name: '本地 Ollama',
    kind: '本地部署',
    baseUrl: 'http://127.0.0.1:11434/v1',
    key: '无需密钥',
    models: 2,
    status: 'ok',
    latency: '86 ms',
    weight: 0,
  },
];

/** 模型列表（带用途标签） */
export const settingsModels = [
  { id: 'm1', name: 'qwen3-max', vendor: '阿里云百炼', purposes: ['对话', '长文'], context: '128K', price: '¥0.0024 / 千 token', enabled: true, isDefault: true },
  { id: 'm2', name: 'deepseek-v3.2', vendor: 'DeepSeek 官方', purposes: ['对话', '推理'], context: '64K', price: '¥0.0010 / 千 token', enabled: true, isDefault: false },
  { id: 'm3', name: 'doubao-1.5-pro', vendor: '火山方舟', purposes: ['对话', '视觉'], context: '32K', price: '¥0.0008 / 千 token', enabled: true, isDefault: false },
  { id: 'm4', name: 'qwen2.5-vl-72b', vendor: '阿里云百炼', purposes: ['视觉', 'OCR'], context: '32K', price: '¥0.0030 / 千 token', enabled: true, isDefault: false },
  { id: 'm5', name: 'text-embedding-v3', vendor: '阿里云百炼', purposes: ['嵌入'], context: '8K', price: '¥0.0005 / 千 token', enabled: true, isDefault: false },
  { id: 'm6', name: 'bge-reranker-v2', vendor: '本地 Ollama', purposes: ['重排'], context: '8K', price: '本地算力', enabled: true, isDefault: false },
  { id: 'm7', name: 'glm-4.6', vendor: '本地 Ollama', purposes: ['对话', '工具调用'], context: '128K', price: '本地算力', enabled: false, isDefault: false },
];

/** 转录器三档单选 */
export const settingsTranscriber = {
  current: 'whisper-large-v3',
  options: [
    { id: 'whisper-turbo', name: 'Whisper Turbo', vendor: 'OpenAI', speed: '6× 实时', accuracy: '96.1%', note: '长视频首选，显存占用最低', tag: '推荐' },
    { id: 'whisper-large-v3', name: 'Whisper Large v3', vendor: 'OpenAI', speed: '1.8× 实时', accuracy: '97.8%', note: '专业术语识别更准，GPU 占用较高', tag: '当前' },
    { id: 'paraformer-v2', name: 'Paraformer v2', vendor: '阿里云', speed: '4× 实时', accuracy: '97.2%', note: '中文口语与标点优化，适合网课', tag: '' },
  ],
  runtime: {
    device: 'CPU 8 线程 · 无 GPU',
    queue: '队列 1 个任务',
    sample: '第 4 讲 46 分钟视频耗时 12 分 20 秒',
  },
};

/** 采集 Cookie（B 站） */
export const settingsCookie = {
  platform: '哔哩哔哩（B 站）',
  status: '已绑定',
  updatedAt: '2026-11-20 21:34',
  masked: 'SESSDATA=8f2a…c91b；bili_jct=41d0…9e77；buvid3=F1C2…7A3D',
  scope: '课程字幕 / 播放列表 / 分 P 标题',
  lastSync: '2026-11-26 23:10 · 同步 12 个课程合集',
  tips: [
    '仅用于抓取已购买课程的字幕与播放列表，Cookie 只存于本机浏览器。',
    'Cookie 约 30 天过期，失效后视频采集任务会提示重新绑定。',
    '请勿填写账号密码，保存后界面只回显掩码，不展示完整明文。',
  ],
};

/** 通知开关 */
export const settingsNotify = [
  { id: 'n1', label: '每日复习提醒', desc: '到期卡片 ≥ 20 张时，08:30 推送一次', channel: '桌面通知', on: true },
  { id: 'n2', label: '任务完成提醒', desc: '视频转写、资料解析结束后即时提示', channel: '桌面通知', on: true },
  { id: 'n3', label: '任务失败告警', desc: '解析失败或队列积压超过 3 个时告警', channel: '应用内', on: true },
  { id: 'n4', label: '周报邮件', desc: '每周日 21:00 汇总学习时长与掌握率', channel: '邮件', on: false },
  { id: 'n5', label: '计划打卡提醒', desc: '当日计划未完成 50% 时，20:00 提醒', channel: '应用内', on: true },
  { id: 'n6', label: '模型用量阈值', desc: '当日 token 用量达到额度 80% 时提示', channel: '应用内', on: false },
];

/** 外观 */
export const settingsAppearance = {
  theme: { current: 'light', options: [{ id: 'light', label: '浅色' }, { id: 'dark', label: '深色' }, { id: 'auto', label: '跟随系统' }] },
  density: { current: 'compact', options: [{ id: 'compact', label: '紧凑' }, { id: 'standard', label: '标准' }] },
  sidebar: { current: 'expanded', options: [{ id: 'expanded', label: '默认展开' }, { id: 'collapsed', label: '默认收起' }] },
  motion: { current: 'on', options: [{ id: 'on', label: '开启' }, { id: 'off', label: '关闭' }] },
  fontScale: { current: '13', options: [{ id: '12', label: '12' }, { id: '13', label: '13' }, { id: '14', label: '14' }] },
};

/** 数据备份（四个操作） */
export const settingsBackup = {
  summary: '上次备份 2026-11-26 23:40 · 全量 268 MB · 保留 5 份快照',
  actions: [
    { id: 'create', label: '创建备份', desc: '打包资料索引、笔记、卡片与配置', meta: '预计 268 MB · 约 40 秒', tone: 'solid' },
    { id: 'verify', label: '校验完整性', desc: '逐块比对 SHA-256 与索引条数', meta: '最近校验 2026-11-26 · 通过', tone: 'line' },
    { id: 'restore', label: '恢复快照', desc: '回滚到选定快照，覆盖当前数据库', meta: '可选快照 5 份 · 需二次确认', tone: 'line' },
    { id: 'drill', label: '演练恢复', desc: '在临时库演练，不触碰生产数据', meta: '最近演练 2026-11-19 · 成功', tone: 'line' },
  ],
  snapshots: [
    { id: 's1', time: '2026-11-26 23:40', size: '268 MB', kind: '自动 · 全量' },
    { id: 's2', time: '2026-11-24 22:05', size: '241 MB', kind: '手动 · 全量' },
    { id: 's3', time: '2026-11-20 21:12', size: '196 MB', kind: '自动 · 增量' },
  ],
};

/** 诊断监控 */
export const settingsDiag = [
  { id: 'd1', name: '数据库延迟', value: '18 ms', hint: '本机 PostgreSQL 16 · 近 1 分钟均值', tone: 'ok' },
  { id: 'd2', name: '任务队列', value: '3 个待处理', hint: '并发上限 2 · 最早任务等待 4 分钟', tone: 'warn' },
  { id: 'd3', name: '向量索引', value: '16 284 条切片', hint: '最近重建 2026-11-27 07:40', tone: 'ok' },
  { id: 'd4', name: '前后端版本', value: 'web 8.0.0 / api 8.0.0', hint: '版本一致，无需迁移', tone: 'ok' },
  { id: 'd5', name: '磁盘可用', value: '42.6 GB', hint: '备份目录占比 31%，建议保留 ≥ 20 GB', tone: 'ok' },
];

/** 关于 */
export const settingsAbout = {
  version: 'v8.0.0-proto',
  build: '2026-11-27 · 内置静态资源，无外链',
  channel: '内测渠道',
  stack: 'React 19 · Vite 7 · Tailwind 3.4.17 · daisyUI 4.12.24',
  changelog: [
    { id: 'c1', date: '2026-11-27', text: '原型 v8 完成 14 个页面布局替换，数据全部走 mock。' },
    { id: 'c2', date: '2026-11-24', text: '新增任务中心与问答过程可视化，支持撤销任务。' },
    { id: 'c3', date: '2026-11-19', text: '视频页补齐大纲、图文、转写与时间轴联动。' },
  ],
};

export default {
  profile,
  authDemo,
  authBrand,
  dashboardKpis,
  weeklyGoal,
  recentLearnings,
  deckDistribution,
  deckDistributionTotal,
  heatmap,
  heatmapSummary,
  studyEntries,
  quickUploads,
  systemInfo,
  aiUsage,
  notificationCount,
  paletteActions,
  docSubjects,
  docKinds,
  documents,
  docQueue,
  docStats,
  docStorage,
  docReader,
  documentDetail,
  noteFolders,
  noteList,
  noteOpen,
  notesRecent,
  noteStats,
  bankTree,
  questionBanks,
  bankStats,
  bankOverview,
  bankQueue,
  deckSubjects,
  deckChapters,
  deckProficiency,
  deckCards,
  deckStats,
  deckEditor,
  studyModes,
  quizSession,
  quizRelated,
  quizOptionStats,
  quizRelatedPoints,
  reciteGroups,
  reciteCards,
  examPaper,
  examHistory,
  wrongList,
  wrongStats,
  reviewQueue,
  reviewCard,
  reviewGrades,
  reviewSnooze,
  reviewStats,
  reviewToday,
  upcomingReviews,
  planHeader,
  planGoalBars,
  planTodayTasks,
  planTemplates,
  planStats,
  planMonth,
  planWeek,
  planDay,
  growthLevel,
  growthDims,
  growthStats,
  growthMilestones,
  growthTimeline,
  taskStats,
  taskRows,
  taskSummary,
  taskCleanup,
  qaStrategies,
  qaSessions,
  qaQuestion,
  qaAnswer,
  qaHints,
  recommendedQuestions,

  videoList,
  videoMeta,
  videoTabs,
  videoSummary,
  videoOutline,
  videoQA,
  videoFigures,
  videoTimeline,
  videoSources,
  videoTranscript,
  videoNotes,

  settingsGroups,
  settingsAccount,
  accountProfile,
  accountStats,
  accountDevices,
  settingsProviders,
  settingsModels,
  settingsTranscriber,
  settingsCookie,
  settingsNotify,
  settingsAppearance,
  settingsBackup,
  settingsDiag,
  settingsAbout,
};
