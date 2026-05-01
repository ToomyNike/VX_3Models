const { request } = require('../../utils/request');
const { getPlotId } = require('../../utils/storage');

Page({
  data: {
    saving: false,
    opIndex: 0,
    opValue: 'irrigation',
    opTypes: [
      { label: '灌溉', value: 'irrigation' },
      { label: '施肥', value: 'fertilization' },
      { label: '修剪/除草', value: 'canopy_management' },
      { label: '病虫害/冻害', value: 'damage_report' }
    ],
    today: ''
  },

  onLoad() {
    const today = new Date().toISOString().slice(0, 10);
    this.setData({ today });
  },

  changeOp(e) {
    const opIndex = Number(e.detail.value);
    this.setData({
      opIndex,
      opValue: this.data.opTypes[opIndex].value
    });
  },

  async submit(e) {
    const op = this.data.opTypes[this.data.opIndex];
    const values = e.detail.value;
    const payload = {
      plot_id: getPlotId(),
      op_type: op.value,
      date: values.date || this.data.today,
      amount: Number(values.amount || 0),
      unit: values.unit,
      fertilizer_type: values.fertilizer_type,
      operation_type: values.operation_type,
      severity: values.severity,
      remark: values.remark
    };

    this.setData({ saving: true });
    try {
      await request({ url: '/api/farmop/add', method: 'POST', data: payload });
      wx.showToast({ title: '打卡已保存', icon: 'success' });
      setTimeout(() => wx.redirectTo({ url: '/pages/index/index' }), 500);
    } catch (error) {
      wx.showToast({ title: '保存失败', icon: 'none' });
    } finally {
      this.setData({ saving: false });
    }
  }
});
