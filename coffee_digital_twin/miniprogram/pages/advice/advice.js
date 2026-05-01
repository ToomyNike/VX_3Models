const { request } = require('../../utils/request');
const { getTaskId } = require('../../utils/storage');

Page({
  data: {
    loading: true,
    taskId: '',
    advice: {}
  },

  onShow() {
    this.setData({ taskId: getTaskId() });
    this.loadAdvice();
  },

  async loadAdvice() {
    this.setData({ loading: true });
    try {
      const res = await request({
        url: '/api/advice/generate',
        method: 'POST',
        data: {
          task_id: this.data.taskId
        }
      });
      this.setData({ loading: false, advice: res.advice || {} });
    } catch (error) {
      this.setData({ loading: false });
      wx.showToast({ title: '建议生成失败', icon: 'none' });
    }
  }
});
