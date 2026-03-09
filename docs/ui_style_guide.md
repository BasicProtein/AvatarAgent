# AvatarAgent UI 设计规范
> 基于 Claude 官网（claude.ai / anthropic.com）风格研究，2026-03-03

---

## 一、设计哲学

Claude 的 UI 核心是 **"克制的温暖感"**：
- 不用鲜艳颜色博眼球，用质感和留白建立高级感
- 用字重和透明度传递层级，而非用颜色
- 所有交互元素保持一致的圆角半径，不混用
- 大量呼吸空间，拒绝信息堆砌

---

## 二、色彩系统

| Token | 值 | 用途 |
|---|---|---|
| `--color-bg-page` | `#FAF9F5` | 页面背景（温暖象牙白，非纯白）|
| `--color-bg-card` | `#FFFFFF` | 卡片/面板背景 |
| `--color-bg-hover` | `rgba(31,30,29,0.04)` | hover 背景 |
| `--color-text-primary` | `#141413` | 主文字（几乎纯黑，非 #000）|
| `--color-text-secondary` | `#737268` | 次要文字（暖灰）|
| `--color-text-tertiary` | `#9B9A94` | 辅助文字、placeholder |
| `--color-border` | `rgba(31,30,29,0.15)` | 通用边框（极细、半透明）|
| `--color-border-focus` | `rgba(31,30,29,0.5)` | 焦点/hover 边框 |
| `--color-primary` | `#141413` | 主操作色（深黑，即 Claude 橙棕品牌按钮也用深底）|
| `--color-primary-text` | `#FFFFFF` | 主按钮文字 |
| `--color-error` | `#C0392B` | 错误/危险（低饱和红）|
| `--color-success` | `#27AE60` | 成功（低饱和绿）|

---

## 三、圆角规范 ⭐ 最核心

按钮和 Badge 统一使用 **胶囊形圆角 `9999px`**，营造柔和、现代的视觉感。输入框等矩形控件保持 `10px` 圆角，形成层次对比。

| 场景 | 圆角值 |
|---|---|
| 主操作按钮（Primary） | `9999px`（胶囊形）|
| 次要按钮（Secondary/Ghost） | `9999px`（胶囊形）|
| Badge / Tag | `9999px`（胶囊形）|
| 输入框、Select | `10px` |
| 卡片/Panel | `16px` |
| 对话框/Modal | `20px` |
| 大圆形图标按钮 | `50%` |

> ✅ 按钮和标签统一使用 `9999px` 胶囊形圆角
> ❌ 禁止在同一页面内混用不同档位的圆角（如有些按钮 4px 有些 10px）

---

## 四、按钮规范

### 4.1 样式分级

| 级别 | 外观 | CSS 关键属性 |
|---|---|---|
| **Primary** | 深黑底 + 白字 | `background: #141413; color: #fff; border-radius: 9999px; padding: 10px 20px;` |
| **Secondary** | 透明底 + 极细边框 + 深色字 | `background: transparent; border: 0.67px solid rgba(31,30,29,0.15); border-radius: 9999px;` |
| **Ghost** | 无背景无边框 + 灰字 | hover 时出现浅背景 |
| **Danger** | 低饱和红底 | `background: #C0392B; color: #fff;` |

### 4.2 尺寸规范

| 尺寸 | 高度 | Padding | 字号 |
|---|---|---|---|
| `sm` | 32px | `6px 14px` | 13px |
| `md`（默认） | 40px | `10px 20px` | 14px |
| `lg` | 48px | `14px 24px` | 15px |

### 4.3 字重
所有按钮统一 `font-weight: 500`（Medium），不用 600/700

---

## 五、输入框规范

```css
.input {
  background: #FFFFFF;
  border: 0.67px solid rgba(31, 30, 29, 0.15);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 15px;
  color: #141413;
  transition: border-color 0.15s ease;
}

.input:focus {
  border-color: rgba(31, 30, 29, 0.5);
  outline: none;
  box-shadow: 0 0 0 3px rgba(31, 30, 29, 0.06);
}
```

---

## 六、卡片/面板规范

```css
.panel {
  background: #FFFFFF;
  border: 1px solid rgba(31, 30, 29, 0.08);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
```

---

## 七、间距规范

使用 4px 基础单位：

| Token | 值 | 用途 |
|---|---|---|
| `--space-1` | `4px` | 极小间距 |
| `--space-2` | `8px` | 组件内紧密元素 |
| `--space-3` | `12px` | 默认行间距 |
| `--space-4` | `16px` | 组件间距 |
| `--space-5` | `20px` | 区块内间距 |
| `--space-6` | `24px` | 标准内边距 |
| `--space-8` | `32px` | 大间距 |
| `--space-10` | `40px` | 超大间距/页面留白 |

---

## 八、字体规范

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
```

| 场景 | 字号 | 字重 |
|---|---|---|
| 页面大标题 | 28–32px | 600 |
| 区块标题 | 18–20px | 600 |
| 卡片标题 | 15–16px | 600 |
| 正文 | 14–15px | 400 |
| 说明文字 | 13px | 400 |
| 辅助标注 | 12px | 400/500 |

---

## 九、交互动效规范

- **所有 transition** 统一 `150ms ease`（快但不失丝滑）
- **Hover**：背景加深 `rgba(0,0,0,0.04)`，边框加深
- **Active/Press**：`transform: scale(0.98)`，轻微下压感
- **Loading**：按钮内 spinner，文字变为"处理中..."，按钮不消失

---

## 十、录音 UI 具体规范（声音训练模块）

### 三个状态

#### Idle（待机）
```
[ 麦克风图标 36px，暖灰色 ]
  标题文字："点击下方按钮开始录音"（14px，次要文字色）
  说明："建议在安静环境下录制 5-30 秒清晰人声"（12px，辅助色）
  [ Secondary 按钮："开始录音" ]
```

#### Recording（录音中）
```
[ 🔴 脉冲红点 + "录音中" + 计时器 "00:08" ]
  [ 波形动画：20根细条，交替高度动画 ]
  [ Danger 按钮："停止录音" ]
  说明："最长 60 秒"（12px）
```

#### Done（完成）
```
[ ✅ 绿色勾 36px ]
  "录音完成（00:11）"（14px）
  [ <audio> 原生播放器，圆角 10px，全宽 ]
  [ Secondary 按钮："重新录制" ]
```

### 容器样式
```css
.record-area {
  border: 1px solid rgba(31, 30, 29, 0.12);  /* 实线细边框，非虚线 */
  border-radius: 12px;
  background: rgba(250, 249, 245, 0.6);       /* 温暖象牙白底 */
  padding: 32px 24px;
  min-height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## 十一、开发注意事项

1. **Element Plus 覆盖**：使用 `:deep()` 覆盖 Element Plus 默认样式，特别是 `el-button`、`el-input` 的 `border-radius`
2. **按钮/Badge/Tag 用 `9999px` 胶囊形**，输入框等矩形控件用 `10px`
3. **边框用 rgba**：使用半透明边框而非固定颜色，适配深色模式
4. **克制动效**：`transition: all 0.15s ease`，hover 不要放大图标，只改颜色/背景
5. **留白优先**：宁可元素少，不要堆砌按钮和说明文字
