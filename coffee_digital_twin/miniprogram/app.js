App({
  globalData: {
    appName: '咖啡数字孪生',
    latestTaskId: '',
    plotId: ''
  },

  onLaunch() {
    this.globalData.latestTaskId = wx.getStorageSync('latestTaskId') || '';
    this.globalData.plotId = wx.getStorageSync('plotId') || '';
  }
});
