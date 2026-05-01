function savePlotId(plotId) {
  wx.setStorageSync('plotId', plotId);
  getApp().globalData.plotId = plotId;
}

function getPlotId() {
  return wx.getStorageSync('plotId') || getApp().globalData.plotId || '';
}

function saveTaskId(taskId) {
  wx.setStorageSync('latestTaskId', taskId);
  getApp().globalData.latestTaskId = taskId;
}

function getTaskId() {
  return wx.getStorageSync('latestTaskId') || getApp().globalData.latestTaskId || '';
}

module.exports = {
  savePlotId,
  getPlotId,
  saveTaskId,
  getTaskId
};
