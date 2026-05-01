const { request } = require('../../utils/request');
const { savePlotId } = require('../../utils/storage');

Page({
  data: {
    saving: false,
    form: {
      plot_name: '潞江坝咖啡示范园',
      area_mu: 12.5,
      tree_age: 4,
      coffee_variety: '云南小粒咖啡',
      latitude: 24.93,
      longitude: 98.88,
      elevation_m: 850,
      soil_type: '赤红壤',
      shade_level: '中等遮阴',
      plant_density: 330,
      row_spacing_m: 2.0,
      plant_spacing_m: 1.5
    }
  },

  async submit(e) {
    const values = e.detail.value;
    const payload = {
      ...values,
      area_mu: Number(values.area_mu || 0),
      tree_age: Number(values.tree_age || 0),
      latitude: Number(values.latitude || 0),
      longitude: Number(values.longitude || 0),
      elevation_m: Number(values.elevation_m || 0),
      plant_density: Number(values.plant_density || 0),
      row_spacing_m: Number(values.row_spacing_m || 0),
      plant_spacing_m: Number(values.plant_spacing_m || 0)
    };
    this.setData({ saving: true });
    try {
      const res = await request({
        url: '/api/plot/init',
        method: 'POST',
        data: payload
      });
      savePlotId(res.plot_id);
      wx.showToast({ title: '建园已保存', icon: 'success' });
      setTimeout(() => wx.redirectTo({ url: '/pages/index/index' }), 500);
    } catch (error) {
      wx.showToast({ title: '保存失败', icon: 'none' });
    } finally {
      this.setData({ saving: false });
    }
  }
});
