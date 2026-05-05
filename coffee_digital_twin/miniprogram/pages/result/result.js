const { request } = require('../../utils/request');
const { chartItems, asPercent } = require('../../utils/formatter');
const { getTaskId } = require('../../utils/storage');

// 静态模型说明（也可从 /api/model/info 动态加载）
const MODEL_INFO_LIST = [
  {
    name: 'APSIM-Coffee',
    layer: '作物生长层',
    icon: '🌱',
    predicts: ['生育期', '产量趋势', '水分胁迫', '氮素状态', 'LAI'],
    explains: 'APSIM-Coffee 模拟咖啡全生育期动态，预测产量趋势，量化水分胁迫和氮素状态对产量形成的影响。水分胁迫指数越高，说明作物感受到的水分压力越大。',
  },
  {
    name: 'HYDRUS-1D',
    layer: '土壤水分层',
    icon: '💧',
    predicts: ['剖面含水率', '入渗深度', '根系吸水效率'],
    explains: 'HYDRUS-1D 解释灌溉水能入渗多深、主根区是否真正缺水。能区分"表层湿润"和"根区供水充足"两种情况，避免误判。',
  },
  {
    name: 'BEPS-Lite',
    layer: '冠层生态层',
    icon: '🌳',
    predicts: ['GPP', 'NPP', 'ET', '碳汇', '长势评分'],
    explains: 'BEPS-Lite 评估冠层光合生产力。GPP/NPP 下降是水分或光照不足的早期预警。长势评分下降而水肥正常，提示可能存在遮阴或病虫害问题。',
  },
];

Page({
  data: {
    loading: true,
    taskId: '',
    result: {},
    mechanism: {},          // 三模型机理解释
    yieldItems: [],
    soilItems: [],
    gppItems: [],
    nppItems: [],
    etItems: [],
    rootUptake: '-',
    rootUptakePct: '-',     // 格式化的百分比用于机理卡片
    modelInfoList: MODEL_INFO_LIST,
    validationCases: [],    // 示范验证案例
  },

  onLoad(options) {
    this.setData({ taskId: options.task_id || getTaskId() });
  },

  onShow() {
    if (this.data.taskId) {
      this.loadResult();
    } else {
      this.setData({ loading: false });
    }
  },

  async loadResult() {
    // AI辅助生成-DeepSeek-V3 - 2026年5月2日 18:30:10 - 小程序结果页数据装载与图表格式化
    this.setData({ loading: true });
    try {
      const res = await request({ url: `/api/model/result/${this.data.taskId}` });
      const soil = (res.hydrus && res.hydrus.soil_profile_current || []).map((item) => ({
        label: `${item.depth_cm}cm`,
        value: item.theta
      }));

      // 根系吸水效率格式化
      const rawUptake = res.hydrus && res.hydrus.root_uptake_ratio;
      const uptakePct = rawUptake !== undefined && rawUptake !== null
        ? `${(parseFloat(rawUptake) * 100).toFixed(0)}%`
        : '-';

      this.setData({
        loading: false,
        result: res,
        mechanism: res.mechanism_explanation || {},
        yieldItems: chartItems(res.apsim && res.apsim.yield_curve || [], 'date', 'yield_kg_mu'),
        soilItems: chartItems(soil, 'label', 'value', 0.35),
        gppItems: chartItems(res.beps && res.beps.gpp_series || [], 'date', 'gpp'),
        nppItems: chartItems(res.beps && res.beps.npp_series || [], 'date', 'npp'),
        etItems: chartItems(res.beps && res.beps.et_series || [], 'date', 'et'),
        rootUptake: asPercent(rawUptake),
        rootUptakePct: uptakePct,
      });

      // 加载示范验证案例（可选，失败不影响主流程）
      this._loadValidationCases();
    } catch (error) {
      this.setData({ loading: false });
      wx.showToast({ title: '结果读取失败', icon: 'none' });
    }
  },

  async _loadValidationCases() {
    try {
      // 从后端加载示范案例（静态 JSON 也可以直接 require）
      const res = await request({ url: '/api/model/validation_cases' });
      if (Array.isArray(res)) {
        this.setData({ validationCases: res.slice(0, 3) });
      }
    } catch (_e) {
      // 失败时使用内置静态案例摘要
      this.setData({
        validationCases: [
          {
            case_id: 'case_001',
            case_name: '根区缺水 → 优先补灌',
            scenario: '连续少雨，灌溉量偏低，进入果实膨大期',
            expected_suggestion: '系统应识别中度至重度干旱并建议优先补灌',
            expert_check: '符合云南咖啡旱季补水管理经验',
            validation_result: '通过',
          },
          {
            case_id: 'case_002',
            case_name: '氮素偏低 + 土壤偏干 → 先补水再追肥',
            scenario: '氮素检测偏低，但近期土壤水分不足',
            expected_suggestion: '系统应建议先补水，待根区水分恢复后再少量追肥',
            expert_check: '符合农艺逻辑：土壤缺水时施肥，肥效释放受限',
            validation_result: '通过',
          },
          {
            case_id: 'case_003',
            case_name: '长势下降但水肥正常 → 巡园排查',
            scenario: '近期水肥管理正常，但长势评分和GPP持续下降',
            expected_suggestion: '系统应建议巡园检查遮阴、病虫害和冠层修剪',
            expert_check: '符合咖啡园管理经验：水肥正常时长势下降需排查冠层问题',
            validation_result: '通过',
          },
        ],
      });
    }
  },

  goAdvice() {
    wx.navigateTo({ url: '/pages/advice/advice' });
  }
});
