package {{PACKAGE}}.service;

import {{PACKAGE}}.entity.{{ENTITY_NAME}};
import {{PACKAGE}}.repository.{{ENTITY_NAME}}Repository;
import {{PACKAGE}}.dto.{{ENTITY_NAME}}DTO;
import {{PACKAGE}}.exceptions.{{ENTITY_NAME}}NotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.BeanUtils;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * {{TABLE_COMMENT}}服务
 */
@Service
@RequiredArgsConstructor
public class {{ENTITY_NAME}}Service {

    private final {{ENTITY_NAME}}Repository repository;

    /**
     * 分页查询
     */
    public Page<{{ENTITY_NAME}}> findAll(Pageable pageable) {
        return repository.findAll(pageable);
    }

    /**
     * 根据ID查询
     */
    public {{ENTITY_NAME}} findById(Long id) {
        return repository.findById(id)
            .orElseThrow(() -> new {{ENTITY_NAME}}NotFoundException(id));
    }

    /**
     * 创建
     */
    @Transactional
    public {{ENTITY_NAME}} create({{ENTITY_NAME}}DTO dto) {
        {{ENTITY_NAME}} entity = new {{ENTITY_NAME}}();
        BeanUtils.copyProperties(dto, entity);
        return repository.save(entity);
    }

    /**
     * 更新
     */
    @Transactional
    public {{ENTITY_NAME}} update(Long id, {{ENTITY_NAME}}DTO dto) {
        {{ENTITY_NAME}} entity = findById(id);
        BeanUtils.copyProperties(dto, entity, "id", "createdAt");
        return repository.save(entity);
    }

    /**
     * 删除
     */
    @Transactional
    public void delete(Long id) {
        {{ENTITY_NAME}} entity = findById(id);
        repository.delete(entity);
    }
}
