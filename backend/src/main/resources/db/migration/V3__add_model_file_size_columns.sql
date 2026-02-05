-- 数据库迁移：添加模型表文件大小列
-- 执行方式：psql -U edge_user -d edge_cloud -f V3__add_model_file_size_columns.sql

-- 添加 PT、ONNX 和 Engine 文件大小列到 models 表
ALTER TABLE models ADD COLUMN IF NOT EXISTS pt_file_size_bytes BIGINT;
ALTER TABLE models ADD COLUMN IF NOT EXISTS onnx_file_size_bytes BIGINT;
ALTER TABLE models ADD COLUMN IF NOT EXISTS engine_file_size_bytes BIGINT;

-- 添加注释
COMMENT ON COLUMN models.pt_file_size_bytes IS 'PyTorch 文件大小（字节）';
COMMENT ON COLUMN models.onnx_file_size_bytes IS 'ONNX 文件大小（字节）';
COMMENT ON COLUMN models.engine_file_size_bytes IS 'TensorRT Engine 文件大小（字节）';
