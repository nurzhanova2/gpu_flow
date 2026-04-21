const hourLabels = Array.from({ length: 24 }, (_, index) => `${String(index).padStart(2, "0")}:00`);

export const userSummaryStats = [
  { id: "active", label: "Активные сессии", value: "1", hint: "1 сессия запущена", tone: "green" },
  { id: "position", label: "Позиция в очереди", value: "3", hint: "ETA 11-14 мин", tone: "yellow" },
  { id: "week", label: "GPU-часы (7д)", value: "18.4", hint: "+2.1ч к прошлой неделе", tone: "blue" },
  { id: "success", label: "Успешный запуск", value: "96%", hint: "24 успешных старта", tone: "green" },
];

export const launchProfiles = [
  {
    id: "cpu-standard",
    label: "CPU Standard",
    description: "Без GPU. Мгновенный запуск.",
    queue: "Без очереди",
    tag: "Быстро",
    icon: "CPU",
    recommended: false,
  },
  {
    id: "gpu-basic",
    label: "GPU Basic",
    description: "1x NVIDIA T4, сбалансированная нагрузка.",
    queue: "~6 мин",
    tag: "Баланс",
    icon: "T4",
    recommended: false,
  },
  {
    id: "gpu-pro",
    label: "GPU Pro",
    description: "1x NVIDIA A100 с увеличенной памятью.",
    queue: "~12 мин",
    tag: "Рекомендуем",
    icon: "A100",
    recommended: true,
  },
  {
    id: "gpu-max",
    label: "GPU Max",
    description: "2x A100 для длительных задач обучения.",
    queue: "~25 мин",
    tag: "Максимум",
    icon: "2xA100",
    recommended: false,
  },
];

export const mySessionState = {
  status: "waiting",
  stateLabel: "Заявка в очереди, ожидается выделение GPU",
  queuePosition: 3,
  queueTotal: 9,
  etaRange: "11-14 мин",
  averageWaitToday: "9 мин",
  completedAhead: 2,
  progressPercent: 33,
  selectedProfile: "GPU Pro",
  requestedAt: "10:18",
};

export const queueSnapshot = [
  { id: "q1", user: "Вы", profile: "GPU Pro", status: "waiting", waitMin: 12, mine: true },
  { id: "q2", user: "Mina K.", profile: "GPU Pro", status: "starting", waitMin: 3 },
  { id: "q3", user: "Alex J.", profile: "GPU Basic", status: "running", waitMin: 0 },
  { id: "q4", user: "Nora P.", profile: "CPU Standard", status: "waiting", waitMin: 8 },
  { id: "q5", user: "Tim R.", profile: "GPU Pro", status: "waiting", waitMin: 15 },
  { id: "q6", user: "Eva S.", profile: "GPU Basic", status: "starting", waitMin: 2 },
  { id: "q7", user: "Leo B.", profile: "GPU Max", status: "waiting", waitMin: 21 },
  { id: "q8", user: "Nina D.", profile: "CPU Standard", status: "running", waitMin: 0 },
  { id: "q9", user: "Yuri T.", profile: "GPU Basic", status: "waiting", waitMin: 6 },
];

export const activeSessions = [
  {
    id: "s1",
    user: "Вы",
    node: "node-beta-02",
    gpu: "A100-40GB",
    profile: "GPU Pro",
    status: "running",
    durationMin: 47,
    gpuUsage: 83,
    memoryUsage: 69,
    cpuUsage: 42,
    mine: true,
  },
  {
    id: "s2",
    user: "Mina K.",
    node: "node-alpha-01",
    gpu: "A100-80GB",
    profile: "GPU Max",
    status: "running",
    durationMin: 102,
    gpuUsage: 91,
    memoryUsage: 82,
    cpuUsage: 67,
  },
  {
    id: "s3",
    user: "Alex J.",
    node: "node-gamma-03",
    gpu: "T4",
    profile: "GPU Basic",
    status: "idle",
    durationMin: 31,
    gpuUsage: 18,
    memoryUsage: 35,
    cpuUsage: 22,
  },
  {
    id: "s4",
    user: "Nina D.",
    node: "node-delta-04",
    gpu: "CPU only",
    profile: "CPU Standard",
    status: "starting",
    durationMin: 6,
    gpuUsage: 0,
    memoryUsage: 24,
    cpuUsage: 38,
  },
  {
    id: "s5",
    user: "Tim R.",
    node: "node-epsilon-05",
    gpu: "A100-40GB",
    profile: "GPU Pro",
    status: "running",
    durationMin: 63,
    gpuUsage: 76,
    memoryUsage: 58,
    cpuUsage: 44,
  },
];

export const recentSessionHistory = [
  { id: "h1", startedAt: "21 апр, 08:15", duration: "1ч 12м", profile: "GPU Pro", result: "completed" },
  { id: "h2", startedAt: "20 апр, 17:02", duration: "42м", profile: "GPU Basic", result: "completed" },
  { id: "h3", startedAt: "20 апр, 11:44", duration: "2ч 05м", profile: "GPU Pro", result: "completed" },
  { id: "h4", startedAt: "19 апр, 19:09", duration: "53м", profile: "CPU Standard", result: "completed" },
  { id: "h5", startedAt: "19 апр, 14:26", duration: "18м", profile: "GPU Max", result: "failed" },
  { id: "h6", startedAt: "18 апр, 09:11", duration: "1ч 37м", profile: "GPU Pro", result: "completed" },
];

export const gpuUtilizationSeries = hourLabels.map((time, index) => ({
  time,
  nodeAlpha: Math.max(8, Math.min(99, Math.round(52 + Math.sin(index * 0.35) * 28 + (index % 3) * 5))),
  nodeBeta: Math.max(5, Math.min(99, Math.round(45 + Math.cos(index * 0.28) * 25 + (index % 4) * 4))),
  nodeGamma: Math.max(0, Math.min(92, Math.round(22 + Math.sin(index * 0.52) * 18 + (index % 5) * 3))),
}));

export const queueTrendSeries = Array.from({ length: 18 }, (_, index) => ({
  time: `${String(6 + index).padStart(2, "0")}:00`,
  queued: Math.max(1, Math.round(4 + Math.sin(index * 0.45) * 3 + (index % 3))),
  avgWait: Math.max(2, Math.round(8 + Math.cos(index * 0.4) * 5 + (index % 4))),
}));

export const usageSplit = [
  { id: "busy", label: "GPU занято", value: 71, color: "var(--tone-green)" },
  { id: "idle", label: "GPU простаивает", value: 21, color: "var(--tone-yellow)" },
  { id: "maintenance", label: "Техобслуживание", value: 8, color: "var(--tone-blue)" },
];
