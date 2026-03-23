# API调用文档

## 目录
1. [启动服务](#启动服务)
2. [调用方式](#调用方式)
3. [完整调用示例](#完整调用示例)
4. [前端集成示例](#前端集成示例)

---

## 启动服务

```bash
# 进入API服务目录
cd python_services

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env

# 启动服务
python main.py
```

服务启动后:
- API地址: `http://localhost:8088`
- API文档: `http://localhost:8088/docs`

---

## 调用方式

### 1. curl 命令调用

#### 健康检查
```bash
curl http://localhost:8088/health
```

#### 抓取用户视频
```bash
curl -X POST "http://localhost:8088/api/v1/douyin/fetch/user" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "max_count": 100,
    "enable_filter": true,
    "min_likes": 50
  }'
```

#### 查询任务状态
```bash
curl http://localhost:8088/api/v1/douyin/task/{task_id}
```

#### 运行完整工作流
```bash
curl -X POST "http://localhost:8088/api/v1/workflow/run" \
  -H "Content-Type: application/json" \
  -d '{
    "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "topic": "如何应对职场PUA",
    "voice_id": "cosyvoice-v3.5-flash-xxx",
    "workflow_type": "without_video"
  }'
```

---

### 2. Python 调用

```python
import requests

API_BASE = "http://localhost:8088"

# 1. 健康检查
response = requests.get(f"{API_BASE}/health")
print(response.json())

# 2. 抓取视频
data = {
    "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "max_count": 100
}
response = requests.post(f"{API_BASE}/api/v1/douyin/fetch/user", json=data)
task_id = response.json()["task_id"]

# 3. 查询任务状态
response = requests.get(f"{API_BASE}/api/v1/douyin/task/{task_id}")
print(response.json())
```

---

### 3. JavaScript/TypeScript 调用

```javascript
const BASE_URL = 'http://localhost:8088';

// 使用 fetch API
async function fetchVideos(url) {
  const response = await fetch(`${BASE_URL}/api/v1/douyin/fetch/user`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url: url,
      max_count: 100
    })
  });
  const data = await response.json();
  return data.task_id;
}

// 轮询任务状态
async function waitTask(taskId) {
  while (true) {
    const response = await fetch(`${BASE_URL}/api/v1/douyin/task/${taskId}`);
    const data = await response.json();

    console.log(`进度: ${data.progress}% - ${data.status}`);

    if (['success', 'failed'].includes(data.status)) {
      return data;
    }

    await new Promise(resolve => setTimeout(resolve, 3000));
  }
}
```

---

### 4. Axios 调用

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8088',
  headers: { 'Content-Type': 'application/json' }
});

// 抓取视频
async function fetchVideos(url) {
  const { data } = await api.post('/api/v1/douyin/fetch/user', {
    url,
    max_count: 100
  });
  return data.task_id;
}

// 查询任务
async function getTaskStatus(taskId) {
  const { data } = await api.get(`/api/v1/douyin/task/${taskId}`);
  return data;
}
```

---

## 完整调用示例

### 完整工作流调用（Python）

```python
import requests
import time

API_BASE = "http://localhost:8088"

def run_workflow():
    # 1. 运行工作流
    data = {
        "douyin_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
        "topic": "如何应对职场PUA",
        "voice_id": "cosyvoice-v3.5-flash-xxx",
        "workflow_type": "without_video"
    }

    response = requests.post(f"{API_BASE}/api/v1/workflow/run", json=data)
    task_id = response.json()["task_id"]
    print(f"工作流任务ID: {task_id}")

    # 2. 轮询任务状态
    while True:
        response = requests.get(f"{API_BASE}/api/v1/workflow/task/{task_id}")
        result = response.json()

        status = result["status"]
        progress = result["progress"]

        print(f"进度: {progress}% - 状态: {status}")

        if status == "success":
            print("工作流完成!")
            print(result["result"])
            break
        elif status == "failed":
            print(f"工作流失败: {result['error']}")
            break

        time.sleep(5)

run_workflow()
```

---

## 前端集成示例

### Vue 3 Composition API

```vue
<template>
  <div class="workflow-container">
    <el-form @submit.prevent="handleSubmit">
      <el-form-item label="抖音链接">
        <el-input v-model="form.douyinUrl" />
      </el-form-item>
      <el-form-item label="主题">
        <el-input v-model="form.topic" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="runWorkflow" :loading="loading">
          运行工作流
        </el-button>
      </el-form-item>
    </el-form>

    <el-progress v-if="loading" :percentage="progress.progress" />

    <div v-if="result">
      <h3>生成结果</h3>
      <pre>{{ result }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const API_BASE = 'http://localhost:8088';

const form = ref({
  douyinUrl: '',
  topic: ''
});

const loading = ref(false);
const progress = ref({ progress: 0, status: '' });
const result = ref(null);

async function runWorkflow() {
  loading.value = true;
  progress.value = { progress: 0, status: '' };

  try {
    // 提交任务
    const { data } = await axios.post(`${API_BASE}/api/v1/workflow/run`, {
      douyin_url: form.value.douyinUrl,
      topic: form.value.topic,
      workflow_type: 'without_video'
    });

    const taskId = data.task_id;

    // 轮询状态
    while (true) {
      const { data: taskData } = await axios.get(
        `${API_BASE}/api/v1/workflow/task/${taskId}`
      );

      progress.value = taskData;

      if (taskData.status === 'success') {
        result.value = taskData.result;
        break;
      }
      if (taskData.status === 'failed') {
        alert('任务失败: ' + taskData.error);
        break;
      }

      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  } catch (error) {
    alert('请求失败: ' + error.message);
  } finally {
    loading.value = false;
  }
}
</script>
```

### React Hook

```jsx
import { useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8088';

export function useWorkflow() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ progress: 0, status: '' });
  const [result, setResult] = useState(null);

  const runWorkflow = async (douyinUrl, topic) => {
    setLoading(true);
    setProgress({ progress: 0, status: '' });

    try {
      // 提交任务
      const { data } = await axios.post(`${API_BASE}/api/v1/workflow/run`, {
        douyin_url: douyinUrl,
        topic,
        workflow_type: 'without_video'
      });

      const taskId = data.task_id;

      // 轮询状态
      while (true) {
        const { data: taskData } = await axios.get(
          `${API_BASE}/api/v1/workflow/task/${taskId}`
        );

        setProgress(taskData);

        if (taskData.status === 'success') {
          setResult(taskData.result);
          break;
        }
        if (taskData.status === 'failed') {
          throw new Error(taskData.error);
        }

        await new Promise(resolve => setTimeout(resolve, 3000));
      }
    } catch (error) {
      alert('请求失败: ' + error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  return { loading, progress, result, runWorkflow };
}
```

---

## 响应格式

所有API响应遵循统一格式：

```json
{
  "code": 200,
  "message": "success",
  "request_id": "req_xxx",
  "data": { ... }
}
```

任务相关接口返回：

```json
{
  "task_id": "xxx-xxx-xxx",
  "status": "running",
  "progress": 50,
  "result": { ... },
  "error": null
}
```
