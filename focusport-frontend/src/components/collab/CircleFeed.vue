<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import SpaceButton from '../base/SpaceButton.vue'
import CreatePostModal from './CreatePostModal.vue'

const username = ref(localStorage.getItem('username') || 'guest')
const posts = ref([])
const loading = ref(false)
const hasMore = ref(true)
const page = ref(1)
const filterType = ref('all')
const showCreateModal = ref(false)
const openCommentsPostId = ref(null)
const commentInputs = ref({})
const commentSubmitting = ref({})

const filterTabs = [
  { value: 'all', label: '全部动态' },
  { value: 'friends', label: '好友动态' }
]

const loadPosts = async (reset = false) => {
  if (loading.value) return
  if (!reset && !hasMore.value) return

  loading.value = true
  try {
    if (reset) {
      page.value = 1
      posts.value = []
    }

    const response = await axios.get('/api/circle/posts', {
      params: {
        username: username.value,
        filter_type: filterType.value,
        page: page.value,
        page_size: 20
      }
    })

    const newPosts = response.data.posts || []
    if (reset) {
      posts.value = newPosts
    } else {
      posts.value.push(...newPosts)
    }
    hasMore.value = response.data.has_more
    page.value++
  } catch (error) {
    console.error('加载动态失败:', error)
  } finally {
    loading.value = false
  }
}

const refreshPosts = () => loadPosts(true)
const loadMore = () => loadPosts(false)

const toggleLike = async (post) => {
  try {
    const response = await axios.post(`/api/circle/posts/${post.id}/like`, {
      post_id: post.id,
      username: username.value
    })
    post.is_liked = response.data.liked
    post.likes_count += response.data.liked ? 1 : -1
  } catch (error) {
    console.error('点赞操作失败:', error)
  }
}

const toggleComments = (postId) => {
  openCommentsPostId.value = openCommentsPostId.value === postId ? null : postId
  if (openCommentsPostId.value === postId) {
    loadComments(postId)
  }
}

const comments = ref({})
const commentsLoading = ref({})

const loadComments = async (postId) => {
  commentsLoading.value[postId] = true
  try {
    const response = await axios.get(`/api/circle/posts/${postId}/comments`)
    comments.value[postId] = response.data.comments || []
  } catch (error) {
    console.error('加载评论失败:', error)
    comments.value[postId] = []
  } finally {
    commentsLoading.value[postId] = false
  }
}

const submitComment = async (post) => {
  const content = commentInputs.value[post.id]?.trim()
  if (!content) return

  commentSubmitting.value[post.id] = true
  try {
    await axios.post(`/api/circle/posts/${post.id}/comments`, {
      post_id: post.id,
      username: username.value,
      content
    })
    commentInputs.value[post.id] = ''
    post.comments_count++
    await loadComments(post.id)
  } catch (error) {
    console.error('发表评论失败:', error)
    alert(error.response?.data?.detail || '评论失败')
  } finally {
    commentSubmitting.value[post.id] = false
  }
}

const deletePost = async (post) => {
  if (!confirm('确定要删除这条动态吗？')) return
  try {
    await axios.delete(`/api/circle/posts/${post.id}`, {
      params: { username: username.value }
    })
    posts.value = posts.value.filter(p => p.id !== post.id)
  } catch (error) {
    console.error('删除动态失败:', error)
    alert(error.response?.data?.detail || '删除失败')
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

const onPostCreated = () => {
  showCreateModal.value = false
  refreshPosts()
}

onMounted(() => {
  loadPosts(true)
})
</script>

<template>
  <section class="circle-feed">
    <header class="feed-header">
      <div class="filter-tabs">
        <button
          v-for="tab in filterTabs"
          :key="tab.value"
          type="button"
          class="filter-tab"
          :class="{ active: filterType === tab.value }"
          @click="filterType = tab.value; refreshPosts()"
        >
          {{ tab.label }}
        </button>
      </div>
      <SpaceButton variant="primary" size="sm" @click="showCreateModal = true">
        ✏️ 发布动态
      </SpaceButton>
    </header>

    <div class="posts-timeline">
      <article v-for="post in posts" :key="post.id" class="post-card">
        <header class="post-header">
          <div class="user-avatar">{{ post.avatar }}</div>
          <div class="user-info">
            <strong class="username">{{ post.username }}</strong>
            <span class="post-time">{{ formatTime(post.created_at) }}</span>
          </div>
          <button
            v-if="post.username === username"
            type="button"
            class="delete-btn"
            @click="deletePost(post)"
          >
            ×
          </button>
        </header>

        <div class="post-content">{{ post.content }}</div>

        <div v-if="post.image_urls?.length" class="post-images">
          <img
            v-for="(url, idx) in post.image_urls.slice(0, 3)"
            :key="idx"
            :src="url"
            class="post-image"
            loading="lazy"
          />
        </div>

        <footer class="post-actions">
          <button
            type="button"
            class="action-btn"
            :class="{ liked: post.is_liked }"
            @click="toggleLike(post)"
          >
            <span class="action-icon">{{ post.is_liked ? '❤️' : '🤍' }}</span>
            <span>{{ post.likes_count || 0 }}</span>
          </button>

          <button
            type="button"
            class="action-btn"
            :class="{ active: openCommentsPostId === post.id }"
            @click="toggleComments(post.id)"
          >
            <span class="action-icon">💬</span>
            <span>{{ post.comments_count || 0 }}</span>
          </button>
        </footer>

        <!-- 评论区 -->
        <div v-if="openCommentsPostId === post.id" class="comments-section">
          <div v-if="commentsLoading[post.id]" class="comments-loading">
            加载中...
          </div>
          <div v-else-if="comments[post.id]?.length" class="comments-list">
            <div v-for="comment in comments[post.id]" :key="comment.id" class="comment-item">
              <span class="comment-avatar">{{ comment.avatar }}</span>
              <div class="comment-body">
                <strong>{{ comment.username }}</strong>
                <span>{{ comment.content }}</span>
              </div>
            </div>
          </div>
          <div v-else class="no-comments">暂无评论</div>

          <div class="comment-form">
            <input
              v-model="commentInputs[post.id]"
              type="text"
              placeholder="写评论..."
              class="comment-input"
              @keyup.enter="submitComment(post)"
            />
            <button
              type="button"
              class="comment-submit"
              :disabled="!commentInputs[post.id]?.trim() || commentSubmitting[post.id]"
              @click="submitComment(post)"
            >
              发送
            </button>
          </div>
        </div>
      </article>

      <div v-if="loading && posts.length === 0" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载动态中...</p>
      </div>

      <div v-else-if="!loading && posts.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <h3>还没有动态</h3>
        <p>发布第一条动态，开始你的社交之旅</p>
      </div>

      <div v-if="hasMore && posts.length > 0 && !loading" class="load-more">
        <button type="button" class="load-more-btn" @click="loadMore">
          加载更多
        </button>
      </div>
    </div>

    <CreatePostModal
      v-model:visible="showCreateModal"
      :username="username"
      @created="onPostCreated"
    />
  </section>
</template>

<style scoped>
.circle-feed {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
}

.filter-tab {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 20px;
  color: rgba(222, 240, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.9em;
}

.filter-tab:hover {
  background: rgba(255, 255, 255, 0.1);
}

.filter-tab.active {
  background: linear-gradient(180deg, rgba(49, 120, 255, 0.3), rgba(18, 35, 78, 0.9));
  border-color: rgba(115, 224, 255, 0.4);
  color: #eef7ff;
}

.posts-timeline {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-right: 4px;
}

.post-card {
  background: linear-gradient(180deg, rgba(14, 28, 58, 0.9), rgba(8, 16, 36, 0.95));
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 16px;
  padding: 16px;
}

.post-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.username {
  font-size: 0.95em;
  color: #eef7ff;
}

.post-time {
  font-size: 0.8em;
  color: rgba(222, 240, 255, 0.5);
}

.delete-btn {
  width: 28px;
  height: 28px;
  background: rgba(255, 100, 100, 0.1);
  border: none;
  border-radius: 8px;
  color: rgba(255, 150, 150, 0.8);
  font-size: 18px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.post-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(255, 100, 100, 0.2);
}

.post-content {
  font-size: 0.95em;
  line-height: 1.6;
  color: rgba(238, 247, 255, 0.9);
  margin-bottom: 12px;
  white-space: pre-wrap;
}

.post-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.post-image {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.2);
}

.post-actions {
  display: flex;
  gap: 16px;
  padding-top: 8px;
  border-top: 1px solid rgba(115, 224, 255, 0.1);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: rgba(222, 240, 255, 0.6);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: all 0.2s;
  font-size: 0.9em;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(222, 240, 255, 0.9);
}

.action-btn.liked {
  color: #ff6b9d;
}

.action-btn.active {
  color: #3b82f6;
}

.action-icon {
  font-size: 16px;
}

.comments-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(115, 224, 255, 0.1);
}

.comments-loading,
.no-comments {
  text-align: center;
  padding: 16px;
  color: rgba(222, 240, 255, 0.5);
  font-size: 0.9em;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.comment-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.comment-avatar {
  font-size: 20px;
  line-height: 1;
}

.comment-body {
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 0.9em;
}

.comment-body strong {
  color: #3b82f6;
  margin-right: 8px;
}

.comment-form {
  display: flex;
  gap: 8px;
}

.comment-input {
  flex: 1;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(115, 224, 255, 0.15);
  border-radius: 12px;
  color: #eef7ff;
  font-size: 0.9em;
}

.comment-input:focus {
  outline: none;
  border-color: rgba(115, 224, 255, 0.4);
}

.comment-submit {
  padding: 10px 16px;
  background: linear-gradient(180deg, #2fd8ff, #2d74ff);
  border: none;
  border-radius: 12px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.comment-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #eef7ff;
}

.empty-state p {
  margin: 0;
  color: rgba(222, 240, 255, 0.6);
}

.load-more {
  text-align: center;
  padding: 16px;
}

.load-more-btn {
  padding: 10px 24px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(115, 224, 255, 0.2);
  border-radius: 12px;
  color: rgba(222, 240, 255, 0.8);
  cursor: pointer;
  transition: all 0.2s;
}

.load-more-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(115, 224, 255, 0.4);
}
</style>
