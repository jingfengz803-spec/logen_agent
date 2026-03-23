// API服务调用示例 - JavaScript/TypeScript
// 可用于前端Vue/React项目

const BASE_URL = 'http://localhost:8088';

// ==================== API客户端类 ====================
class VideoCreationAPI {
  constructor(baseURL = BASE_URL, apiKey = null) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
    this.headers = {
      'Content-Type': 'application/json'
    };
    if (apiKey) {
      this.headers['Authorization'] = `Bearer ${apiKey}`;
    }
  }

  async request(method, path, data = null) {
    const url = `${this.baseURL}${path}`;
    const options = {
      method,
      headers: {
        ...this.headers,
        'X-Request-ID': `req_${Date.now()}`
      }
    };

    if (data) {
      options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    return await response.json();
  }

  // ==================== 健康检查 ====================
  async healthCheck() {
    return await this.request('GET', '/health');
  }

  // ==================== 抖音抓取 ====================
  async fetchUserVideos(url, maxCount = 100) {
    const data = {
      url,
      max_count: maxCount,
      enable_filter: true,
      min_likes: 50,
      min_comments: 0
    };
    const result = await this.request('POST', '/api/v1/douyin/fetch/user', data);
    return result.task_id;
  }

  async getTaskStatus(taskId) {
    return await this.request('GET', `/api/v1/douyin/task/${taskId}`);
  }

  async waitTask(taskId, onProgress = null, timeout = 300000) {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const result = await this.getTaskStatus(taskId);

      if (onProgress) {
        onProgress(result);
      }

      if (['success', 'failed', 'cancelled'].includes(result.status)) {
        return result;
      }

      await this.sleep(2000);
    }

    throw new Error(`任务超时: ${taskId}`);
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ==================== AI分析 ====================
  async analyzeViral(videoData) {
    const data = { video_data: videoData };
    const result = await this.request('POST', '/api/v1/ai/analyze/viral', data);
    return result.task_id;
  }

  async analyzeStyle(videoData) {
    const data = {
      video_data: videoData,
      analysis_dimensions: [
        '文案风格', '视频类型', '拍摄特征',
        '高频词汇', '标签策略', '音乐风格'
      ]
    };
    const result = await this.request('POST', '/api/v1/ai/analyze/style', data);
    return result.task_id;
  }

  async generateScript(referenceData, topic) {
    const data = {
      reference_data: referenceData,
      topic,
      target_duration: 30,
      tone: '专业'
    };
    const result = await this.request('POST', '/api/v1/ai/generate/script', data);
    return result.task_id;
  }

  // ==================== TTS语音 ====================
  async createVoice(audioUrl, prefix = 'myvoice') {
    const data = {
      audio_url: audioUrl,
      prefix,
      model: 'cosyvoice-v3.5-flash',
      wait_ready: true
    };
    const result = await this.request('POST', '/api/v1/tts/voice/create', data);
    return result.task_id;
  }

  async listVoices() {
    const result = await this.request('GET', '/api/v1/tts/voice/list');
    return result.voices || [];
  }

  async textToSpeech(text, voiceId) {
    const data = {
      text,
      voice_id: voiceId,
      output_format: 'mp3'
    };
    const result = await this.request('POST', '/api/v1/tts/speech', data);
    return result.task_id;
  }

  // ==================== 视频生成 ====================
  async generateVideo(videoUrl, audioUrl) {
    const data = {
      video_url: videoUrl,
      audio_url: audioUrl,
      video_extension: true
    };
    const result = await this.request('POST', '/api/v1/video/generate', data);
    return result.task_id;
  }

  // ==================== 完整工作流 ====================
  async runWorkflow(douyinUrl, topic, voiceId = null, workflowType = 'without_video') {
    const data = {
      douyin_url: douyinUrl,
      topic,
      voice_id: voiceId,
      workflow_type: workflowType,
      max_videos: 100
    };
    const result = await this.request('POST', '/api/v1/workflow/run', data);
    return result.task_id;
  }
}

// ==================== Vue 3 Composition API 示例 ====================
export function useVideoCreationAPI() {
  const api = new VideoCreationAPI();
  const loading = ref(false);
  const error = ref(null);
  const progress = ref({ status: '', progress: 0 });

  // 抓取视频
  const fetchVideos = async (url) => {
    loading.value = true;
    error.value = null;
    try {
      const taskId = await api.fetchUserVideos(url);
      const result = await api.waitTask(taskId, (p) => {
        progress.value = p;
      });
      return result;
    } catch (e) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  // 运行工作流
  const runWorkflow = async (douyinUrl, topic, voiceId) => {
    loading.value = true;
    error.value = null;
    try {
      const taskId = await api.runWorkflow(douyinUrl, topic, voiceId);
      const result = await api.waitTask(taskId, (p) => {
        progress.value = p;
      });
      return result;
    } catch (e) {
      error.value = e.message;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  return {
    loading,
    error,
    progress,
    fetchVideos,
    runWorkflow
  };
}

// ==================== 使用示例 ====================
async function exampleUsage() {
  const api = new VideoCreationAPI();

  // 1. 健康检查
  console.log('=== 健康检查 ===');
  const health = await api.healthCheck();
  console.log('服务状态:', health);

  // 2. 运行完整工作流
  console.log('\n=== 运行工作流 ===');
  const taskId = await api.runWorkflow(
    'https://www.douyin.com/user/MS4wLjABAAAA...',
    '如何应对职场PUA',
    null,  // 不指定音色
    'without_video'  // 不生成视频
  );

  // 3. 等待完成（带进度回调）
  const result = await api.waitTask(taskId, (progress) => {
    console.log(`进度: ${progress.progress}% - ${progress.status}`);
  });

  console.log('工作流完成:', result);
}

// React Hook 示例
export function useVideoCreation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState({ status: '', progress: 0 });

  const runWorkflow = async (douyinUrl, topic, voiceId) => {
    setLoading(true);
    setError(null);

    try {
      const api = new VideoCreationAPI();
      const taskId = await api.runWorkflow(douyinUrl, topic, voiceId);

      const result = await api.waitTask(taskId, (p) => {
        setProgress(p);
      });

      return result;
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  };

  return { loading, error, progress, runWorkflow };
}

// 导出
export default VideoCreationAPI;
