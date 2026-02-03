package {{PACKAGE}}.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

/**
 * {{TABLE_COMMENT}}实体
 */
@Entity
@Table(name = "{{TABLE_NAME}}")
@Data
public class {{ENTITY_NAME}} {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    {{FIELDS}}

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
