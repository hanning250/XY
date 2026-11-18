<script setup lang="ts">
/**
 * ★ 授权到期拦截页（全面停用时的门面）。
 *
 * 到期后整个界面只保留这一块：说清楚"什么时候到期的、要怎么办"，
 * 并给管理员一条立刻恢复的路（输入授权码）。
 *
 * 三个刻意的设计决定：
 *   ① 不隐藏、不伪装成"网络错误"——客户必须一眼知道是授权问题，
 *      否则运维会去查设备、查网络，白白折腾。
 *   ② 保留「退出登录」：非管理员看到的是"请联系管理员"，
 *      得能退出去把机器交给管理员操作。
 *   ③ 数据采集仍在后台跑（后端没停抓拍），所以文案说明
 *      「报警数据仍在采集，续期后不会丢」——避免客户以为数据断了。
 */
import { onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import LicensePanel from '@/components/LicensePanel.vue'
import { tokenStore } from '@/api'
import { useAuth } from '@/stores/auth'
import { useLicense } from '@/stores/license'

const license = useLicense()
const auth = useAuth()

onMounted(() => {
  // 授权接口在白名单里，到期也能查到"我是不是管理员"（决定能否续期）
  void auth.fetchMe()
})

async function logout() {
  try {
    await ElMessageBox.confirm('退出后需要重新登录才能续期，确定退出吗？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  tokenStore.clear()
  window.dispatchEvent(new CustomEvent('isup:unauthorized'))
}
</script>

<template>
  <div class="gate">
    <div class="card">
      <div class="bar" />
      <div class="body">
        <div class="lead">
          <div class="lead-title">授权已到期，系统已停用</div>
          <div class="lead-sub">
            报警看板、实时监控与管理功能已暂停。
            <template v-if="license.info?.expired && license.expireText">
              到期日 {{ license.expireText }}。
            </template>
            后台仍在继续采集报警数据，续期后即可恢复查看，不会丢数据。
          </div>
        </div>

        <LicensePanel gate />

        <div class="foot">
          <span class="foot-note">
            授权码由供应商提供。如已续期但仍显示此页，请刷新页面（Ctrl+F5）。
          </span>
          <el-button text @click="logout">退出登录</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 铺满整屏，不给下面的业务界面留任何可点区域 */
.gate {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: auto;
  background: radial-gradient(circle at 50% 22%, var(--surface-3) 0%, var(--stage) 72%);
}
.card {
  width: 560px;
  max-width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow-2);
  overflow: hidden;
}
/* 顶部一道品牌色条：与登录页、主界面同一套语言 */
.bar {
  height: 3px;
  background: linear-gradient(90deg, var(--brand-sky), var(--brand), var(--brand-deep));
}
.body {
  padding: 22px 24px 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.lead-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--danger);
  letter-spacing: 0.3px;
}
.lead-sub {
  margin-top: 8px;
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--text-2);
}
.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}
.foot-note {
  font-size: 11.5px;
  color: var(--text-3);
  line-height: 1.5;
}
</style>
