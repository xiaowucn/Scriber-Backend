import pytest

from remarkable.pw_models.model import NewFileTree
from remarkable.db import pw_db
from remarkable.common.enums import TaskType


class TestNewFileTree:
    """NewFileTree model tests with real database - 基于业务验证逻辑"""

    @pytest.mark.gen_test
    async def test_find_default_valid_judge_task_with_scenario(self):
        """测试有效的 JUDGE 任务配置（需要 scenario_id）"""
        async with pw_db.transaction() as txn:
            # 创建有效的 JUDGE 配置：有 task_type 和 scenario_id
            parent = await pw_db.create(
                NewFileTree,
                name="parent_judge_valid",
                pid=0,
                ptree_id=0,
                default_molds=[3, 4],
                default_scenario_id=20,  # JUDGE 任务需要有 scenario_id
                default_task_type=TaskType.JUDGE.value,
            )

            child = await pw_db.create(
                NewFileTree,
                name="child_no_config",
                pid=0,
                ptree_id=parent.id,
                default_molds=[],
                default_scenario_id=None,
                default_task_type=None,
            )

            result = await NewFileTree.find_default(child.id)

            assert result is not None
            assert result.default_task_type == TaskType.JUDGE.value
            assert result.default_scenario_id == 20
            assert result.id == parent.id
            await txn.rollback()

    @pytest.mark.gen_test
    async def test_find_default_grandparent_or_self(self):
        async with pw_db.transaction() as txn:
            # 祖父节点：有效配置
            grandparent = await pw_db.create(
                NewFileTree,
                name="grandparent_valid",
                pid=0,
                ptree_id=0,
                default_molds=[1],
                default_scenario_id=5,
                default_task_type=TaskType.AUDIT.value,
            )

            parent = await pw_db.create(
                NewFileTree,
                name="parent_invalid",
                pid=0,
                ptree_id=grandparent.id,
                default_molds=[2],
                default_scenario_id=None,
                default_task_type=None,
            )

            # 子节点：无配置
            child = await pw_db.create(
                NewFileTree,
                name="child_no_config",
                pid=0,
                ptree_id=parent.id,
                default_molds=[],
                default_scenario_id=None,
                default_task_type=None,
            )

            result = await NewFileTree.find_default(child.id)

            # 应该跳过父节点的无效配置，找到祖父节点的有效配置
            assert result is not None
            assert result.default_task_type == TaskType.AUDIT.value
            assert result.default_scenario_id == 5
            assert result.id == grandparent.id

            await pw_db.update(child, default_task_type=TaskType.EXTRACT.value, default_scenario_id=None)
            result = await NewFileTree.find_default(child.id)
            # 找到自己
            assert result is not None
            assert result.default_task_type == TaskType.EXTRACT.value
            assert result.default_scenario_id is None
            assert result.id == child.id
            await txn.rollback()

    @pytest.mark.gen_test
    async def test_find_default_three_layer_finds_nearest_valid(self):
        """重点测试：三层结构中找到最近的有效配置"""
        async with pw_db.transaction() as txn:
            # 第一层：有效的 PDF2WORD 配置
            layer1 = await pw_db.create(
                NewFileTree,
                name="layer1_pdf2word",
                pid=0,
                ptree_id=0,
                default_molds=[1, 2],
                default_scenario_id=1,
                default_task_type=TaskType.PDF2WORD.value,
            )

            # 第二层：有效的 CLEAN_FILE 配置（更近）
            layer2 = await pw_db.create(
                NewFileTree,
                name="layer2_clean_file",
                pid=0,
                ptree_id=layer1.id,
                default_molds=[3, 4],
                default_scenario_id=2,
                default_task_type=TaskType.CLEAN_FILE.value,
            )

            # 第三层：目标节点，无配置
            layer3 = await pw_db.create(
                NewFileTree,
                name="layer3_target",
                pid=0,
                ptree_id=layer2.id,
                default_molds=[],
                default_scenario_id=None,
                default_task_type=None,
            )

            result = await NewFileTree.find_default(layer3.id)

            # 应该找到最近的有效配置（layer2），而不是 layer1
            assert result is not None
            assert result.default_task_type == TaskType.CLEAN_FILE.value
            assert result.default_scenario_id == 2
            assert result.id == layer2.id
            await txn.rollback()

    @pytest.mark.gen_test
    async def test_find_default_returns_none_when_no_task_type_anywhere(self):
        """测试当整个层级都没有 default_task_type 时返回 None"""
        async with pw_db.transaction() as txn:
            parent = await pw_db.create(
                NewFileTree,
                name="parent_no_task",
                pid=0,
                ptree_id=0,
                default_molds=[1, 2],
                default_scenario_id=None,
                default_task_type=None,
            )

            child = await pw_db.create(
                NewFileTree,
                name="child_no_task",
                pid=0,
                ptree_id=parent.id,
                default_molds=[],
                default_scenario_id=None,
                default_task_type=None,
            )

            result = await NewFileTree.find_default(child.id)

            assert result is None
            await txn.rollback()

    @pytest.mark.gen_test
    async def test_find_default_returns_none_when_tree_not_exists(self):
        """测试当树节点不存在时返回 None"""
        result = await NewFileTree.find_default(-1)
        assert result is None
