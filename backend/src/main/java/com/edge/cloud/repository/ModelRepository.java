package com.edge.cloud.repository;

import com.edge.cloud.entity.Model;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * 模型数据访问接口
 */
@Repository
public interface ModelRepository extends JpaRepository<Model, String> {

    /**
     * 根据模型类型查询
     */
    List<Model> findByModelType(Model.ModelType modelType);

    /**
     * 根据模型类型查询（分页）
     */
    Page<Model> findByModelType(Model.ModelType modelType, Pageable pageable);

    /**
     * 根据状态查询
     */
    List<Model> findByStatus(Model.ModelStatus status);

    /**
     * 根据状态查询（分页）
     */
    Page<Model> findByStatus(Model.ModelStatus status, Pageable pageable);

    /**
     * 根据父模型ID查询子模型列表
     */
    List<Model> findByParentModelId(String parentModelId);

    /**
     * 根据数据集ID查询相关模型
     */
    List<Model> findByDatasetId(String datasetId);

    /**
     * 根据版本号查询
     */
    Optional<Model> findByVersion(String version);

    /**
     * 查询最新版本的模型
     */
    @Query("SELECT m FROM Model m WHERE m.modelName = :modelName ORDER BY m.createdAt DESC")
    List<Model> findLatestByName(String modelName);

    /**
     * 查询可部署的模型（状态为READY且有engine或onnx文件）
     */
    @Query("SELECT m FROM Model m WHERE m.status = 'READY' AND (m.engineFilePath IS NOT NULL OR m.onnxFilePath IS NOT NULL) ORDER BY m.createdAt DESC")
    List<Model> findDeployableModels();

    /**
     * 统计各状态的模型数量
     */
    @Query("SELECT m.status, COUNT(m) FROM Model m GROUP BY m.status")
    List<Object[]> countByStatus();
}
