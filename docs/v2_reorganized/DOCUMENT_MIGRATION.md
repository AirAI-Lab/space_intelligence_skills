# 文档迁移映射表

> **旧文档**: `docs/*.md`
> **新文档**: `docs/v2_reorganized/`

---

## 1. 架构文档

| 旧文档 | 新文档 | 状态 |
|--------|--------|------|
| `AGENT_ARCHITECTURE_FINAL.md` | `01_architecture/OVERVIEW.md` | ✅ 整合 |
| `MULTI_AGENT_DESIGN.md` | `01_architecture/MULTI_AGENT_DESIGN.md` | 待迁移 |
| `SKYEDGE_AI_V3_TECHNICAL_MOAT.md` | `01_architecture/TECHNICAL_MOAT.md` | 待迁移 |
| `PRODUCT_V3_TECHNICAL_ANALYSIS.md` | `01_architecture/` | 待整合 |

## 2. 软件开发

| 旧文档 | 新文档 | 状态 |
|--------|--------|------|
| `IMPLEMENTATION_GUIDE.md` | `02_software/CLOUD_PLATFORM.md` | 待迁移 |
| `IMPLEMENTATION_STEPS_GUIDE.md` | `02_software/` | 待整合 |
| `CODE_SYNC_GUIDE.md` | `02_software/` | 待整合 |
| `DEPLOYMENT_GUIDE.md` | `02_software/DEPLOYMENT.md` | 待迁移 |
| - | `02_software/EDGE_INFER_FRAMEWORK.md` | ✅ 新建 |
| - | `02_software/PLUGIN_DEVELOPMENT.md` | 待新建 |

## 3. 算法开发

| 旧文档 | 新文档 | 状态 |
|--------|--------|------|
| `RCMT_FRAMEWORK_DESIGN_V2.md` | `03_algorithm/RCMT_FRAMEWORK.md` | ✅ 整合 |
| `RCMT_DELIVERY_CHECKLIST.md` | `03_algorithm/` | 待整合 |
| `RCMT_RECONSTRUCTION_SUMMARY.md` | `03_algorithm/` | 待整合 |
| `04_training.md` | `03_algorithm/TRAINING_GUIDE.md` | 待迁移 |
| `SOTA_ALGORITHM_ANALYSIS.md` | `03_algorithm/` | 待整合 |

## 4. 产品规划

| 旧文档 | 新文档 | 状态 |
|--------|--------|------|
| `PRODUCT_PROPOSAL_V1.md` | `04_product/PRODUCT_ROADMAP.md` | 待整合 |
| `PRODUCT_PROPOSAL_DETAILED.md` | `04_product/` | 待整合 |
| `02_PRODUCT_ROADMAP_FINAL.md` | `04_product/` | 待整合 |
| `PRODUCT_V2_COMPLETE_PROPOSAL.md` | `04_product/` | 待整合 |

## 5. 商业文档

| 旧文档 | 新文档 | 状态 |
|--------|--------|------|
| `BUSINESS_PLAN_20260216.md` | `05_business/BUSINESS_PLAN.md` | 待迁移 |
| `PITCH_DECK_ANGEL_V2.md` | `05_business/INVESTOR_GUIDE.md` | 待整合 |
| `INVESTOR_QUICK_GUIDE.md` | `05_business/INVESTOR_GUIDE.md` | 待整合 |
| `COMPREHENSIVE_ANALYSIS_20260216.md` | `05_business/` | 待整合 |

## 6. 战略文档

| 旧文档 | 新文档 | 状态 |
|--------|--------|------|
| `THREE_PHASE_STRATEGY.md` | `05_business/STRATEGY.md` | 待迁移 |
| `STRATEGIC_ANALYSIS_JUSHI_COMPETITIVE.md` | `05_business/` | 待整合 |
| `ULTIMATE_PROJECT_PLAN.md` | `05_business/` | 待整合 |

## 7. 归档文档 (不迁移)

以下文档保留在原位置但不迁移到新结构：

- `API_FIX_REPORT.md` - 已修复的API问题
- `FRONTEND_FIX*.md` - 已修复的前端问题
- `UPLOAD_*.md` - 已修复的上传问题
- `CODE_VERIFICATION_REPORT.md` - 一次性验证报告
- `templates.md` - 旧模板

## 8. 用户手册 (保留原位置)

- `user_manual/*.md` - 用户手册，保持不变
- `api/README.md` - API文档，保持不变

---

## 9. 迁移计划

### Phase 1 (已完成)
- [x] 创建新文档结构
- [x] 创建系统总览
- [x] 创建软件开发指南
- [x] 创建算法开发指南
- [x] 创建代理配置
- [x] 创建长期记忆

### Phase 2 (待执行)
- [ ] 迁移多智能体设计文档
- [ ] 迁移技术护城河文档
- [ ] 迁移部署指南
- [ ] 整合产品路线图

### Phase 3 (待执行)
- [ ] 整合商业文档
- [ ] 整合战略文档
- [ ] 清理冗余文档

---

**维护者**: SkyEdge AI Team
**最后更新**: 2026-03-06
