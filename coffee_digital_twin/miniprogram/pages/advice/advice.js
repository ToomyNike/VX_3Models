const { request } = require('../../utils/request');
const { getTaskId } = require('../../utils/storage');

let _msgId = 0;
const nextId = () => ++_msgId;

Page({
  data: {
    taskId: '',
    messages: [],   // {id, role:'user'|'assistant', content}
    history: [],    // 传给后端的精简历史 [{role,content},...]
    inputText: '',
    typing: false,
    scrollTarget: 'bottom',
  },

  onShow() {
    const taskId = getTaskId();
    this.setData({ taskId });

    // 每次进入页面，若没有消息则自动获取初始建议
    if (this.data.messages.length === 0) {
      this._loadInitialAdvice(taskId);
    }
  },

  // ── 首次加载：调用 /generate 获取三段式建议 + model_basis 作为开场 ──
  // AI辅助生成-DeepSeek-V3 - 2026年5月3日 11:20:05 - 小程序端接入AI决策流展示
  async _loadInitialAdvice(taskId) {
    this.setData({ typing: true });
    try {
      const res = await request({
        url: '/api/advice/generate',
        method: 'POST',
        data: { task_id: taskId },
      });
      const a = res.advice || {};
      const basis = a.model_basis || {};

      // 拼接结构化开场白：what / how / why / model_basis
      const parts = [
        a.what ? `📊 当前状态\n${a.what}` : '',
        a.how  ? `✅ 建议操作\n${a.how}` : '',
        a.why  ? `🔬 为什么这样做\n${a.why}` : '',
      ];

      // 模型依据（三模型分列）
      const basisParts = [
        basis.apsim  ? `🌱 APSIM-Coffee：${basis.apsim}` : '',
        basis.hydrus ? `💧 HYDRUS-1D：${basis.hydrus}` : '',
        basis.beps   ? `🌳 BEPS-Lite：${basis.beps}` : '',
      ].filter(Boolean);
      if (basisParts.length > 0) {
        parts.push(`📌 模型依据\n${basisParts.join('\n')}`);
      }

      if (a.confidence_note) {
        parts.push(`ℹ️ ${a.confidence_note}`);
      }

      const opening = parts.filter(Boolean).join('\n\n');
      this._pushMessage('assistant', opening || '已加载三模型机理分析结果，请随时提问！');
    } catch (e) {
      this._pushMessage('assistant', '三模型数据加载完成，请随时向我提问关于咖啡园管理的问题。');
    } finally {
      this.setData({ typing: false });
    }
  },

  // ── 输入框 ──
  onInput(e) {
    this.setData({ inputText: e.detail.value });
  },

  // ── 发送消息 ──
  async onSend() {
    const text = (this.data.inputText || '').trim();
    if (!text || this.data.typing) return;

    // 显示用户消息，清空输入框
    this._pushMessage('user', text);
    this.setData({ inputText: '', typing: true });

    // 构造传给后端的历史（去掉 id，只保留 role+content）
    const history = this.data.messages
      .slice(0, -1)  // 不含刚加的用户消息（后端自己会加）
      .map(({ role, content }) => ({ role, content }));

    try {
      const res = await request({
        url: '/api/advice/chat',
        method: 'POST',
        data: {
          task_id: this.data.taskId,
          message: text,
          history,
        },
      });
      this._pushMessage('assistant', res.reply || '（未收到回复）');
    } catch (e) {
      this._pushMessage('assistant', '网络错误，请稍后重试。');
    } finally {
      this.setData({ typing: false });
    }
  },

  // ── 追加一条消息并自动滚动到底部 ──
  _pushMessage(role, content) {
    const msg = { id: nextId(), role, content };
    this.setData({
      messages: [...this.data.messages, msg],
      scrollTarget: '',
    });
    // 微延迟后重置 scrollTarget 触发滚动
    setTimeout(() => this.setData({ scrollTarget: 'bottom' }), 50);
  },
});
