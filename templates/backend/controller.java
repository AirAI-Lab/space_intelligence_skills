package {{PACKAGE}}.controller;

import {{PACKAGE}}.entity.{{ENTITY_NAME}};
import {{PACKAGE}}.service.{{ENTITY_NAME}}Service;
import {{PACKAGE}}.dto.{{ENTITY_NAME}}DTO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;

/**
 * {{TABLE_COMMENT}}API
 */
@Tag(name = "{{TABLE_COMMENT}}", description = "{{TABLE_COMMENT}}管理")
@RestController
@RequestMapping("/api/v1/{{RESOURCE_NAME}}")
@RequiredArgsConstructor
public class {{ENTITY_NAME}}Controller {

    private final {{ENTITY_NAME}}Service service;

    @Operation(summary = "分页查询")
    @GetMapping
    public Page<{{ENTITY_NAME}}> list(Pageable pageable) {
        return service.findAll(pageable);
    }

    @Operation(summary = "根据ID查询")
    @GetMapping("/{id}")
    public {{ENTITY_NAME}} getById(@PathVariable Long id) {
        return service.findById(id);
    }

    @Operation(summary = "创建")
    @PostMapping
    public {{ENTITY_NAME}} create(@RequestBody {{ENTITY_NAME}}DTO dto) {
        return service.create(dto);
    }

    @Operation(summary = "更新")
    @PutMapping("/{id}")
    public {{ENTITY_NAME}} update(@PathVariable Long id, @RequestBody {{ENTITY_NAME}}DTO dto) {
        return service.update(id, dto);
    }

    @Operation(summary = "删除")
    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
