# Git版本管理和回退指南

> **目的**: 教你如何安全地管理代码版本和回退
> **日期**: 2026-03-06

---

## 1. Git工作原理

### 1.1 核心概念

**Git不会覆盖代码！** 每次提交都会创建新的版本快照：

```
v1.1.0-doc-restructure (60ad90e) ← 当前版本
         ↑
v1.0.1-ota-enhancement (0bec492) ← 旧版本仍然存在
         ↑
更早的提交...
```

### 1.2 提交历史

所有提交都永久保存，你可以：
- 查看任何历史版本
- 回退到任何时间点
- 创建分支进行实验

---

## 2. 当前版本标记

### 2.1 标签 (Tags)

已创建的里程碑标签：

| 标签 | 提交哈希 | 日期 | 说明 |
|------|----------|------|------|
| `v1.1.0-doc-restructure` | 60ad90e | 2026-03-06 | 文档重组、自动化脚本 |
| `v1.0.1-ota-enhancement` | 0bec492 | 2026-02-06 | OTA升级功能增强 |

### 2.2 分支 (Branches)

当前分支：
- `main` - 主分支（最新代码）
- `backup-before-doc-restructure` - 文档重组前的备份分支

---

## 3. 如何回退到之前的版本

### 3.1 查看提交历史

```powershell
# 查看最近20次提交
git log --oneline -20

# 查看特定时间之前的提交
git log --before="2026-03-06" --oneline

# 查看特定文件的修改历史
git log --oneline -- docs/README.md
```

### 3.2 临时查看旧版本（不影响当前代码）

```powershell
# 查看某个标签的代码
git checkout v1.0.1-ota-enhancement

# 或查看某个提交
git checkout 0bec492

# 查看完成后返回最新版本
git checkout main
```

### 3.3 永久回退到某个版本

**方法1: 创建新分支保留当前版本，然后回退**

```powershell
# 1. 先保存当前工作（以防万一）
git branch backup-current-work

# 2. 回退到指定版本
git reset --hard v1.0.1-ota-enhancement

# 3. 如果需要恢复
git checkout backup-current-work
```

**方法2: 使用 revert 撤销特定提交（推荐）**

```powershell
# 撤销某次提交，但保留历史
git revert <commit-hash>

# 例如撤销今天的文档重组
git revert 60ad90e
```

### 3.4 恢复被删除的文件

```powershell
# 查看被删除的文件
git log --diff-filter=D --summary

# 恢复某个文件到指定版本
git checkout <commit-hash> -- <file-path>

# 例如恢复删除的 docs/README.md
git checkout 0bec492 -- docs/README.md
```

---

## 4. 安全工作流程

### 4.1 重要修改前创建备份分支

```powershell
# 做大改动前
git checkout -b feature/new-feature

# 或创建备份分支
git branch backup-$(Get-Date -Format 'yyyyMMdd')
```

### 4.2 使用标签标记里程碑

```powershell
# 完成重要功能后打标签
git tag -a v1.2.0-feature-name -m "功能描述"
git push origin v1.2.0-feature-name
```

### 4.3 定期创建备份分支

```powershell
# 每周创建备份
git branch weekly-backup-$(Get-Date -Format 'yyyyMMdd')
git push origin weekly-backup-*
```

---

## 5. 实用命令速查

### 查看命令

```powershell
# 查看提交历史
git log --oneline --graph --all

# 查看某次提交的详细内容
git show <commit-hash>

# 查看两个版本之间的差异
git diff v1.0.1-ota-enhancement v1.1.0-doc-restructure

# 查看某个文件的修改历史
git log -p -- <file-path>
```

### 恢复命令

```powershell
# 恢复工作区的修改
git checkout -- <file>

# 恢复暂存区的修改
git reset HEAD <file>

# 完全回退到某个版本
git reset --hard <commit-hash>

# 撤销某次提交
git revert <commit-hash>
```

### 分支管理

```powershell
# 创建并切换分支
git checkout -b <branch-name>

# 列出所有分支
git branch -a

# 删除本地分支
git branch -d <branch-name>

# 删除远程分支
git push origin --delete <branch-name>
```

---

## 6. 当前项目的版本策略

### 6.1 版本命名规范

- `v1.0.0` - 主要版本（重大变更）
- `v1.1.0` - 次要版本（新功能）
- `v1.0.1` - 修复版本（bug修复）

### 6.2 分支策略

- `main` - 稳定的生产分支
- `develop` - 开发分支（可选）
- `feature/*` - 功能分支
- `backup-*` - 备份分支

### 6.3 下次大改动前

```powershell
# 1. 创建备份分支
git branch backup-before-<feature-name>
git push origin backup-before-<feature-name>

# 2. 创建功能分支
git checkout -b feature/<feature-name>

# 3. 开发并测试...

# 4. 合并回main
git checkout main
git merge feature/<feature-name>

# 5. 打标签
git tag -a v1.x.x -m "功能描述"
git push origin v1.x.x
```

---

## 7. 常见问题

### Q1: 如何查看某个旧版本的所有文件？

```powershell
git checkout v1.0.1-ota-enhancement
# 浏览文件...
git checkout main  # 返回
```

### Q2: 如何比较两个版本的差异？

```powershell
# 查看文件列表差异
git diff --name-status v1.0.1 v1.1.0

# 查看具体内容差异
git diff v1.0.1 v1.1.0 -- docs/
```

### Q3: 如何找回被删除的提交？

```powershell
# 查看所有操作记录（包括已删除的提交）
git reflog

# 恢复到某个提交
git checkout <commit-hash>
```

### Q4: 误删了重要文件怎么办？

```powershell
# 从最近的提交恢复
git checkout HEAD -- <file-path>

# 从特定提交恢复
git checkout <commit-hash> -- <file-path>
```

---

## 8. 推荐：在GitHub上查看

最直观的方式是访问GitHub：

```
https://github.com/AirAI-Lab/edge_infer_cloud/commits/main
```

你可以：
- 浏览所有提交历史
- 查看每次提交的差异
- 下载任何版本的代码
- 比较不同版本

---

**总结**: 你的代码很安全！所有历史版本都永久保存在Git仓库中。如果需要回退，有很多方法可以恢复。

**维护者**: SkyEdge AI Team
**创建日期**: 2026-03-06
