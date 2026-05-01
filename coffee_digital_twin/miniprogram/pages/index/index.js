const { request } = require('../../utils/request');
const { saveTaskId } = require('../../utils/storage');
const { asText } = require('../../utils/formatter');

Page({
  data: {
    loading: true,
    backendStatus: 'checking',
    backendText: '正在连接后端',
    dashboard: {},
    advice: {},
    latestTaskId: ''
  },

  onShow() {
    this.loadDashboard();
  },

  async loadDashboard() {
    this.setData({ loading: true });
    try {
      const res = await request({ url: '/api/dashboard' });
      if (res.task_id) {
        saveTaskId(res.task_id);
      }
      this.setData({
        loading: false,
        backendStatus: 'online',
        backendText: '后端已连接',
        latestTaskId: res.task_id || '',
        dashboard: res.dashboard || {},
        advice: res.advice || {}
      });
    } catch (error) {
      this.setData({
        loading: false,
        backendStatus: 'offline',
        backendText: '后端未连接'
      });
      wx.showToast({ title: '后端未连接', icon: 'none' });
    }
  },

  textValue(value) {
    return asText(value);
  },

  goPlotInit() {
    wx.navigateTo({ url: '/pages/plotInit/plotInit' });
  },

  goFarmLog() {
    wx.navigateTo({ url: '/pages/farmLog/farmLog' });
  },

  goScenario() {
    wx.navigateTo({ url: '/pages/scenario/scenario' });
  },

  goResult() {
    const suffix = this.data.latestTaskId ? `?task_id=${this.data.latestTaskId}` : '';
    wx.navigateTo({ url: `/pages/result/result${suffix}` });
  },

  goAdvice() {
    wx.navigateTo({ url: '/pages/advice/advice' });
  }
});
