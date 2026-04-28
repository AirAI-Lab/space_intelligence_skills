package com.edge.cloud.repository;

import com.edge.cloud.entity.InferenceResult;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface InferenceResultRepository extends JpaRepository<InferenceResult, Long> {

    Page<InferenceResult> findByDeviceId(String deviceId, Pageable pageable);

    Page<InferenceResult> findBySource(String source, Pageable pageable);

    Page<InferenceResult> findByDeviceIdAndSource(String deviceId, String source, Pageable pageable);

    Page<InferenceResult> findByAlertLevelIsNotNull(Pageable pageable);

    Page<InferenceResult> findByAlertLevelIn(List<String> levels, Pageable pageable);

    @Query("SELECT r FROM InferenceResult r WHERE r.deviceId = :deviceId " +
           "AND r.time BETWEEN :startTime AND :endTime ORDER BY r.time DESC")
    Page<InferenceResult> findByDeviceIdAndTimeBetween(
            @Param("deviceId") String deviceId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            Pageable pageable);

    @Query("SELECT r FROM InferenceResult r WHERE " +
           "(:deviceId IS NULL OR r.deviceId = :deviceId) AND " +
           "(:source IS NULL OR r.source = :source) AND " +
           "(:alertLevel IS NULL OR (:alertLevel = 'any' AND r.alertLevel IS NOT NULL) OR r.alertLevel = :alertLevel) " +
           "ORDER BY r.time DESC")
    Page<InferenceResult> findWithFilters(
            @Param("deviceId") String deviceId,
            @Param("source") String source,
            @Param("alertLevel") String alertLevel,
            Pageable pageable);

    @Query("SELECT r FROM InferenceResult r WHERE " +
           "(:deviceId IS NULL OR r.deviceId = :deviceId) AND " +
           "(:source IS NULL OR r.source = :source) AND " +
           "(:alertLevel IS NULL OR (:alertLevel = 'any' AND r.alertLevel IS NOT NULL) OR r.alertLevel = :alertLevel) AND " +
           "r.time >= :startTime AND r.time <= :endTime " +
           "ORDER BY r.time DESC")
    Page<InferenceResult> findWithFiltersAndTime(
            @Param("deviceId") String deviceId,
            @Param("source") String source,
            @Param("alertLevel") String alertLevel,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            Pageable pageable);

    @Query("SELECT COUNT(r) FROM InferenceResult r WHERE r.time >= :since")
    long countSince(@Param("since") LocalDateTime since);

    @Query("SELECT COUNT(r) FROM InferenceResult r WHERE r.alertLevel IS NOT NULL AND r.time >= :since")
    long countAlertsSince(@Param("since") LocalDateTime since);

    @Query("SELECT r.alertLevel, COUNT(r) FROM InferenceResult r " +
           "WHERE r.alertLevel IS NOT NULL AND r.time >= :since GROUP BY r.alertLevel")
    List<Object[]> countByAlertLevelSince(@Param("since") LocalDateTime since);

    @Query("SELECT r.deviceId, COUNT(r), AVG(r.inferenceTimeMs) FROM InferenceResult r " +
           "WHERE r.time >= :since GROUP BY r.deviceId")
    List<Object[]> statsByDeviceSince(@Param("since") LocalDateTime since);

    @Query("SELECT FUNCTION('to_char', r.time, 'YYYY-MM-DD\"T\"HH24') AS hour, " +
           "COUNT(r) AS cnt, " +
           "SUM(CASE WHEN r.alertLevel IS NOT NULL THEN 1 ELSE 0 END) AS alertCnt " +
           "FROM InferenceResult r WHERE r.time >= :since " +
           "GROUP BY FUNCTION('to_char', r.time, 'YYYY-MM-DD\"T\"HH24') " +
           "ORDER BY hour")
    List<Object[]> hourlyTrendSince(@Param("since") LocalDateTime since);

    @Query("SELECT r.source, AVG(r.inferenceTimeMs) FROM InferenceResult r " +
           "WHERE r.time >= :since AND r.inferenceTimeMs IS NOT NULL GROUP BY r.source")
    List<Object[]> avgInferenceMsBySourceSince(@Param("since") LocalDateTime since);

    @Query("SELECT COUNT(r) FROM InferenceResult r WHERE r.source = :source AND r.time >= :since")
    long countBySourceSince(@Param("source") String source, @Param("since") LocalDateTime since);
}
