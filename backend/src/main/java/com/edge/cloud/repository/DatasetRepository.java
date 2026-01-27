package com.edge.cloud.repository;

import com.edge.cloud.entity.Dataset;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * 数据集数据访问接口
 */
@Repository
public interface DatasetRepository extends JpaRepository<Dataset, String> {

    /**
     * 根据数据集类型查询
     */
    List<Dataset> findByDatasetType(Dataset.DatasetType datasetType);

    /**
     * 根据状态查询
     */
    List<Dataset> findByStatus(Dataset.DatasetStatus status);

    /**
     * 根据状态查询（分页）
     */
    Page<Dataset> findByStatus(Dataset.DatasetStatus status, Pageable pageable);

    /**
     * 根据格式查询
     */
    List<Dataset> findByFormat(String format);

    /**
     * 模糊搜索数据集名称
     */
    List<Dataset> findByDatasetNameContainingIgnoreCase(String name);

    /**
     * 查询可用的数据集（状态为READY）
     */
    @Query("SELECT d FROM Dataset d WHERE d.status = 'READY' ORDER BY d.createdAt DESC")
    List<Dataset> findAvailableDatasets();
}
