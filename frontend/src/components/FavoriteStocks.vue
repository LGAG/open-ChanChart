<template>
  <div class="favorite-stocks">
    <!-- 加载中骨架（首次加载时短暂闪现） -->
    <div v-if="loading && favorites.length === 0" class="fav-hint">加载中…</div>

    <!-- 空态 -->
    <el-empty
      v-else-if="favorites.length === 0"
      description="暂无收藏"
      :image-size="60"
    />

    <!-- 收藏列表：点击切换图表，× 取消收藏 -->
    <div v-else class="fav-list">
      <el-tag
        v-for="stock in favorites"
        :key="stock.code + '|' + stock.market"
        class="fav-tag"
        closable
        effect="plain"
        @click="handleSelect(stock)"
        @close="handleRemove(stock)"
      >
        {{ stock.code }} - {{ stock.name }}
      </el-tag>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getFavorites, removeFavorite } from '../api/favorite'

const emit = defineEmits(['select'])

const favorites = ref([])
const loading = ref(false)

const loadFavorites = async () => {
  loading.value = true
  try {
    const response = await getFavorites()
    if (response?.code === 200) {
      favorites.value = response.data || []
    }
  } catch (error) {
    ElMessage.error('加载收藏失败：' + (error?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 点击某只收藏 → 触发与搜索选中相同的图表加载链路（由 Home.vue 的 handleStockChange 处理）
const handleSelect = (stock) => {
  emit('select', stock)
}

// 取消收藏：乐观更新 + 失败回滚
const handleRemove = async (stock) => {
  const prev = favorites.value
  favorites.value = prev.filter(s => !(s.code === stock.code && s.market === stock.market))
  try {
    const response = await removeFavorite(stock)
    if (response?.code === 200 && response?.data?.removed) {
      ElMessage.success(`已取消收藏 ${stock.code}`)
    } else {
      // 后端未删到（记录可能已不存在）→ 保持已移除状态即可
      ElMessage.info(response?.message || '记录已不存在')
    }
  } catch (error) {
    favorites.value = prev  // 回滚
    ElMessage.error('取消收藏失败：' + (error?.message || '未知错误'))
  }
}

// 供父组件「收藏当前股票」后刷新列表
const refresh = () => loadFavorites()
defineExpose({ refresh })

onMounted(loadFavorites)
</script>

<style scoped>
.favorite-stocks {
  min-height: 40px;
}

.fav-hint {
  color: var(--text-dim);
  font-size: 13px;
  padding: 6px 0;
}

.fav-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.fav-tag {
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.fav-tag:hover {
  transform: translateY(-1px);
  box-shadow: var(--glow);
}

/* dark 主题下 plain tag 文字/边框可读性兜底 */
:deep(.fav-tag.el-tag) {
  color: var(--text);
  border-color: var(--panel-border);
  background: var(--panel-bg);
}
</style>
