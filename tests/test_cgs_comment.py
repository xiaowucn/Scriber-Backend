import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

from remarkable.plugins.cgs.services.comment import remove_docx_formatting_nodes


class TestRemoveDocxFormattingNodes:
    """Test cases for remove_docx_formatting_nodes function"""

    def create_test_docx(self, temp_dir: Path, include_highlight=True, include_color=True, include_schemeClr=False, include_textFill=False) -> Path:
        """
        创建一个包含测试XML内容的DOCX文件

        Args:
            temp_dir: 临时目录
            include_highlight: 是否包含highlight节点
            include_color: 是否包含color节点
            include_schemeClr: 是否包含schemeClr节点
            include_textFill: 是否包含textFill节点

        Returns:
            创建的DOCX文件路径
        """
        docx_path = temp_dir / "test.docx"

        # 创建DOCX文件结构
        word_dir = temp_dir / "docx_content" / "word"
        word_dir.mkdir(parents=True, exist_ok=True)

        # 创建header1.xml内容
        header_content = '<?xml version="1.0" encoding="UTF-8"?>'
        header_content += '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        header_content += "<w:p><w:r><w:rPr>"

        if include_highlight:
            header_content += '<w:highlight w:val="yellow"/>'
        if include_color:
            header_content += '<w:color w:val="FF0000"/>'
        if include_schemeClr:
            header_content += '<a:schemeClr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="accent1"/>'
        if include_textFill:
            header_content += '<a:textFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill><a:srgbClr val="FF0000"/></a:solidFill></a:textFill>'

        header_content += "</w:rPr><w:t>Header text</w:t></w:r></w:p></w:hdr>"

        header_file = word_dir / "header1.xml"
        header_file.write_text(header_content, encoding="utf-8")

        # 创建footer1.xml内容
        footer_content = '<?xml version="1.0" encoding="UTF-8"?>'
        footer_content += '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        footer_content += "<w:p><w:r><w:rPr>"

        if include_highlight:
            footer_content += '<w:highlight w:val="green"/>'
        if include_color:
            footer_content += '<w:color w:val="0000FF"/>'
        if include_schemeClr:
            footer_content += '<a:schemeClr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="accent2"/>'
        if include_textFill:
            footer_content += '<a:textFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill><a:srgbClr val="00FF00"/></a:solidFill></a:textFill>'

        footer_content += "</w:rPr><w:t>Footer text</w:t></w:r></w:p></w:ftr>"

        footer_file = word_dir / "footer1.xml"
        footer_file.write_text(footer_content, encoding="utf-8")

        # 创建document.xml（也会被处理）
        document_content = '<?xml version="1.0" encoding="UTF-8"?>'
        document_content += '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        document_content += "<w:body><w:p><w:r><w:rPr>"
        document_content += '<w:highlight w:val="cyan"/><w:color w:val="00FF00"/>'
        if include_schemeClr:
            document_content += '<a:schemeClr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="accent3"/>'
        if include_textFill:
            document_content += '<a:textFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill><a:srgbClr val="0000FF"/></a:solidFill></a:textFill>'
        document_content += "</w:rPr><w:t>Document text</w:t></w:r></w:p></w:body></w:document>"

        document_file = word_dir / "document.xml"
        document_file.write_text(document_content, encoding="utf-8")

        # 创建styles.xml
        styles_content = '<?xml version="1.0" encoding="UTF-8"?>'
        styles_content += '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        styles_content += '<w:style w:type="paragraph"><w:rPr>'
        if include_highlight:
            styles_content += '<w:highlight w:val="red"/>'
        if include_color:
            styles_content += '<w:color w:val="FF00FF"/>'
        if include_schemeClr:
            styles_content += '<a:schemeClr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="accent4"/>'
        if include_textFill:
            styles_content += '<a:textFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill><a:srgbClr val="FFFF00"/></a:solidFill></a:textFill>'
        styles_content += '</w:rPr></w:style></w:styles>'

        styles_file = word_dir / "styles.xml"
        styles_file.write_text(styles_content, encoding="utf-8")

        # 创建numbering.xml
        numbering_content = '<?xml version="1.0" encoding="UTF-8"?>'
        numbering_content += '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        numbering_content += '<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:rPr>'
        if include_highlight:
            numbering_content += '<w:highlight w:val="blue"/>'
        if include_color:
            numbering_content += '<w:color w:val="00FFFF"/>'
        if include_schemeClr:
            numbering_content += '<a:schemeClr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" val="accent5"/>'
        if include_textFill:
            numbering_content += '<a:textFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:solidFill><a:srgbClr val="FF00FF"/></a:solidFill></a:textFill>'
        numbering_content += '</w:rPr></w:lvl></w:abstractNum></w:numbering>'

        numbering_file = word_dir / "numbering.xml"
        numbering_file.write_text(numbering_content, encoding="utf-8")

        # 创建DOCX压缩文件
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            for file_path in (temp_dir / "docx_content").rglob("*"):
                if file_path.is_file():
                    arc_name = file_path.relative_to(temp_dir / "docx_content")
                    zip_ref.write(file_path, arc_name)

        return docx_path

    def count_xml_nodes(self, xml_content: str, node_names: list) -> dict:
        """
        统计XML内容中指定节点的数量

        Args:
            xml_content: XML内容字符串
            node_names: 要统计的节点名称列表

        Returns:
            节点数量字典
        """
        root = ET.fromstring(xml_content)
        counts = {}

        for node_name in node_names:
            # 统计所有可能的节点格式
            count = 0
            for elem in root.iter():
                if elem.tag.endswith(f"{node_name}") or elem.tag == f"w:{node_name}" or elem.tag == f"a:{node_name}":
                    count += 1
            counts[node_name] = count

        return counts

    def test_remove_highlight_and_color_nodes(self):
        """测试删除highlight和color节点"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建包含所有格式化节点的测试DOCX文件
            docx_path = self.create_test_docx(temp_path, include_highlight=True, include_color=True, include_schemeClr=True, include_textFill=True)

            # 执行删除操作
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 验证文件仍然存在
            assert docx_path.exists(), "DOCX文件应该仍然存在"

            # 解压修改后的文件并验证
            extract_dir = temp_path / "extracted"
            with zipfile.ZipFile(docx_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # 检查所有处理的XML文件中的格式化节点被删除
            # 根据当前实现，处理的文件包括：document.xml, header*.xml, footer*.xml, styles.xml, numbering.xml
            processed_files = ["document.xml", "styles.xml", "numbering.xml"]
            processed_files.extend([f"header{i}.xml" for i in range(1, 10)])
            processed_files.extend([f"footer{i}.xml" for i in range(1, 10)])

            for xml_name in processed_files:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["highlight", "color", "schemeClr", "textFill"])
                    assert counts["highlight"] == 0, f"{xml_name}中的highlight节点应该被删除"
                    assert counts["color"] == 0, f"{xml_name}中的color节点应该被删除"
                    assert counts["schemeClr"] == 0, f"{xml_name}中的schemeClr节点应该被删除"
                    assert counts["textFill"] == 0, f"{xml_name}中的textFill节点应该被删除"

    def test_remove_only_highlight_nodes(self):
        """测试只删除highlight节点的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建只包含highlight节点的测试DOCX文件
            docx_path = self.create_test_docx(temp_path, include_highlight=True, include_color=False)

            # 执行删除操作
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 解压修改后的文件并验证
            extract_dir = temp_path / "extracted"
            with zipfile.ZipFile(docx_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # 检查所有处理的XML文件中的highlight节点被删除
            # 根据当前实现，处理的文件包括：document.xml, header*.xml, footer*.xml, styles.xml, numbering.xml
            processed_files = ["document.xml", "styles.xml", "numbering.xml"]
            processed_files.extend([f"header{i}.xml" for i in range(1, 10)])
            processed_files.extend([f"footer{i}.xml" for i in range(1, 10)])

            for xml_name in processed_files:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["highlight"])
                    assert counts["highlight"] == 0, f"{xml_name}中的highlight节点应该被删除"

            # 确保color节点没有被意外删除（因为测试文件中没有color节点）
            for xml_name in processed_files:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["color"])
                    # 由于测试文件中没有color节点，所以count应该为0
                    assert counts["color"] == 0, f"{xml_name}中不应该有color节点"

    def test_remove_only_color_nodes(self):
        """测试只删除color节点的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建只包含color节点的测试DOCX文件
            docx_path = self.create_test_docx(temp_path, include_highlight=False, include_color=True)

            # 执行删除操作
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 解压修改后的文件并验证
            extract_dir = temp_path / "extracted"
            with zipfile.ZipFile(docx_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # 检查所有处理的XML文件中的color节点被删除
            # 根据当前实现，处理的文件包括：document.xml, header*.xml, footer*.xml, styles.xml, numbering.xml
            processed_files = ["document.xml", "styles.xml", "numbering.xml"]
            processed_files.extend([f"header{i}.xml" for i in range(1, 10)])
            processed_files.extend([f"footer{i}.xml" for i in range(1, 10)])

            for xml_name in processed_files:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["color"])
                    assert counts["color"] == 0, f"{xml_name}中的color节点应该被删除"

            # 确保highlight节点没有被意外删除（因为测试文件中没有highlight节点）
            for xml_name in processed_files:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["highlight"])
                    # 由于测试文件中没有highlight节点，所以count应该为0
                    assert counts["highlight"] == 0, f"{xml_name}中不应该有highlight节点"

    def test_no_formatting_nodes(self):
        """测试没有格式化节点的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建不包含highlight和color节点的测试DOCX文件
            docx_path = self.create_test_docx(temp_path, include_highlight=False, include_color=False)

            # 执行删除操作应该不会报错
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 验证文件仍然存在
            assert docx_path.exists(), "DOCX文件应该仍然存在"

    def test_missing_word_directory(self):
        """测试缺少word目录的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docx_path = temp_path / "empty.docx"

            # 创建空的ZIP文件
            with zipfile.ZipFile(docx_path, "w") as zip_ref:
                # 创建一个空的文件
                zip_ref.writestr("_rels/.rels", "")

            # 执行删除操作应该不会报错
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 验证文件仍然存在
            assert docx_path.exists(), "DOCX文件应该仍然存在"

    def test_invalid_xml_file(self):
        """测试处理无效XML文件的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docx_path = temp_path / "invalid.docx"

            # 创建包含无效XML的DOCX文件
            word_dir = temp_path / "docx_content" / "word"
            word_dir.mkdir(parents=True)

            # 创建无效的document XML文件（因为document.xml会被处理）
            document_file = word_dir / "document.xml"
            document_file.write_text("invalid xml content", encoding="utf-8")

            # 创建有效的styles.xml和numbering.xml文件
            styles_content = '<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
            numbering_content = '<?xml version="1.0" encoding="UTF-8"?><w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'

            (word_dir / "styles.xml").write_text(styles_content, encoding="utf-8")
            (word_dir / "numbering.xml").write_text(numbering_content, encoding="utf-8")

            # 创建DOCX文件
            with zipfile.ZipFile(docx_path, "w") as zip_ref:
                zip_ref.write(document_file, "word/document.xml")
                zip_ref.write(word_dir / "styles.xml", "word/styles.xml")
                zip_ref.write(word_dir / "numbering.xml", "word/numbering.xml")

            # 执行删除操作应该处理异常但不崩溃
            with patch("remarkable.plugins.cgs.services.comment.logger") as mock_logger:
                remove_docx_formatting_nodes(temp_path, str(docx_path))

                # 验证错误被记录（因为document.xml是无效的XML）
                mock_logger.error.assert_called()

    @patch("remarkable.plugins.cgs.services.comment.logger")
    def test_logging_calls(self, mock_logger):
        """测试日志记录调用"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建包含highlight和color节点的测试DOCX文件
            docx_path = self.create_test_docx(temp_path, include_highlight=True, include_color=True)

            # 执行删除操作
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 验证info日志被调用
            info_calls = mock_logger.info.call_args_list
            assert len(info_calls) >= 1, "应该有info日志调用"

            # 验证包含处理文件的日志（应该只处理document.xml, styles.xml, numbering.xml）
            processing_logged = any("处理XML文件" in str(call) for call in info_calls)
            assert processing_logged, "应该记录文件处理日志"

            # 验证包含删除节点的日志
            removal_logged = any("中删除" in str(call) for call in info_calls)
            assert removal_logged, "应该记录节点删除日志"

            # 验证处理的文件数量（应该处理document.xml, header*.xml, footer*.xml, styles.xml, numbering.xml）
            processed_files = [call for call in info_calls if "处理XML文件" in str(call)]
            assert len(processed_files) <= 15, f"应该最多处理15个文件，实际处理了{len(processed_files)}个文件"

    def test_no_header_footer_files(self):
        """测试没有header或footer文件的DOCX文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docx_path = temp_path / "no_headers.docx"

            # 创建只有document.xml的DOCX文件
            word_dir = temp_path / "docx_content" / "word"
            word_dir.mkdir(parents=True)

            # 创建document.xml文件
            document_content = '<?xml version="1.0" encoding="UTF-8"?>'
            document_content += '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            document_content += "<w:body><w:p><w:r><w:rPr>"
            document_content += '<w:highlight w:val="yellow"/><w:color w:val="FF0000"/>'
            document_content += "</w:rPr><w:t>Document text</w:t></w:r></w:p></w:body></w:document>"

            document_file = word_dir / "document.xml"
            document_file.write_text(document_content, encoding="utf-8")

            # 创建DOCX文件
            with zipfile.ZipFile(docx_path, "w") as zip_ref:
                zip_ref.write(document_file, "word/document.xml")

            # 执行删除操作应该不会报错
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 验证文件仍然存在
            assert docx_path.exists(), "DOCX文件应该仍然存在"

            # 验证document.xml中的节点也被删除
            extract_dir = temp_path / "extracted"
            with zipfile.ZipFile(docx_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            document_file = extract_dir / "word" / "document.xml"
            if document_file.exists():
                document_content = document_file.read_text(encoding="utf-8")
                counts = self.count_xml_nodes(document_content, ["highlight", "color"])
                assert counts["highlight"] == 0, "Document中的highlight节点应该被删除"
                assert counts["color"] == 0, "Document中的color节点应该被删除"

    def test_all_xml_files_processed(self):
        """测试处理所有类型的XML文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docx_path = temp_path / "all_files.docx"

            # 创建包含所有类型XML文件的DOCX文件
            word_dir = temp_path / "docx_content" / "word"
            word_dir.mkdir(parents=True)

            # 创建document.xml
            document_content = '<?xml version="1.0" encoding="UTF-8"?>'
            document_content += '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            document_content += "<w:body><w:p><w:r><w:rPr>"
            document_content += '<w:highlight w:val="yellow"/><w:color w:val="FF0000"/>'
            document_content += "</w:rPr><w:t>Document text</w:t></w:r></w:p></w:body></w:document>"

            # 创建styles.xml
            styles_content = '<?xml version="1.0" encoding="UTF-8"?>'
            styles_content += '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            styles_content += '<w:style w:type="paragraph"><w:rPr>'
            styles_content += '<w:highlight w:val="green"/><w:color w:val="00FF00"/>'
            styles_content += '</w:rPr></w:style></w:styles>'

            # 创建numbering.xml
            numbering_content = '<?xml version="1.0" encoding="UTF-8"?>'
            numbering_content += '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            numbering_content += '<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:rPr>'
            numbering_content += '<w:highlight w:val="blue"/><w:color w:val="0000FF"/>'
            numbering_content += '</w:rPr></w:lvl></w:abstractNum></w:numbering>'

            # 写入文件
            (word_dir / "document.xml").write_text(document_content, encoding="utf-8")
            (word_dir / "styles.xml").write_text(styles_content, encoding="utf-8")
            (word_dir / "numbering.xml").write_text(numbering_content, encoding="utf-8")

            # 创建DOCX文件
            with zipfile.ZipFile(docx_path, "w") as zip_ref:
                zip_ref.write(word_dir / "document.xml", "word/document.xml")
                zip_ref.write(word_dir / "styles.xml", "word/styles.xml")
                zip_ref.write(word_dir / "numbering.xml", "word/numbering.xml")

            # 执行删除操作
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 验证所有文件中的节点都被删除
            extract_dir = temp_path / "extracted"
            with zipfile.ZipFile(docx_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # 检查每个文件
            for xml_name in ["document.xml", "styles.xml", "numbering.xml"]:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["highlight", "color", "schemeClr", "textFill"])
                    assert counts["highlight"] == 0, f"{xml_name}中的highlight节点应该被删除"
                    assert counts["color"] == 0, f"{xml_name}中的color节点应该被删除"
                    assert counts["schemeClr"] == 0, f"{xml_name}中的schemeClr节点应该被删除"
                    assert counts["textFill"] == 0, f"{xml_name}中的textFill节点应该被删除"

    def test_remove_schemeClr_and_textFill_nodes(self):
        """测试删除schemeClr和textFill节点"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 创建只包含schemeClr和textFill节点的测试DOCX文件
            docx_path = self.create_test_docx(temp_path, include_highlight=False, include_color=False, include_schemeClr=True, include_textFill=True)

            # 执行删除操作
            remove_docx_formatting_nodes(temp_path, str(docx_path))

            # 解压修改后的文件并验证
            extract_dir = temp_path / "extracted"
            with zipfile.ZipFile(docx_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # 检查所有处理的XML文件中的schemeClr和textFill节点被删除
            processed_files = ["document.xml", "styles.xml", "numbering.xml"]
            processed_files.extend([f"header{i}.xml" for i in range(1, 10)])
            processed_files.extend([f"footer{i}.xml" for i in range(1, 10)])

            for xml_name in processed_files:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["schemeClr", "textFill"])
                    assert counts["schemeClr"] == 0, f"{xml_name}中的schemeClr节点应该被删除"
                    assert counts["textFill"] == 0, f"{xml_name}中的textFill节点应该被删除"

            # 确保highlight和color节点没有被意外删除（因为测试文件中没有这些节点）
            for xml_name in processed_files:
                xml_file = extract_dir / "word" / xml_name
                if xml_file.exists():
                    content = xml_file.read_text(encoding="utf-8")
                    counts = self.count_xml_nodes(content, ["highlight", "color"])
                    assert counts["highlight"] == 0, f"{xml_name}中不应该有highlight节点"
                    assert counts["color"] == 0, f"{xml_name}中不应该有color节点"
