from remarkable.config import project_root
from remarkable.pdfinsight.reader import PdfinsightReader

sample_path = f'{project_root}/data/tests/interdoc/octopus_1532_interdoc.zip'
merged_table_sample_path = f'{project_root}/data/tests/interdoc/ecitic_1802_interdoc.zip'
chinaamc_sample_path = f'{project_root}/data/tests/interdoc/chinaamc_939_interdoc.zip'
gffunds_sample1_path = f'{project_root}/data/tests/interdoc/gffunds_1829_interdoc.zip'
gffunds_sample2_path = f'{project_root}/data/tests/interdoc/gffunds_3657_interdoc.zip'
gffunds_sample3_path = f'{project_root}/data/tests/interdoc/gffunds_3658_interdoc.zip'


def test_fix_tables():
    interdoc = PdfinsightReader(sample_path)
    tables = interdoc.fix_tables()
    assert len(tables) == 2
    assert len(tables[0].tables) == 1
    assert len(tables[1].tables) == 11


def test_fix_tbl_merged():
    interdoc = PdfinsightReader(merged_table_sample_path)
    _, ele = interdoc.find_element_by_index(192)
    assert ele
    assert ele['merged'] == [[[0, 0], [0, 1]]]
    assert ele['cells'].get('0_0')
    assert ele['cells'].get('0_1')['dummy']
    assert ele['cells'].get('0_2')


def test_fix_tables_with_combo():
    interdoc = PdfinsightReader(chinaamc_sample_path)
    assert len(interdoc.table_dict) == 6
    assert len(interdoc.table_dict[32].tables) == 1
    assert len(interdoc.table_dict[33].tables) == 2
    assert len(interdoc.table_dict[36].tables) == 2
    assert len(interdoc.table_dict[41].tables) == 1


def test_fix_table_cells():
    """
    docs_scriber/-/issues/2287
    docs_scriber/-/issues/2337
    """
    interdoc1 = PdfinsightReader(gffunds_sample1_path)
    cells = interdoc1.table_dict[134].cells
    assert len(cells) == 18
    assert cells['0_2']['text'] == cells['0_3']['text']
    assert cells['1_0']['text'] == cells['0_0']['text']
    assert all(cells[idx]['dummy'] for idx in ('0_3', '1_0', '1_1', '1_4', '1_5'))

    interdoc2 = PdfinsightReader(gffunds_sample2_path)
    cells2 = interdoc2.table_dict[90].cells
    assert len(cells2) == 44
    assert cells2['6_0']['text'] == cells2['6_1']['text']
    assert all(cells2[idx]['dummy'] for idx in (f'{i}_1' for i in range(6, 11)))

    interdoc3 = PdfinsightReader(gffunds_sample3_path)
    cells3 = interdoc3.table_dict[502].cells
    assert len(cells3) == 36
    assert cells3['0_2']['text'] == cells3['0_3']['text']
    assert cells3['0_4']['text'] == cells3['1_4']['text']
    assert all(cells3[idx]['dummy'] for idx in ('1_0', '1_1', '1_4', '1_5', '1_6', '1_7', '1_8'))
