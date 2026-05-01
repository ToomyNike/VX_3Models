const { request } = require('../../utils/request');
const { chartItems, asPercent } = require('../../utils/formatter');
const { getTaskId } = require('../../utils/storage');

Page({
  data: {
    loading: true,
    taskId: '',
    result: {},
    yieldItems: [],
    soilItems: [],
    gppItems: [],
    nppItems: [],
    etItems: [],
    rootUptake: '-'
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
    this.setData({ loading: true });
    try {
      const res = await request({ url: `/api/model/result/${this.data.taskId}` });
      const soil = (res.hydrus && res.hydrus.soil_profile_current || []).map((item) => ({
        label: `${item.depth_cm}cm`,
        value: item.theta
      }));
      this.setData({
        loading: false,
        result: res,
        yieldItems: chartItems(res.apsim && res.apsim.yield_curve || [], 'date', 'yield_kg_mu'),
        soilItems: chartItems(soil, 'label', 'value', 0.35),
        gppItems: chartItems(res.beps && res.beps.gpp_series || [], 'date', 'gpp'),
        nppItems: chartItems(res.beps && res.beps.npp_series || [], 'date', 'npp'),
        etItems: chartItems(res.beps && res.beps.et_series || [], 'date', 'et'),
        rootUptake: asPercent(res.hydrus && res.hydrus.root_uptake_ratio)
      });
    } catch (error) {
      this.setData({ loading: false });
      wx.showToast({ title: '结果读取失败', icon: 'none' });
    }
  },

  goAdvice() {
    wx.navigateTo({ url: '/pages/advice/advice' });
  }
});
