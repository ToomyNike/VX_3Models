const { request } = require('../../utils/request');
const { getPlotId, saveTaskId } = require('../../utils/storage');

Page({
  data: {
    running: false,
    selected: 0,
    scenarios: [
      {
        name: '当前管理方案',
        extra_irrigation_mm: 0,
        extra_fertilizer_kg_mu: 0,
        note: '按已有建园和打卡数据运行'
      },
      {
        name: '明天补充滴灌',
        extra_irrigation_mm: 20,
        extra_fertilizer_kg_mu: 0,
        note: '比较补水后产量和水分状态'
      },
      {
        name: '暂不浇水',
        extra_irrigation_mm: 0,
        extra_fertilizer_kg_mu: 0,
        note: '观察水分胁迫是否加重'
      },
      {
        name: '本周少量追肥',
        extra_irrigation_mm: 0,
        extra_fertilizer_kg_mu: 8,
        note: '比较氮素状态和产量变化'
      }
    ]
  },

  choose(e) {
    this.setData({ selected: Number(e.currentTarget.dataset.index) });
  },

  async runModel() {
    const item = this.data.scenarios[this.data.selected];
    this.setData({ running: true });
    try {
      const result = await request({
        url: '/api/model/run',
        method: 'POST',
        data: {
          plot_id: getPlotId(),
          scenario: {
            scenario_name: item.name,
            extra_irrigation_mm: item.extra_irrigation_mm,
            extra_fertilizer_kg_mu: item.extra_fertilizer_kg_mu
          }
        }
      });
      saveTaskId(result.task_id);
      wx.navigateTo({ url: `/pages/result/result?task_id=${result.task_id}` });
    } catch (error) {
      wx.showToast({ title: '模型运行失败', icon: 'none' });
    } finally {
      this.setData({ running: false });
    }
  }
});
