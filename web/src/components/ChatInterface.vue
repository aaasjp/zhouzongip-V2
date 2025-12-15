<template>
  <div class="chat-layout">
    <!-- 左侧边栏：对话列表 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <el-button type="primary" @click="createNewChat" style="width: 100%;">
          + 新建对话
        </el-button>
      </div>
      
      <div class="sidebar-content">
        <div 
          v-for="session in sessions" 
          :key="session.session_id"
          :class="['session-item', { active: currentSessionId === session.session_id }]"
          @click="loadSession(session.session_id)"
        >
          <div class="session-content">
            <div class="session-title">{{ session.title || '新对话' }}</div>
            <div class="session-time">{{ formatTime(session.updated_at) }}</div>
          </div>
          <div class="session-actions" @click.stop>
            <el-button 
              type="danger" 
              size="small" 
              text
              @click="deleteSession(session.session_id)"
            >
              删除
            </el-button>
          </div>
        </div>
        
        <div v-if="sessions.length === 0" class="empty-sessions">
          <p>暂无对话记录</p>
          <p class="hint">点击"新建对话"开始聊天</p>
        </div>
      </div>
    </div>

    <!-- 右侧主区域：对话内容 + 结构化展示 -->
    <div class="main-content">
      <div class="conversation-pane">
        <div class="chat-header" v-if="currentSessionTitle">
          <h3>{{ currentSessionTitle }}</h3>
        </div>
        
        <div class="chat-messages" ref="messagesContainer">
          <div v-if="messages.length === 0 && !chatting" class="empty-chat">
            <p>开始新的对话吧！</p>
          </div>
          
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <div class="message-wrapper">
              <div 
                v-if="getStructuredItems(msg.content).length === 0 || msg.role !== 'assistant'"
                class="message-content markdown-body" 
                v-html="formatMessage(msg.content)"
              ></div>
              <div v-else class="message-content structured-preview">
                <!-- 显示总体说明 -->
                <div v-if="getStructuredDescription(msg.content)" class="message-description">
                  <div class="description-label">总体说明：</div>
                  <div class="description-content markdown-body" v-html="formatMessage(getStructuredDescription(msg.content))"></div>
                </div>
                <!-- 显示标题芯片 -->
                <div class="title-chips">
                  <span 
                    v-for="(item, idx) in getStructuredItems(msg.content)" 
                    :key="idx" 
                    class="title-chip" 
                    :class="{ script: item.type === 'script', active: isChipActive(item) }"
                    @click="selectStructuredItem(item)"
                  >
                    {{ item.title || '未命名' }}
                  </span>
                </div>
              </div>
              <div class="message-time">{{ formatTime(msg.created_at) }}</div>
              <div v-if="msg.sources && msg.sources.length > 0" class="sources">
                <strong>参考来源：</strong>
                <span v-for="(source, idx) in msg.sources" :key="idx">
                  <a :href="source.url" target="_blank">{{ source.name }}</a>
                  <span v-if="idx < msg.sources.length - 1">, </span>
                </span>
              </div>
              <div v-if="msg.suggested_questions && msg.suggested_questions.length > 0" class="suggested-questions">
                <span 
                  v-for="(q, idx) in msg.suggested_questions" 
                  :key="idx"
                  class="suggested-question"
                  @click="askQuestion(q)">
                  {{ q }}
                </span>
              </div>
            </div>
          </div>
          
          <div v-if="streaming" class="message assistant">
            <div class="message-wrapper">
              <div 
                v-if="getStructuredItems(currentAnswer).length === 0"
                class="message-content markdown-body" 
                v-html="formatMessage(currentAnswer)"
              ></div>
              <div v-else class="message-content structured-preview">
                <!-- 显示总体说明 -->
                <div v-if="getStructuredDescription(currentAnswer)" class="message-description">
                  <div class="description-label">总体说明：</div>
                  <div class="description-content markdown-body" v-html="formatMessage(getStructuredDescription(currentAnswer))"></div>
                </div>
                <!-- 显示标题芯片 -->
                <div class="title-chips">
                  <span 
                    v-for="(item, idx) in getStructuredItems(currentAnswer)" 
                    :key="idx" 
                    class="title-chip" 
                    :class="{ script: item.type === 'script', active: isChipActive(item) }"
                    @click="selectStructuredItem(item)"
                  >
                    {{ item.title || '未命名' }}
                  </span>
                </div>
              </div>
              <div class="message-time">正在输出...</div>
            </div>
          </div>
        </div>
        
        <div class="input-area">
          <div class="input-settings">
            <el-form :model="chatForm" inline>
              <el-form-item label="用户ID">
                <el-input 
                  v-model="chatForm.user_id" 
                  placeholder="请输入用户ID" 
                  style="width: 150px;"
                  size="small"
                />
              </el-form-item>
              <el-form-item label="租户代码">
                <el-input 
                  v-model="chatForm.tenant_code" 
                  placeholder="可选" 
                  style="width: 120px;"
                  size="small"
                />
              </el-form-item>
              <el-form-item label="组织代码">
                <el-input 
                  v-model="chatForm.org_code" 
                  placeholder="可选" 
                  style="width: 120px;"
                  size="small"
                />
              </el-form-item>
              <el-form-item label="对话模式">
                <el-select 
                  v-model="chatForm.chat_mode" 
                  placeholder="请选择" 
                  style="width: 150px;"
                  size="small"
                >
                  <el-option label="普通对话" value="general" />
                  <el-option label="创意生成" value="idea_gen" />
                  <el-option label="脚本生成" value="scripts_gen" />
                </el-select>
              </el-form-item>
              <el-form-item label="外部资源">
                <el-checkbox v-model="chatForm.use_external_resource" size="small">小红书</el-checkbox>
              </el-form-item>
              <el-form-item label="主题">
                <el-select 
                  v-model="chatForm.theme" 
                  placeholder="可选" 
                  style="width: 150px;"
                  size="small"
                >
                  <el-option label="默认" value="" />
                  <el-option label="理工男" value="tech_male" />
                  <el-option label="海外出差" value="overseas_trip" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="chatForm.use_vector_db" size="small">使用素材库</el-checkbox>
                <el-checkbox v-model="chatForm.stream" size="small">流式输出</el-checkbox>
              </el-form-item>
            </el-form>
          </div>
          
          <div class="uploaded-docs" v-if="uploadedDocs.length > 0">
            <div class="doc-tag" v-for="(doc, idx) in uploadedDocs" :key="idx" :class="{ 'doc-error': !doc.parse_success }">
              <span>{{ doc.file_name }}</span>
              <span v-if="doc.parse_success" class="doc-status">✓</span>
              <span v-else class="doc-status error">✗</span>
              <el-icon @click="removeDoc(idx)" class="doc-remove"><Close /></el-icon>
            </div>
          </div>
          
          <div class="input-box">
            <el-input 
              v-model="chatForm.question" 
              type="textarea" 
              :rows="3"
              placeholder="请输入您的问题... (Ctrl+Enter 发送)"
              @keyup.ctrl.enter="sendMessage"
              :disabled="chatting"
            />
            <div class="input-actions">
              <el-upload
                :action="'/chat_service/upload_and_parse'"
                :on-success="handleUploadAndParseSuccess"
                :on-error="handleUploadError"
                :before-upload="beforeUpload"
                :show-file-list="false"
                :multiple="true"
                :disabled="chatting"
              >
                <el-button :disabled="chatting">上传并解析文档</el-button>
              </el-upload>
              <el-button 
                type="primary" 
                @click="sendMessage" 
                :loading="chatting"
                :disabled="!chatForm.question || !chatForm.user_id"
              >
                发送
              </el-button>
              <el-button @click="clearChat" :disabled="chatting">清空</el-button>
            </div>
          </div>
        </div>
      </div>

      <div class="structured-pane" v-if="structuredItems.length > 0">
        <div class="structured-header">
          <div class="structured-title">
            {{ chatForm.chat_mode === 'idea_gen' ? '创意输出' : chatForm.chat_mode === 'scripts_gen' ? '脚本输出' : '结构化内容' }}
          </div>
        </div>
        <div class="structured-body" v-if="structuredItems.length > 0">
          <!-- 具体项目卡片 -->
          <div 
            class="structured-card" 
            v-for="(item, idx) in structuredItems" 
            :key="idx"
            :class="{ active: idx === activeStructuredIndex }"
          >
            <div class="structured-card-title">
              <span class="structured-tag" :class="{ script: item.type === 'script' }">
                {{ item.type === 'script' ? '脚本' : '创意' }}
              </span>
              <span class="structured-title-text">{{ item.title || '未命名' }}</span>
            </div>
            <div class="structured-card-content markdown-body" v-html="formatMessage(item.content)"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { Close } from '@element-plus/icons-vue'

export default {
  name: 'ChatInterface',
  components: {
    Close
  },
  data() {
    return {
      chatForm: {
        user_id: 'user001',
        tenant_code: '',
        org_code: '',
        question: '',
        use_vector_db: true,
        stream: true,
        session_id: '',
        chat_mode: 'general', // 对话模式：'general'普通对话, 'idea_gen'创意生成, 'scripts_gen'脚本生成
        use_external_resource: false,
        theme: ''
      },
      chatting: false,
      streaming: false,
      currentAnswer: '',
      messages: [],
      sessions: [],
      currentSessionId: '',
      currentSessionTitle: '',
      loadingSessions: false,
      uploadedDocs: [], // 上传的文档列表 [{file_name: '', file_url: '', content: '', parse_success: true}]
      structuredItems: [], // 结构化的创意/脚本输出
      structuredDescription: '', // 创意/脚本的总体说明
      activeStructuredIndex: 0, // 右侧高亮的卡片索引
      lastSources: [] // 最近一次助手回复的参考来源
    }
  },
  mounted() {
    this.loadSessions()
  },
  methods: {
    async loadSessions() {
      if (!this.chatForm.user_id) {
        return
      }
      
      this.loadingSessions = true
      try {
        const res = await axios.get('/chat_service/sessions', {
          params: {
            user_id: this.chatForm.user_id,
            tenant_code: this.chatForm.tenant_code || '',
            org_code: this.chatForm.org_code || '',
            limit: 50
          }
        })
        
        if (res.data.status === 'success') {
          this.sessions = res.data.data || []
        } else {
          ElMessage.error('加载对话列表失败：' + res.data.msg)
        }
      } catch (error) {
        ElMessage.error('加载对话列表失败：' + error.message)
      } finally {
        this.loadingSessions = false
      }
    },
    
    async createNewChat() {
      if (!this.chatForm.user_id) {
        ElMessage.warning('请先输入用户ID')
        return
      }
      
      // 生成新的session_id
      const sessionId = this.generateSessionId()
      
      try {
        const res = await axios.post('/chat_service/session', {
          user_id: this.chatForm.user_id,
          session_id: sessionId,
          title: '新对话',
          tenant_code: this.chatForm.tenant_code || '',
          org_code: this.chatForm.org_code || ''
        })
        
        if (res.data.status === 'success') {
          this.chatForm.session_id = sessionId
          this.currentSessionId = sessionId
          this.currentSessionTitle = '新对话'
          this.messages = []
          await this.loadSessions()
          ElMessage.success('新建对话成功')
        } else {
          ElMessage.error('新建对话失败：' + res.data.msg)
        }
      } catch (error) {
        ElMessage.error('新建对话失败：' + error.message)
      }
    },
    
    async loadSession(sessionId) {
      if (this.chatting) {
        ElMessage.warning('正在对话中，请稍候...')
        return
      }
      
      this.currentSessionId = sessionId
      this.chatForm.session_id = sessionId
      
      // 获取会话信息
      try {
        const sessionRes = await axios.get(`/chat_service/session/${sessionId}`)
        if (sessionRes.data.status === 'success') {
          const session = sessionRes.data.data
          this.currentSessionTitle = session.title || '新对话'
        }
      } catch (error) {
        console.error('获取会话信息失败：', error)
      }
      
      // 加载消息历史
      try {
        const res = await axios.get(`/chat_service/session/${sessionId}/messages`, {
          params: {
            limit: 100
          }
        })
        
        if (res.data.status === 'success') {
          this.messages = (res.data.data || []).map(msg => ({
            role: msg.role,
            content: msg.content,
            created_at: msg.created_at,
            sources: msg.sources || [],
            suggested_questions: msg.suggested_questions || []
          }))
          
          const lastAssistant = [...this.messages].reverse().find(m => m.role === 'assistant')
          const parsed = this.parseStructuredContent(lastAssistant?.content || '')
          this.structuredItems = parsed.items || []
          this.structuredDescription = parsed.description || ''
          this.lastSources = lastAssistant?.sources || []
          this.activeStructuredIndex = 0

          this.$nextTick(() => {
            this.scrollToBottom()
          })
        } else {
          ElMessage.error('加载消息历史失败：' + res.data.msg)
        }
      } catch (error) {
        ElMessage.error('加载消息历史失败：' + error.message)
      }
    },
    
    async deleteSession(sessionId) {
      try {
        await ElMessageBox.confirm(
          '确定要删除这个对话吗？',
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const res = await axios.delete(`/chat_service/session/${sessionId}`)
        
        if (res.data.status === 'success') {
          ElMessage.success('删除成功')
          
          // 如果删除的是当前对话，清空消息
          if (sessionId === this.currentSessionId) {
            this.messages = []
            this.currentSessionId = ''
            this.currentSessionTitle = ''
            this.chatForm.session_id = ''
          }
          
          // 重新加载会话列表
          await this.loadSessions()
        } else {
          ElMessage.error('删除失败：' + res.data.msg)
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败：' + error.message)
        }
      }
    },
    
    generateSessionId() {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    },
    
    async sendMessage() {
      if (!this.chatForm.user_id) {
        ElMessage.warning('请输入用户ID')
        return
      }
      if (!this.chatForm.question) {
        ElMessage.warning('请输入问题')
        return
      }

      // 如果没有session_id，先创建新会话
      if (!this.chatForm.session_id) {
        const sessionId = this.generateSessionId()
        try {
          const res = await axios.post('/chat_service/session', {
            user_id: this.chatForm.user_id,
            session_id: sessionId,
            title: this.chatForm.question.substring(0, 50),
            tenant_code: this.chatForm.tenant_code || '',
            org_code: this.chatForm.org_code || ''
          })
          
          if (res.data.status === 'success') {
            this.chatForm.session_id = sessionId
            this.currentSessionId = sessionId
            this.currentSessionTitle = this.chatForm.question.substring(0, 50)
            await this.loadSessions()
          } else {
            ElMessage.error('创建会话失败：' + res.data.msg)
            return
          }
        } catch (error) {
          ElMessage.error('创建会话失败：' + error.message)
          return
        }
      }

      const question = this.chatForm.question
      this.chatForm.question = ''
      
      this.messages.push({
        role: 'user',
        content: question,
        created_at: new Date().toISOString()
      })

      // 新问题时清空右侧结构化内容，等新输出再显示
      this.structuredItems = []
      this.structuredDescription = ''
      this.lastSources = []
      this.activeStructuredIndex = 0

      this.chatting = true
      this.streaming = this.chatForm.stream
      this.currentAnswer = ''

      try {
        if (this.chatForm.stream) {
          await this.sendStreamMessage(question)
        } else {
          await this.sendNormalMessage(question)
        }
        
        // 发送成功后重新加载会话列表（更新标题和时间）
        await this.loadSessions()
        // 清空已上传的文档
        this.uploadedDocs = []
      } catch (error) {
        ElMessage.error('发送失败：' + error.message)
        this.messages.push({
          role: 'assistant',
          content: '抱歉，发生了错误：' + error.message,
          created_at: new Date().toISOString()
        })
      } finally {
        this.chatting = false
        this.streaming = false
        this.$nextTick(() => {
          this.scrollToBottom()
        })
      }
    },
    
    async sendStreamMessage(question) {
      // 只传递解析成功的文档
      const uploadedDocs = this.uploadedDocs
        .filter(doc => doc.parse_success && doc.content)
        .map(doc => ({
          file_name: doc.file_name,
          file_url: doc.file_url,
          content: doc.content,
          parse_success: true
        }))
      
      const response = await fetch('/chat_service/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: this.chatForm.user_id,
          session_id: this.chatForm.session_id,
          question: question,
          tenant_code: this.chatForm.tenant_code || '',
          org_code: this.chatForm.org_code || '',
          use_vector_db: this.chatForm.use_vector_db && uploadedDocs.length === 0,
          uploaded_docs: uploadedDocs,
          stream: true,
          limit: 5,
          chat_mode: this.chatForm.chat_mode || 'general',
          use_external_resource: this.chatForm.use_external_resource,
          theme: this.chatForm.theme || ''
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6))
            if (data.error) {
              throw new Error(data.error)
            }
            if (data.done) {
              this.messages.push({
                role: 'assistant',
                content: data.content,
                sources: data.sources?.documents || [],
                suggested_questions: data.suggested_questions || [],
                created_at: new Date().toISOString()
              })
              const parsed = this.parseStructuredContent(data.content)
              this.structuredItems = parsed.items || []
              this.structuredDescription = parsed.description || ''
              this.lastSources = data.sources?.documents || []
              this.activeStructuredIndex = 0
              this.currentAnswer = ''
            } else {
              this.currentAnswer = data.content
              // 流式过程中实时解析，标题出现即生成卡片，内容出现即右侧更新
              const parsed = this.parseStructuredContent(this.currentAnswer)
              this.structuredItems = parsed.items || []
              this.structuredDescription = parsed.description || ''
              if (this.structuredItems.length > 0 && this.activeStructuredIndex >= this.structuredItems.length) {
                this.activeStructuredIndex = 0
              }
            }
          }
        }
      }
    },
    
    async sendNormalMessage(question) {
      // 只传递解析成功的文档
      const uploadedDocs = this.uploadedDocs
        .filter(doc => doc.parse_success && doc.content)
        .map(doc => ({
          file_name: doc.file_name,
          file_url: doc.file_url,
          content: doc.content,
          parse_success: true
        }))
      
      const res = await axios.post('/chat_service/chat', {
        user_id: this.chatForm.user_id,
        session_id: this.chatForm.session_id,
        question: question,
        tenant_code: this.chatForm.tenant_code || '',
        org_code: this.chatForm.org_code || '',
        use_vector_db: this.chatForm.use_vector_db && uploadedDocs.length === 0,
        uploaded_docs: uploadedDocs,
        stream: false,
        limit: 5,
        chat_mode: this.chatForm.chat_mode || 'general',
        use_external_resource: this.chatForm.use_external_resource,
        theme: this.chatForm.theme || ''
      })

      if (res.data.status === 'success') {
        this.messages.push({
          role: 'assistant',
          content: res.data.data.answer,
          sources: res.data.data.sources?.documents || [],
          suggested_questions: res.data.data.suggested_questions || [],
          created_at: new Date().toISOString()
        })
        const parsed = this.parseStructuredContent(res.data.data.answer)
        this.structuredItems = parsed.items || []
        this.structuredDescription = parsed.description || ''
        this.lastSources = res.data.data.sources?.documents || []
        this.activeStructuredIndex = 0
      } else {
        throw new Error(res.data.msg)
      }
    },
    
    askQuestion(question) {
      this.chatForm.question = question
      this.sendMessage()
    },
    
    clearChat() {
      this.messages = []
      this.currentSessionId = ''
      this.currentSessionTitle = ''
      this.chatForm.session_id = ''
      this.uploadedDocs = []
      this.structuredItems = []
      this.structuredDescription = ''
      this.activeStructuredIndex = 0
      this.lastSources = []
    },
    
    formatMessage(content) {
      if (!content) return ''
      try {
        // 使用marked渲染markdown
        return marked.parse(content, {
          breaks: true, // 支持换行
          gfm: true // 支持GitHub风格的markdown
        })
      } catch (error) {
        console.error('Markdown渲染错误:', error)
        // 如果渲染失败，回退到简单的HTML转义
        return content.replace(/\n/g, '<br>')
      }
    },
    
    formatTime(timeStr) {
      if (!timeStr) return ''
      const date = new Date(timeStr)
      const now = new Date()
      const diff = now - date
      
      // 如果是今天，只显示时间
      if (diff < 24 * 60 * 60 * 1000 && date.getDate() === now.getDate()) {
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      }
      
      // 如果是今年，显示月日和时间
      if (date.getFullYear() === now.getFullYear()) {
        return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
      }
      
      // 否则显示完整日期
      return date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    },
    
    scrollToBottom() {
      const container = this.$refs.messagesContainer
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    },
    
    handleUploadAndParseSuccess(response, file) {
      if (response.status === 'success') {
        // 处理多个文档的返回结果
        const results = Array.isArray(response.data) ? response.data : [response.data]
        let successCount = 0
        let failCount = 0
        
        results.forEach(doc => {
          if (doc.parse_success) {
            this.uploadedDocs.push({
              file_name: doc.file_name,
              file_url: doc.file_url,
              content: doc.content,
              parse_success: true
            })
            successCount++
          } else {
            // 解析失败的文档也添加到列表，但标记为失败
            this.uploadedDocs.push({
              file_name: doc.file_name,
              file_url: doc.file_url || '',
              content: '',
              parse_success: false,
              parse_error: doc.parse_error || '解析失败'
            })
            failCount++
          }
        })
        
        if (successCount > 0 && failCount === 0) {
          ElMessage.success(`成功上传并解析${successCount}个文档`)
        } else if (successCount > 0 && failCount > 0) {
          ElMessage.warning(`成功解析${successCount}个文档，${failCount}个文档解析失败`)
        } else {
          ElMessage.error('所有文档解析失败')
        }
      } else {
        ElMessage.error('文档上传失败：' + response.msg)
      }
    },
    
    handleUploadError(error) {
      ElMessage.error('文档上传失败：' + error.message)
    },
    
    beforeUpload(file) {
      // 可以在这里添加文件大小和类型验证
      const isLt50M = file.size / 1024 / 1024 < 50
      if (!isLt50M) {
        ElMessage.error('文件大小不能超过50MB')
        return false
      }
      return true
    },
    
    removeDoc(index) {
      this.uploadedDocs.splice(index, 1)
    },

    getStructuredItems(content) {
      const parsed = this.parseStructuredContent(content)
      return parsed.items || []
    },

    getStructuredDescription(content) {
      const parsed = this.parseStructuredContent(content)
      return parsed.description || ''
    },

    selectStructuredItem(item) {
      if (!item) return
      const idx = this.structuredItems.findIndex(
        it => it.title === item.title && it.type === item.type
      )
      if (idx !== -1) {
        this.activeStructuredIndex = idx
        this.$nextTick(() => {
          const container = this.$el.querySelector('.structured-body')
          const cards = container ? container.querySelectorAll('.structured-card') : []
          if (cards[idx]) {
            cards[idx].scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        })
      }
    },

    isChipActive(item) {
      const idx = this.structuredItems.findIndex(
        it => it.title === item.title && it.type === item.type
      )
      return idx === this.activeStructuredIndex
    },

    parseStructuredContent(content) {
      if (!content) return { items: [], description: '' }
      const results = []
      let description = ''
      const text = content
      const startTokens = [
        { type: 'idea', token: '[IDEA_START]', end: '[IDEA_END]' },
        { type: 'script', token: '[SCRIPT_START]', end: '[SCRIPT_END]' }
      ]
      const cleanTags = (str) => {
        return (str || '').replace(/\[(IDEA|SCRIPT)_START\]|\[(IDEA|SCRIPT)_END\]|\[TITLE_START\]|\[TITLE_END\]|\[END_TITLE\]|\[CONTENT_START\]|\[CONTENT_END\]|\[END_CONTENT\]/g, '').trim()
      }

      let cursor = 0
      while (cursor < text.length) {
        let next = null
        startTokens.forEach(t => {
          const idx = text.indexOf(t.token, cursor)
          if (idx !== -1 && (next === null || idx < next.idx)) {
            next = { ...t, idx }
          }
        })
        if (!next) break

        // 提取 [IDEA_START] 或 [SCRIPT_START] 之前的说明文本
        if (next.idx > cursor) {
          const descText = text.substring(cursor, next.idx).trim()
          if (descText) {
            description = descText
          }
        }

        const segmentStart = next.idx + next.token.length
        const nextEnd = text.indexOf(next.end, segmentStart)
        const segment = text.substring(segmentStart, nextEnd === -1 ? text.length : nextEnd)

        // 在新的格式中，一个IDEA_START/SCRIPT_START块内可能包含多个标题-内容对
        // 格式：[TITLE_START]标题1[TITLE_END][CONTENT_START]内容1[CONTENT_END][TITLE_START]标题2[TITLE_END][CONTENT_START]内容2[CONTENT_END]...
        const titleStartTag = '[TITLE_START]'
        const titleEndTag = '[TITLE_END]'
        const contentStartTag = '[CONTENT_START]'
        const contentEndTag = '[CONTENT_END]'

        // 循环解析segment中的所有标题-内容对
        let segmentCursor = 0
        while (segmentCursor < segment.length) {
          const titleStartIdx = segment.indexOf(titleStartTag, segmentCursor)
          if (titleStartIdx === -1) break

          // 查找标题结束标签
          const titleEndIdx = segment.indexOf(titleEndTag, titleStartIdx + titleStartTag.length)
          if (titleEndIdx === -1) break

          // 提取标题
          const title = segment.substring(titleStartIdx + titleStartTag.length, titleEndIdx)

          // 查找内容开始标签（应该在标题结束之后）
          const contentStartIdx = segment.indexOf(contentStartTag, titleEndIdx + titleEndTag.length)
          if (contentStartIdx === -1) {
            // 如果没有找到内容开始标签，只保存标题，内容为空
            results.push({
              type: next.type,
              title: cleanTags(title),
              content: ''
            })
            segmentCursor = titleEndIdx + titleEndTag.length
            continue
          }

          // 查找内容结束标签
          const contentEndIdx = segment.indexOf(contentEndTag, contentStartIdx + contentStartTag.length)
          if (contentEndIdx === -1) {
            // 如果没有找到内容结束标签，提取到下一个标题开始或segment结束
            const nextTitleStart = segment.indexOf(titleStartTag, contentStartIdx + contentStartTag.length)
            const bodyEnd = nextTitleStart !== -1 ? nextTitleStart : segment.length
            const body = segment.substring(contentStartIdx + contentStartTag.length, bodyEnd)
            results.push({
              type: next.type,
              title: cleanTags(title),
              content: cleanTags(body)
            })
            segmentCursor = contentStartIdx + contentStartTag.length
            break
          }

          // 提取内容
          const body = segment.substring(contentStartIdx + contentStartTag.length, contentEndIdx)
          results.push({
            type: next.type,
            title: cleanTags(title),
            content: cleanTags(body)
          })

          // 移动到当前内容结束之后，继续查找下一个标题-内容对
          segmentCursor = contentEndIdx + contentEndTag.length
        }

        cursor = nextEnd !== -1 ? nextEnd + next.end.length : text.length
      }

      return { items: results, description: description }
    }
  },
  
  watch: {
    'chatForm.user_id'() {
      this.loadSessions()
    }
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 200px);
  min-height: 600px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

/* 左侧边栏 */
.sidebar {
  width: 300px;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  background: white;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
  border: 1px solid transparent;
}

.session-item:hover {
  background: #f0f9ff;
  border-color: #b3d8ff;
}

.session-item.active {
  background: #e1f3ff;
  border-color: #409eff;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.session-time {
  font-size: 12px;
  color: #909399;
}

.session-actions {
  margin-left: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.empty-sessions {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}

.empty-sessions .hint {
  font-size: 12px;
  margin-top: 8px;
}

/* 右侧主区域 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: row;
  background: white;
}

.conversation-pane {
  flex: 1 1 60%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e4e7ed;
  min-width: 0;
}

.structured-pane {
  width: 40%;
  max-width: 520px;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #f7f9fc 0%, #f4f7fb 100%);
}

.chat-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.chat-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.structured-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
}

.structured-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
}

.structured-subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fafafa;
}

.structured-body {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.structured-description {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #b3d8ff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 8px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.08);
}

.structured-description-title {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.structured-description-title::before {
  content: '📋';
  font-size: 16px;
}

.structured-description-content {
  color: #303133;
  line-height: 1.6;
  font-size: 14px;
}

.structured-card {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
}

.structured-card.active {
  border-color: #409eff;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.12);
}

.structured-sources {
  padding: 0 20px 16px;
  font-size: 12px;
  color: #606266;
}

.structured-sources a {
  color: #409eff;
}

.structured-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.structured-tag {
  padding: 2px 8px;
  border-radius: 8px;
  background: #ecf5ff;
  color: #409eff;
  font-size: 12px;
  border: 1px solid #b3d8ff;
}

.structured-tag.script {
  background: #fef3e6;
  color: #e6a23c;
  border-color: #f3d19e;
}

.structured-title-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.structured-card-content {
  color: #303133;
}

.structured-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 24px;
  color: #909399;
  text-align: center;
  gap: 6px;
}

.structured-empty .hint {
  font-size: 12px;
  color: #c0c4cc;
}

.empty-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  font-size: 14px;
}

.message {
  margin-bottom: 24px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message-wrapper {
  max-width: 70%;
  display: flex;
  flex-direction: column;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
  line-height: 1.6;
}

.message.user .message-content {
  background: #409eff;
  color: white;
}

.message.assistant .message-content {
  background: white;
  border: 1px solid #e4e7ed;
  color: #303133;
}

.structured-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-description {
  padding: 12px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-left: 3px solid #409eff;
  border-radius: 8px;
  margin-bottom: 8px;
}

.description-label {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 6px;
}

.description-content {
  color: #303133;
  line-height: 1.6;
  font-size: 14px;
}

.title-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.title-chip {
  padding: 6px 12px;
  border-radius: 14px;
  background: linear-gradient(135deg, #1f7aff, #5aa9ff);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  border: 1px solid #1f7aff;
  line-height: 1.2;
  box-shadow: 0 6px 16px rgba(31, 122, 255, 0.18);
}

.title-chip.script {
  background: linear-gradient(135deg, #f0a500, #f5c163);
  color: #fff;
  border-color: #f0a500;
  box-shadow: 0 6px 16px rgba(240, 165, 0, 0.18);
}

.title-chip.active {
  border-color: #0d6efd;
  box-shadow: 0 0 0 2px rgba(13,110,253,0.28);
}

/* Markdown样式 */
.markdown-body {
  line-height: 1.6;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-body :deep(h1) {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body :deep(h3) {
  font-size: 1.25em;
}

.markdown-body :deep(p) {
  margin-bottom: 10px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-bottom: 10px;
  padding-left: 2em;
}

.markdown-body :deep(li) {
  margin-bottom: 4px;
}

.markdown-body :deep(blockquote) {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin-bottom: 10px;
}

.markdown-body :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
}

.markdown-body :deep(pre) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin-bottom: 10px;
}

.markdown-body :deep(pre code) {
  display: inline;
  max-width: auto;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

.markdown-body :deep(table) {
  border-spacing: 0;
  border-collapse: collapse;
  margin-bottom: 10px;
  width: 100%;
}

.markdown-body :deep(table th),
.markdown-body :deep(table td) {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
}

.markdown-body :deep(table th) {
  font-weight: 600;
  background-color: #f6f8fa;
}

.markdown-body :deep(table tr) {
  background-color: #fff;
  border-top: 1px solid #c6cbd1;
}

.markdown-body :deep(table tr:nth-child(2n)) {
  background-color: #f6f8fa;
}

.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(hr) {
  height: 0.25em;
  padding: 0;
  margin: 16px 0;
  background-color: #e1e4e8;
  border: 0;
}

.markdown-body :deep(img) {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #fff;
  border-radius: 4px;
  margin-bottom: 10px;
}

.markdown-body :deep(strong) {
  font-weight: 600;
}

.markdown-body :deep(em) {
  font-style: italic;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  padding: 0 4px;
}

.message.user .message-time {
  text-align: right;
}

.sources {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  padding: 0 4px;
}

.sources a {
  color: #409eff;
  text-decoration: none;
}

.sources a:hover {
  text-decoration: underline;
}

.suggested-questions {
  margin-top: 8px;
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  padding: 0 4px;
  overflow-x: auto;
}

.suggested-question {
  padding: 4px 12px;
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
  border-radius: 12px;
  cursor: pointer;
  font-size: 12px;
  color: #409eff;
  transition: all 0.2s;
}

.suggested-question:hover {
  background: #e1f3ff;
  border-color: #409eff;
}

/* 输入区域 */
.input-area {
  border-top: 1px solid #e4e7ed;
  background: white;
}

.uploaded-docs {
  padding: 8px 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.doc-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: #e1f3ff;
  border: 1px solid #b3d8ff;
  border-radius: 12px;
  font-size: 12px;
  color: #409eff;
}

.doc-tag span {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-tag .doc-status {
  margin-left: 6px;
  font-size: 12px;
  color: #67c23a;
}

.doc-tag .doc-status.error {
  color: #f56c6c;
}

.doc-tag.doc-error {
  background: #fef0f0;
  border-color: #fbc4c4;
  color: #f56c6c;
}

.doc-remove {
  cursor: pointer;
  font-size: 14px;
  margin-left: 6px;
}

.doc-remove:hover {
  color: #f56c6c;
}

.input-settings {
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}

.input-box {
  padding: 16px 20px;
}

.input-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 滚动条样式 */
.sidebar-content::-webkit-scrollbar,
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track,
.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.sidebar-content::-webkit-scrollbar-thumb,
.chat-messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover,
.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
