package {{PACKAGE}}.repository;

import {{PACKAGE}}.entity.{{ENTITY_NAME}};
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import java.util.*;

/**
 * {{TABLE_COMMENT}}Repository
 */
public interface {{ENTITY_NAME}}Repository extends
    JpaRepository<{{ENTITY_NAME}}, Long>,
    JpaSpecificationExecutor<{{ENTITY_NAME}}> {

    // 自定义查询方法
    List<{{ENTITY_NAME}}> findByStatus(String status);

    Optional<{{ENTITY_NAME}}> findBy{{UNIQUE_FIELD}}(String {{UNIQUE_FIELD}});
}
