"""华夏营销部-标注章节比对 托管协议V1"""

from remarkable.predictor.eltype import ElementClass

predictor_options = [
    {
        "path": ["001托管协议当事人"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__托管协议当事人"],
                "skip_types": [ElementClass.IMAGE.value],
            },
        ],
    },
    {
        "path": ["002基金托管人对基金管理人的业务监督和核查"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__(基金)?托管人对(基金)?管理人的业务((监督|核查)[和与及、]?){2}"],
                "skip_types": [ElementClass.IMAGE.value],
            },
        ],
    },
    {
        "path": ["003基金管理人对基金托管人的业务核查"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_types": [ElementClass.IMAGE.value],
                "inject_syllabus_features": [
                    r"__regex__(基金)?管理人对(基金)?托管人的业务((监督|核查)[和与及、]?){1,2}"
                ],
            },
        ],
    },
    {
        "path": ["004基金财产的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_types": [ElementClass.IMAGE.value],
                "include_title": True,
                "inject_syllabus_features": [r"__regex__基金[财资]产的?保管的原则"],
            },
        ],
    },
    {
        "path": ["005基金资产净值计算和会计核算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_types": [ElementClass.IMAGE.value],
                "only_inject_features": True,
                "include_title": True,
                "inject_syllabus_features": [
                    r"__regex__净值的?(([计估]算|复核|完成)[和及与、]?){2,3}的?(时间及)?(程序)?",
                ],
            },
        ],
    },
    {
        "path": ["006基金份额持有人名册的保管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_types": [ElementClass.IMAGE.value],
                "inject_syllabus_features": [r"__regex__基金(份额)?持有人名册(的?((保管|登记)[与和及、]?){1,2})?"],
            },
        ],
    },
    {
        "path": ["007争议解决方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_types": [ElementClass.IMAGE.value],
                "inject_syllabus_features": [
                    r"__regex__适用法律[与和及]争议解决",
                    r"__regex__争议处理",
                ],
            },
        ],
    },
    {
        "path": ["008托管协议的变更、终止与基金财产的清算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "skip_types": [ElementClass.IMAGE.value],
                "only_inject_features": True,
                "multi": True,
                "include_title": True,
                "inject_syllabus_features": [
                    r"__regex__托管协议的?(变更|修改)(程序|$)",
                    r"__regex__托管协议的?终止((出现)?的?情形|$)",
                ],
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
