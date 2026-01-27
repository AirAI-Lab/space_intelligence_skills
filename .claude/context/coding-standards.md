# 编码规范和约定

## Java 后端编码规范

### 命名约定
```java
// 实体类
public class Dataset { }

// Repository
public interface DatasetRepository extends JpaRepository<Dataset, String> { }

// Service
public class DatasetService { }

// Controller
public class DatasetController { }

// DTO
public class DatasetDTO { }
```

### JPA 实体规范
```java
@Entity
@Table(name = "datasets")
@Data
public class Dataset {
    @Id
    @Column(name = "dataset_id", length = 50)
    private String datasetId;

    @Column(name = "dataset_name", nullable = false)
    private String datasetName;

    @Enumerated(EnumType.STRING)
    @Column(name = "dataset_type")
    private DatasetType datasetType;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
```

### Repository 方法命名
```java
// 查询方法
List<Dataset> findByStatus(DatasetStatus status);
List<Dataset> findByDatasetNameContainingIgnoreCase(String name);

// 分页查询（必须提供 Pageable 重载）
Page<Dataset> findByStatus(DatasetStatus status, Pageable pageable);

// 自定义查询
@Query("SELECT d FROM Dataset d WHERE d.status = 'READY'")
List<Dataset> findAvailableDatasets();
```

### Service 层规范
```java
@Service
@RequiredArgsConstructor // Lombok 构造器注入
public class DatasetService {
    private final DatasetRepository repository;

    // 事务方法添加 @Transactional
    @Transactional
    public DatasetDTO createDataset(DatasetCreateRequest request) {
        // ...
    }
}
```

### REST API 规范
```java
@RestController
@RequestMapping("/api/v1/datasets")
public class DatasetController {
    private final DatasetService service;

    @GetMapping
    public ApiResponse<PageResponse<DatasetDTO>> list(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int pageSize
    ) {
        // 返回统一格式
    }
}
```

## Python 训练服务规范

### 项目结构
```python
training/
├── app.py              # Flask API 入口
├── edge_train/
│   ├── __init__.py
│   ├── trainer.py       # 训练器
│   ├── converter.py     # 转换器
│   └── config.py        # 配置
└── requirements.txt
```

### 日志规范
```python
import logging

logger = logging.getLogger(__name__)

# 使用正确的日志级别
logger.debug("详细调试信息")
logger.info("重要流程节点")
logger.warning("警告但不影响运行")
logger.error("错误需要处理")
```

### 异常处理
```python
try:
    # 业务逻辑
    pass
except FileNotFoundError as e:
    logger.error(f"文件未找到: {file_path}")
    raise  # 重新抛出让上层处理
except Exception as e:
    logger.error(f"处理失败: {e}", exc_info=True)
    raise RuntimeError(f"任务失败: {e}")
```

## 前端 Vue 3 规范

### 组件命名
```vue
<!-- 组件文件名使用 PascalCase -->
<script setup lang="ts">
// API 调用使用 api 前缀
import { getDatasets } from '@/api/dataset'
</script>

<!-- 模板中使用 kebab-case -->
<dataset-list />
```

### API 调用
```typescript
// 使用 async/await
const loadData = async () => {
  loading.value = true
  try {
    const res = await getDatasets(page.value, pageSize.value)
    datasets.value = res.data.items
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}
```

## Docker 和部署规范

### 镜像命名
```bash
# 使用服务名作为镜像名
docker-backend:latest
docker-frontend:latest
docker-training:latest
```

### 环境变量
```bash
# 使用大写下划线
MQTT_BROKER_URL=tcp://localhost:1883
S3_ENDPOINT=http://seaweedfs:8333
BACKEND_API_URL=http://backend:8081
```

### 端口分配
| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | Vue 开发服务器 |
| 后端 | 8081 | Spring Boot |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |
| EMQX | 1883/18083 | MQTT |
| 训练服务 | 5002 | Flask |

## Git 提交规范

### Commit Message 格式
```
<type>: <subject>

<body>

<footer>
Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
</footer>
```

### Type 类型
- `feat`: 新功能
- `fix`: 修复 bug
- `refactor`: 重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具链相关

### 示例
```
feat: 实现 MQTT v5 回调集成

- 集成 MqttService 与 OtaService
- 添加设备状态上报处理
- 修复循环依赖问题

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>
```
