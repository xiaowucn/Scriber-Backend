"""
模型相关任务（在线训练等）
"""

import logging

from remarkable.common.constants import PredictorTrainingStatus
from remarkable.common.util import loop_wrapper
from remarkable.db import peewee_transaction_wrapper
from remarkable.models.model_version import NewModelVersion
from remarkable.pw_models.model import NewMold
from remarkable.service.prompter import (
    extract_feature_v2,
    load_data_v2,
    predict_crude_answer_by_range,
    train_v2,
)
from remarkable.worker.app import app


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def update_predict_model(schema_id, mv_id=0, tree_l=None):
    from remarkable.predictor.helpers import create_predictor_prophet

    exp_flag = False
    try:
        # 读取标注数据集 `inv predictor.prepare-dataset 11 --start=592 --end=592`
        mold = await NewMold.find_by_id(schema_id)
        model_version = await NewModelVersion.find_by_id(mv_id)
        prophet = create_predictor_prophet(mold, model_version=model_version)
        await prophet.run_dump_dataset(None, None, tree_l=tree_l)
        # 训练 `inv predictor.train 11`
        await model_version.update_(**{"status": PredictorTrainingStatus.TRAINING.value})
        prophet.run_train()
    except Exception as exp:
        exp_flag = True
        logging.exception(exp)
    finally:
        status = PredictorTrainingStatus.ERROR.value if exp_flag else PredictorTrainingStatus.DONE.value
        await model_version.update_(**{"status": status})


@app.task
@loop_wrapper
@peewee_transaction_wrapper
async def update_model_v2(schema_id, cond=None, mv_id=0):
    from remarkable.service.new_question import batch_preset

    exp_flag = False
    mold = await NewMold.find_by_id(schema_id)
    try:
        # 读取文档数据和答案 `inv prompter.load-data-v2 5 --start=200 --end=300 --clear --update`
        await load_data_v2(schema_id, vid=mv_id, update=True, clear=True, cond=cond)
        if not mv_id:
            await mold.update_(progress=0.3, comment="v2 update complete")

        await NewModelVersion.update_by_pk(mv_id, status=PredictorTrainingStatus.TRAINING.value)
        # 生成训练数据 `inv prompter.extract-feature-v2 5 --start=200 --end=300`
        extract_feature_v2(schema_id, mv_id)
        if not mv_id:
            await mold.update_(progress=0.6, comment="v2 extract complete")

        # 训练 `inv prompter.train-v2 5`
        train_v2(schema_id, mv_id)
        if not mv_id:
            await mold.update_(progress=0.8, comment="v2 train complete")
        # else:
        #     await ModelVersion.update_by_pk(mv_id, **{'status': PrompterTrainingStatus.TRAIN.value})

        # 重跑定位&预测
        if not mv_id:
            await predict_crude_answer_by_range(
                None,
                None,
                mold=schema_id,
                overwrite=True,
                save=2,
                headnum=5,
                vid=mv_id,
            )  # 预测元素块
            await mold.update_(progress=0.9, comment="v2 prompt complete")
            await batch_preset(None, None, mold=schema_id, overwrite=True, save=2, headnum=5)  # 预测位置
            await mold.update_(progress=1.0, comment="v2 preset complete")
    except Exception as exp:
        exp_flag = True
        logging.exception(exp)
    finally:
        # 更新mold状态
        comment = "v2 error" if exp_flag else "v2 done"
        await mold.update_(b_training=0, comment=comment)
        if mv_id and exp_flag:
            await NewModelVersion.update_by_pk(mv_id, **{"status": PredictorTrainingStatus.ERROR.value})
