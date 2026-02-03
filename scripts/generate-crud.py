#!/usr/bin/env python3
"""
CRUD 代码生成器
用法: python generate-crud.py --name Device --fields "name,type,status"
"""

import argparse
from pathlib import Path

# 模板文件路径
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

def generate_entity(name, fields):
    """生成 Entity"""
    template = (TEMPLATE_DIR / "backend" / "entity.java").read_text()

    # 生成字段代码
    field_code = ""
    for field in fields.split(","):
        field_name = field.strip()
        field_code += f"""
    @Column(name = "{field_name}")
    private String {field_name};

"""

    content = template.replace("{{PACKAGE}}", "com.edge.cloud")
                    .replace("{{TABLE_NAME}}", name.lower())
                    .replace("{{TABLE_COMMENT}}", name)
                    .replace("{{ENTITY_NAME}}", name)
                    .replace("{{FIELDS}}", field_code)

    output_dir = Path("backend/src/main/java/com/edge/cloud/entity")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{name}.java").write_text(content)
    print(f"Generated: {name}.java")

def generate_repository(name):
    """生成 Repository"""
    template = (TEMPLATE_DIR / "backend" / "repository.java").read_text()

    content = template.replace("{{PACKAGE}}", "com.edge.cloud")
                    .replace("{{ENTITY_NAME}}", name)

    output_dir = Path("backend/src/main/java/com/edge/cloud/repository")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{name}Repository.java").write_text(content)
    print(f"Generated: {name}Repository.java")

def generate_service(name):
    """生成 Service"""
    template = (TEMPLATE_DIR / "backend" / "service.java").read_text()

    content = template.replace("{{PACKAGE}}", "com.edge.cloud")
                    .replace("{{ENTITY_NAME}}", name)

    output_dir = Path("backend/src/main/java/com/edge/cloud/service")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{name}Service.java").write_text(content)
    print(f"Generated: {name}Service.java")

def generate_controller(name, resource):
    """生成 Controller"""
    template = (TEMPLATE_DIR / "backend" / "controller.java").read_text()

    content = template.replace("{{PACKAGE}}", "com.edge.cloud")
                    .replace("{{ENTITY_NAME}}", name)
                    .replace("{{RESOURCE_NAME}}", resource)

    output_dir = Path("backend/src/main/java/com/edge/cloud/controller")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{name}Controller.java").write_text(content)
    print(f"Generated: {name}Controller.java")

def generate_frontend_list(name, resource, fields):
    """生成前端列表页面"""
    template = (TEMPLATE_DIR / "frontend" / "list-page.vue").read_text()

    # 生成表格列
    columns = ""
    for field in fields.split(","):
        field_name = field.strip()
        columns += f'      <el-table-column prop="{field_name}" label="{field_name}" />\n'

    content = template.replace("{{RESOURCE_NAME}}", resource)
                    .replace("{{TABLE_COLUMNS}}", columns)
                    .replace("{{QUERY_FIELDS_INIT}}", "")
                    .replace("{{QUERY_FIELDS_RESET}}", "")

    output_dir = Path(f"frontend/src/views/{resource}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "List.vue").write_text(content)
    print(f"Generated: List.vue")

def main():
    parser = argparse.ArgumentParser(description="CRUD代码生成器")
    parser.add_argument("--name", required=True, help="实体名称")
    parser.add_argument("--resource", help="资源名称（默认为实体名小写）")
    parser.add_argument("--fields", help="字段列表，逗号分隔")

    args = parser.parse_args()

    resource = args.resource or args.name.lower()
    fields = args.fields.split(",") if args.fields else ["name", "status"]

    print(f"Generating CRUD for {args.name}...")

    generate_entity(args.name, args.fields)
    generate_repository(args.name)
    generate_service(args.name)
    generate_controller(args.name, resource)
    generate_frontend_list(args.name, resource, args.fields)

    print("\n✅ CRUD code generated successfully!")
    print("\nNext steps:")
    print(f"1. Review generated files in backend/ and frontend/")
    print(f"2. Update field types and validations")
    print(f"3. Run: mvn clean package (backend)")
    print(f"4. Run: npm run dev (frontend)")

if __name__ == "__main__":
    main()
