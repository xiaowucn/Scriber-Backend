from remarkable.fintable.schema import FintableColumnConfig


def test_fintable_config():
    finconfig = FintableColumnConfig()
    finconfig.load_excel()

    # 正常转换
    assert finconfig.find_common_column("资产负债表", FintableColumnConfig.SYS_WINDPDF, "其中：质押借款") == "质押借款"

    # from_sys 中缺失，但与 common 一致
    assert finconfig.find_common_column("资产负债表", FintableColumnConfig.SYS_CSRC, "其他应交款") == "其他应交款"

    # 不存在的项
    assert finconfig.find_common_column("资产负债表", FintableColumnConfig.SYS_CSRC, "AAA") is None
