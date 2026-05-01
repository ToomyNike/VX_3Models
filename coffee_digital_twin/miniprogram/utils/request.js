const { BASE_URL } = require('./config');

function request(options) {
  const url = options.url.startsWith('http') ? options.url : `${BASE_URL}${options.url}`;
  return new Promise((resolve, reject) => {
    wx.request({
      url,
      method: options.method || 'GET',
      data: options.data || {},
      timeout: options.timeout || 10000,
      header: {
        'content-type': 'application/json'
      },
      success(res) {
        console.info('[API]', options.method || 'GET', url, res.statusCode, res.data);
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        reject(new Error(res.data && res.data.message ? res.data.message : `HTTP ${res.statusCode}`));
      },
      fail(error) {
        console.error('[API_FAIL]', options.method || 'GET', url, error);
        reject(error);
      }
    });
  });
}

module.exports = {
  request
};
