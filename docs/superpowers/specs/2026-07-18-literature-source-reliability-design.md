# 文学信源可靠性修复设计

## 目标

修复文学分类的三个独立采集故障：Scrapling fetcher 依赖缺失、失效的豆瓣 API 与 NYTimes 短暂连接超时，同时保持现有证据质量门槛。

## 设计

### Goodreads

- 将运行时依赖从 `scrapling` 改为 `scrapling[fetchers]`，确保 `StealthyFetcher` 的 `curl_cffi` 依赖随部署安装。
- 增加依赖导入测试；部署后由既有 `pip install -r requirements.txt` 安装。

### 豆瓣读书

- 移除返回 404 的 `j/search_subjects` API。
- 使用公开的豆瓣读书榜单页面作为 Scrapling 信源，保留来源 URL 与解析出的项目链接。
- 解析失败维持为单信源失败，不生成伪造证据。

### NYTimes RSS

- 对 `ConnectTimeout`、`ReadTimeout`、HTTP 429 和 HTTP 5xx 进行最多两次指数退避重试。
- 4xx（除 429）与内容解析错误不重试。
- 每次重试记录不含正文和凭据的诊断事件；耗尽重试后维持当前的单信源失败行为。

## 质量与验证

- 已有的证据不足校验保持不变。
- 测试覆盖 fetcher 依赖可用性、豆瓣榜单解析与临时错误的重试边界。
- 不增加第三方 API Key，不抓取需要登录的内容。
