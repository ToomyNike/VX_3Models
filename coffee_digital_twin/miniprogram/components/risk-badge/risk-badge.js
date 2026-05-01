Component({
  properties: {
    risk: {
      type: String,
      value: '低',
      observer(value) {
        this.updateRiskClass(value);
      }
    }
  },

  data: {
    riskClass: 'low'
  },

  lifetimes: {
    attached() {
      this.updateRiskClass(this.properties.risk);
    }
  },

  methods: {
    updateRiskClass(value) {
      const map = {
        '低': 'low',
        '中等': 'medium',
        '高': 'high'
      };
      this.setData({
        riskClass: map[value] || 'low'
      });
    }
  }
});
