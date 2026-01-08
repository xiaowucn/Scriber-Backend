import os
import shutil
from datetime import datetime
from pathlib import Path

from invoke import task

from remarkable.devtools import InvokeWrapper


def remove_empty_folders(path: Path, exclude_dirs=None):
    """
    删除所有空文件夹，可排除特定目录
    :param path: 要清理的根路径
    :param exclude_dirs: 要排除的目录名列表（如['.git', '.svn']）
    """
    if exclude_dirs is None:
        exclude_dirs = set()
    else:
        exclude_dirs = {Path(d).name for d in exclude_dirs}

    for p in path.iterdir():
        if p.is_dir():
            if p.name in exclude_dirs:
                continue
            remove_empty_folders(p, exclude_dirs)

    if path.is_dir() and not any(path.iterdir()) and path.name not in exclude_dirs:
        try:
            path.rmdir()
            print(f"已删除空文件夹: {path}")
        except OSError as e:
            print(f"无法删除 {path}：{e}")


@task(klass=InvokeWrapper)
async def clear_nonexistent_files(_):
    from remarkable.common.storage import localstorage
    from remarkable.db import pw_db
    from remarkable.models.new_file import NewFile

    # Collect filenames from database
    filenames_used = set()
    attrs = ["hash", "pdf", "docx", "pdfinsight"]
    files = await pw_db.execute(NewFile.select(NewFile.id, NewFile.hash, NewFile.pdf, NewFile.docx, NewFile.pdfinsight))

    for file in files:
        fields = [getattr(file, attr) for attr in attrs]
        for field in fields:
            if field is None:
                continue
            filenames_used.add(field)

    localstorage.clear_orphan_files(filenames_used, clear_cache=True)


def _get_source_paths():
    from remarkable.common.storage import localstorage

    return {
        "data_dir": {
            "path": Path(localstorage.root),
            "fields": ["hash", "pdf", "pdfinsight", "revise_docx", "revise_pdf", "docx", "meta_info"],
        },
        "cache_root": {
            "path": Path(localstorage.root, localstorage.cache_root),
            "fields": ["pdf"],
        },
        "label_cache_dir": {
            "path": Path(localstorage.root, localstorage.label_cache_dir),
            "fields": ["pdfinsight"],
        },
    }


@task(klass=InvokeWrapper)
async def migration_files(ctx):
    """
    迁移文件从旧的存储结构到新的时间层次结构

    将文件从 hash[:2]/hash[2:] 结构迁移到 year/month/day/hash[:2]/hash[2:] 结构
    """
    from remarkable.common.storage import localstorage
    from remarkable.common.util import add_time_hierarchy
    from remarkable.config import get_config
    from remarkable.db import pw_db
    from remarkable.models.new_file import NewFile

    # 检查是否启用了时间层次结构
    if not get_config("client.add_time_hierarchy", False):
        return

    # 获取所有文件记录
    files: list[NewFile] = list(await pw_db.execute(NewFile.select(include_deleted=True)))

    if not files:
        print("数据库中没有文件记录，无需迁移")
        return

    # 统计需要迁移的文件
    migration_stats = {"total": 0, "exists": 0, "missing": 0, "already_migrated": 0, "success": 0, "failed": []}

    # 分析文件状态
    print("开始文件迁移任务...")
    files_to_migrate = []
    source_paths = _get_source_paths()

    for file in files:
        for source_name, data in source_paths.items():
            source_dir = data.get("path")
            file_fields = data.get("fields", [])
            if not source_dir:  # 跳过空的源路径
                continue
            # 处理每个文件的多个字段
            for field_name in file_fields:
                field_value = getattr(file, field_name, None)
                # 判空：跳过空值
                if not field_value:
                    continue
                if field_name == "meta_info":
                    if not (field_value := field_value.get("raw_pdf")):
                        continue
                try:
                    # 检查可能的源路径
                    found_source = False
                    # 旧路径
                    old_path = source_dir / field_value[:2] / field_value[2:]

                    # 检查路径是否存在（文件或文件夹都可以）
                    if old_path.exists():
                        # 新路径：根据源路径类型确定目标路径
                        if field_name == "meta_info":
                            new_path = Path(add_time_hierarchy(file.created_utc, field_value, source_dir))
                        else:
                            if not (field_name_path := file.path(field_name)):
                                continue
                            new_path = source_dir / field_name_path

                        found_source = True
                        migration_stats["total"] += 1

                        if new_path.exists():
                            migration_stats["already_migrated"] += 1
                        else:
                            migration_stats["exists"] += 1
                            files_to_migrate.append((file, field_name, old_path, new_path, source_name))

                    # 如果在所有源路径中都没找到文件
                    if not found_source and source_name == "data_dir":
                        # 只记录data_dir的文件，其他都是临时文件，有可能不会产生
                        migration_stats["total"] += 1
                        migration_stats["missing"] += 1
                        print(f"警告: 文件<{file.id}>在源路径不存在 {field_value} (字段: {field_name})")

                except Exception as e:
                    print(f"警告: 构建文件路径失败 {file.id}.{field_name}={field_value}: {e}")
                    continue
    if migration_stats["exists"] == 0:
        print("没有需要迁移的文件")
        return

    # 显示统计信息
    print("\n文件状态统计:")
    print(f"  总文件数: {migration_stats['total']}")
    print(f"  需要迁移: {migration_stats['exists']}")
    print(f"  已经迁移: {migration_stats['already_migrated']}")
    print(f"  文件缺失: {migration_stats['missing']}")

    # 执行迁移
    print("\n开始迁移文件...")

    for i, (file, field_name, old_path, new_path, source_name) in enumerate(files_to_migrate):
        try:
            # 创建目标目录的父目录
            dst_root = Path(new_path).absolute()
            if old_path.is_file():
                # 文件时，创建父目录，并复制文件到父目录
                dst_root.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old_path, dst_root.parent)
            else:
                dst_root.mkdir(parents=True, exist_ok=True)
                # 移动路径和路径下的所有内容到新位置
                shutil.copytree(old_path, new_path, dirs_exist_ok=True)

            migration_stats["success"] += 1

            # 显示进度
            if (i + 1) % 100 == 0 or (i + 1) == len(files_to_migrate):
                print(
                    f"  迁移进度: {i + 1}/{len(files_to_migrate)} "
                    f"(成功: {migration_stats['success']}, 失败: {migration_stats['failed']})"
                )

        except Exception as e:
            migration_stats["failed"].append(old_path)
            print(
                f"  迁移失败: {old_path} -> {new_path} (文件ID: {file.id}, 字段: {field_name}, 源: {source_name}), 错误: {e}"
            )

    # 显示最终结果

    print(f"  成功迁移: {migration_stats['success']} 个文件")
    print(f"  迁移失败: {migration_stats['failed']} 个文件")

    if len(migration_stats["failed"]) > 0:
        print("  建议检查失败的文件并重新运行迁移")

    # 删除所有old_path,跳过失败的迁移
    for _, _, old_path, _, _ in files_to_migrate:
        if old_path in migration_stats["failed"]:
            continue
        if os.path.exists(old_path):
            if os.path.isfile(old_path):
                os.remove(old_path)
            else:
                shutil.rmtree(old_path)
    # 清空空文件夹
    remove_empty_folders(Path(localstorage.root))
    print("\n迁移完成!")


@task(klass=InvokeWrapper)
async def clean_files(ctx, start_date, end_date):
    """
    清除指定日期范围的本地文件缓存

    Args:
        ctx: invoke 上下文
        start_date: 起始日期字符串，格式为 YYYY-MM-DD (例如: 2025-08-01)
        end_date: 终止日期字符串，格式为 YYYY-MM-DD (例如: 2025-08-07)

    Usage:
        invoke clean-files --start-date=2025-08-01 --end-date=2025-08-07
    """
    from remarkable.common.storage import localstorage
    from remarkable.config import get_config
    from remarkable.db import pw_db
    from remarkable.models.new_file import NewFile

    # 检查是否启用了时间层次结构
    if not get_config("client.add_time_hierarchy", False):
        return

    source_paths = _get_source_paths()
    try:
        # 解析日期
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").timestamp()

        # 验证日期范围
        if start_dt > end_dt:
            print("错误: 起始日期不能晚于终止日期")
            return

        files: list[NewFile] = list(
            await pw_db.execute(
                NewFile.select(include_deleted=True).where(
                    NewFile.created_utc >= start_dt, NewFile.created_utc <= end_dt
                )
            )
        )
        if not files:
            print("没有找到匹配的缓存文件")
            return
        # 只删除原文件，不删除相关文件
        # 要考虑下docx、doc转后的pdf
        for file in files:
            print(f"正在删除缓存文件 {file.id}")
            if file.hash:
                localstorage.delete_file(file.path("hash"))
            if file.pdf:
                localstorage.delete_file(file.path("pdf"))
                shutil.rmtree(source_paths["cache_root"]["path"] / file.path("pdf"), ignore_errors=True)
            if file.pdfinsight:
                shutil.rmtree(source_paths["label_cache_dir"]["path"] / file.path("pdfinsight"), ignore_errors=True)

    except ValueError as e:
        print("错误: 日期格式不正确，请使用 YYYY-MM-DD 格式")
        print("示例: inv storage.clean-files --start-date=2025-08-01 --end-date=2025-08-07")
        print(f"详细错误: {e}")
    except Exception as e:
        print(f"清除缓存时发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import asyncio

    from invoke import Context

    # asyncio.run(migration_files(Context()))
    asyncio.run(clean_files(Context(), start_date="2024-04-29", end_date="2025-08-30"))
