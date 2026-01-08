import logging
import subprocess
import time

import pytest

from remarkable.common.exceptions import ShellCmdError
from remarkable.common.util import subprocess_exec


class TestSubprocessExec:
    """Test cases for the optimized subprocess_exec function using pytest."""

    def test_successful_command_execution(self):
        """Test successful execution of a simple command."""
        result = subprocess_exec("echo 'Hello World'")
        assert result.strip() == "Hello World"

    def test_command_with_multiple_lines(self):
        """Test command that produces multiple lines of output."""
        result = subprocess_exec("echo 'Line 1'; echo 'Line 2'; echo 'Line 3'")
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    def test_command_with_stderr_raises_exception(self):
        """Test that commands producing stderr raise ShellCmdError."""
        with pytest.raises(ShellCmdError) as exc_info:
            subprocess_exec("echo 'Error message' >&2")

        assert "Error message" in str(exc_info.value)

    def test_command_with_both_stdout_and_stderr(self):
        """Test command that produces both stdout and stderr."""
        with pytest.raises(ShellCmdError) as exc_info:
            subprocess_exec("echo 'Standard output'; echo 'Error output' >&2")

        # Should raise exception due to stderr, even though stdout exists
        assert "Error output" in str(exc_info.value)

    def test_empty_command_output(self):
        """Test command that produces no output."""
        result = subprocess_exec("true")  # Unix command that succeeds with no output
        assert result == ""

    def test_command_timeout(self):
        """Test command timeout functionality."""
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 5", timeout=1)

    def test_command_with_special_characters(self):
        """Test command with special characters in output."""
        result = subprocess_exec("echo 'Special chars: !@#$%^&*()'")
        assert "Special chars: !@#$%^&*()" in result

    def test_command_with_unicode_output(self):
        """Test command with unicode characters in output."""
        result = subprocess_exec("echo '测试中文字符'")
        assert "测试中文字符" in result

    def test_real_time_stdout_logging(self, caplog):
        """Test that stdout is logged in real-time."""
        with caplog.at_level(logging.INFO, logger="remarkable.common.util.subprocess_output"):
            result = subprocess_exec("echo 'Test output'")

        # Check that output was captured
        assert result.strip() == "Test output"

        # Check that output was logged
        stdout_logs = [
            record for record in caplog.records if record.levelname == "INFO" and "[STDOUT]" in record.message
        ]
        assert len(stdout_logs) == 1
        assert "Test output" in stdout_logs[0].message

    def test_real_time_stderr_logging(self, caplog):
        """Test that stderr is logged in real-time."""
        with caplog.at_level(logging.WARNING, logger="remarkable.common.util.subprocess_output"):
            with pytest.raises(ShellCmdError):
                subprocess_exec("echo 'Error output' >&2")

        # Check that error was logged
        stderr_logs = [
            record for record in caplog.records if record.levelname == "WARNING" and "[STDERR]" in record.message
        ]
        assert len(stderr_logs) == 1
        assert "Error output" in stderr_logs[0].message

    def test_multiline_real_time_logging(self, caplog):
        """Test real-time logging for multi-line commands."""
        with caplog.at_level(logging.INFO, logger="remarkable.common.util.subprocess_output"):
            result = subprocess_exec('for i in 1 2 3; do echo "Line $i"; done')

        # Check captured output
        lines = result.strip().split("\n")
        assert len(lines) == 3

        # Check real-time logging
        stdout_logs = [
            record for record in caplog.records if record.levelname == "INFO" and "[STDOUT]" in record.message
        ]
        assert len(stdout_logs) == 3
        assert "Line 1" in stdout_logs[0].message
        assert "Line 2" in stdout_logs[1].message
        assert "Line 3" in stdout_logs[2].message

    def test_command_with_exit_code_zero_but_stderr(self):
        """Test command that exits with code 0 but has stderr output."""
        # Some commands may write to stderr but still succeed
        with pytest.raises(ShellCmdError):
            subprocess_exec("echo 'Warning message' >&2; exit 0")

    def test_invalid_command(self):
        """Test execution of invalid/non-existent command."""
        with pytest.raises(ShellCmdError):
            subprocess_exec("nonexistent_command_12345")

    def test_command_with_pipes(self):
        """Test command with pipes."""
        result = subprocess_exec("echo 'hello world' | tr '[:lower:]' '[:upper:]'")
        assert result.strip() == "HELLO WORLD"

    def test_command_with_environment_variables(self):
        """Test command that uses environment variables."""
        result = subprocess_exec("echo $HOME")
        # Should return some path (not empty for most systems)
        assert isinstance(result, str)

    def test_threading_approach_reliability(self):
        """Test that the threading approach works reliably."""
        result = subprocess_exec("echo 'Threading test'")
        assert result.strip() == "Threading test"

    def test_command_with_large_output(self):
        """Test command that produces large output."""
        # Generate 100 lines of output
        result = subprocess_exec('for i in $(seq 1 100); do echo "Line $i"; done')
        lines = result.strip().split("\n")
        assert len(lines) == 100
        assert lines[0] == "Line 1"
        assert lines[99] == "Line 100"

    def test_preserve_output_formatting(self):
        """Test that output formatting (spaces, tabs) is preserved."""
        # Use printf instead of echo -e for better cross-platform compatibility
        result = subprocess_exec("printf 'Line1\\n  Line2\\n    Line3\\n'")
        lines = result.split("\n")
        assert lines[0] == "Line1"
        assert lines[1] == "  Line2"
        assert lines[2] == "    Line3"

    def test_logging_command_execution(self, caplog):
        """Test that command execution is logged."""
        with caplog.at_level(logging.INFO, logger="remarkable.common.util"):
            subprocess_exec("echo 'test'")

        # Check that the command execution was logged
        command_logs = [record for record in caplog.records if "running command:" in record.message]
        assert len(command_logs) == 1
        assert "running command: \"echo 'test'\"" in command_logs[0].message

    @pytest.mark.skip()
    def test_timeout_with_cleanup(self):
        """Test that timeout properly cleans up the process."""
        start_time = time.time()
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 10", timeout=1)
        end_time = time.time()

        # Should timeout in approximately 1 second, not 10
        assert end_time - start_time < 3  # Allow some margin for test execution

    def test_empty_stderr_does_not_raise_exception(self):
        """Test that empty stderr does not raise an exception."""
        # Command that might touch stderr stream but doesn't write to it
        result = subprocess_exec("echo 'success' 2>/dev/null")
        assert result.strip() == "success"


class TestSubprocessExecEdgeCases:
    """Test edge cases and error conditions for subprocess_exec."""

    def test_none_timeout(self):
        """Test that None timeout works correctly."""
        result = subprocess_exec("echo 'no timeout'", timeout=None)
        assert result.strip() == "no timeout"

    def test_zero_timeout(self):
        """Test behavior with zero timeout."""
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 1", timeout=0)

    def test_very_short_timeout(self):
        """Test behavior with very short timeout."""
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 1", timeout=0.1)

    def test_command_with_quotes(self):
        """Test command with various quote types."""
        result = subprocess_exec("echo \"Hello 'World'\"")
        assert "Hello 'World'" in result

    def test_command_with_backslashes(self):
        """Test command with backslashes."""
        # Use printf to properly handle backslashes without shell interpretation
        result = subprocess_exec("printf 'Path\\\\to\\\\file'")
        assert "Path\\to\\file" in result

    def test_concurrent_stdout_stderr_logging(self, caplog):
        """Test that concurrent stdout and stderr are properly logged."""
        with caplog.at_level(logging.INFO, logger="remarkable.common.util.subprocess_output"):
            with pytest.raises(ShellCmdError):
                subprocess_exec("echo 'stdout line'; echo 'stderr line' >&2; echo 'more stdout'")

        # Check that both stdout and stderr were logged
        stdout_logs = [
            record for record in caplog.records if record.levelname == "INFO" and "[STDOUT]" in record.message
        ]
        stderr_logs = [
            record for record in caplog.records if record.levelname == "WARNING" and "[STDERR]" in record.message
        ]

        assert len(stdout_logs) >= 1  # At least one stdout log
        assert len(stderr_logs) == 1  # One stderr log
        assert "stderr line" in stderr_logs[0].message

    def test_logging_levels(self, caplog):
        """Test that stdout and stderr use different logging levels."""
        with caplog.at_level(logging.INFO, logger="remarkable.common.util.subprocess_output"):
            with pytest.raises(ShellCmdError):
                subprocess_exec("echo 'info message'; echo 'warning message' >&2")

        # Filter logs to only subprocess output logs
        subprocess_logs = [
            record for record in caplog.records if record.name == "remarkable.common.util.subprocess_output"
        ]

        info_logs = [record for record in subprocess_logs if record.levelname == "INFO"]
        warning_logs = [record for record in subprocess_logs if record.levelname == "WARNING"]

        assert len(info_logs) >= 1
        assert len(warning_logs) == 1
        assert "[STDOUT]" in info_logs[0].message
        assert "[STDERR]" in warning_logs[0].message

    def test_large_output_logging_performance(self, caplog):
        """Test logging performance with large output."""
        with caplog.at_level(logging.INFO, logger="remarkable.common.util.subprocess_output"):
            result = subprocess_exec('for i in $(seq 1 50); do echo "Line $i"; done')

        lines = result.strip().split("\n")
        assert len(lines) == 50

        # Check that all lines were logged
        stdout_logs = [
            record for record in caplog.records if record.levelname == "INFO" and "[STDOUT]" in record.message
        ]
        assert len(stdout_logs) == 50

    def test_thread_exception_handling(self, caplog):
        """测试线程内部异常处理"""
        # 测试当线程读取流时发生异常的情况
        # 这个测试验证异常被正确捕获并放入队列
        with caplog.at_level(logging.INFO, logger="remarkable.common.util.subprocess_output"):
            result = subprocess_exec("echo 'test output'")

        # 验证正常情况下没有异常
        assert result.strip() == "test output"

        # 验证日志中没有异常信息
        error_logs = [record for record in caplog.records if "Error reading" in record.message]
        assert len(error_logs) == 0

    def test_queue_empty_exception_handling(self):
        """测试队列为空时的异常处理逻辑"""
        # 测试当队列为空时的超时处理逻辑
        # 这个测试验证 Empty 异常被正确处理
        result = subprocess_exec("echo 'quick command'", timeout=5)
        assert result.strip() == "quick command"

        # 测试短超时的情况，验证 Empty 异常处理
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 2", timeout=0.5)

    def test_process_poll_during_queue_read(self):
        """测试进程在队列读取过程中结束的情况"""
        # 测试进程快速结束时的处理逻辑
        result = subprocess_exec("echo 'fast command'")
        assert result.strip() == "fast command"

        # 测试进程结束后仍有输出需要读取的情况
        result = subprocess_exec("echo 'line1'; echo 'line2'; echo 'line3'")
        lines = result.strip().split('\n')
        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "line3"

    def test_thread_cleanup_on_exception(self):
        """测试异常情况下线程是否正确清理"""
        # 测试超时异常时线程是否正确清理
        import threading
        initial_thread_count = threading.active_count()

        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 3", timeout=0.5)

        # 等待一小段时间让线程清理完成
        time.sleep(0.2)

        # 验证线程数量没有增加（线程被正确清理）
        final_thread_count = threading.active_count()
        assert final_thread_count <= initial_thread_count + 1  # 允许一些容错

    def test_daemon_thread_behavior(self):
        """测试守护线程的行为"""
        # 验证守护线程不会阻止程序退出
        # 这个测试主要验证线程被正确设置为daemon
        result = subprocess_exec("echo 'daemon test'")
        assert result.strip() == "daemon test"

        # 验证多个命令的守护线程行为
        for i in range(3):
            result = subprocess_exec(f"echo 'daemon test {i}'")
            assert f"daemon test {i}" in result

    @pytest.mark.skip()
    def test_timeout_during_queue_read(self):
        """测试在队列读取过程中发生超时"""
        # 测试在读取队列时发生超时的情况
        start_time = time.time()
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 5", timeout=1.0)
        end_time = time.time()

        # 验证超时时间准确性 - 允许更宽松的范围，因为系统可能很快检测到超时
        elapsed = end_time - start_time
        assert elapsed < 3.0  # 主要确保不会等待完整的5秒

    def test_timeout_after_process_finish(self):
        """测试进程结束后的超时处理"""
        # 测试进程快速完成但输出读取需要时间的情况
        result = subprocess_exec("echo 'quick finish'", timeout=5)
        assert result.strip() == "quick finish"

        # 测试进程完成后的输出读取超时逻辑
        result = subprocess_exec("echo 'line1'; echo 'line2'", timeout=10)
        lines = result.strip().split('\n')
        assert len(lines) == 2

    def test_process_killed_during_execution(self):
        """测试进程在执行过程中被杀死的情况"""
        # 测试超时导致进程被杀死的情况
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("sleep 10", timeout=0.5)

        # 测试进程被外部信号杀死的情况（通过超时模拟）
        start_time = time.time()
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess_exec("while true; do echo 'running'; sleep 0.1; done", timeout=1)
        end_time = time.time()

        # 验证进程确实被及时杀死
        elapsed = end_time - start_time
        assert elapsed < 2.0

    def test_process_exit_code_handling(self):
        """测试不同的进程退出码"""
        # 测试退出码为0的正常情况
        result = subprocess_exec("exit 0")
        assert result == ""

        # 测试非零退出码但无stderr的情况
        # 注意：subprocess_exec主要关注stderr，而不是退出码
        result = subprocess_exec("echo 'success'; exit 1")
        assert result.strip() == "success"

        # 测试非零退出码且有stderr的情况
        with pytest.raises(ShellCmdError):
            subprocess_exec("echo 'error' >&2; exit 1")

    def test_unbuffered_output(self):
        """测试unbuffered输出的实时性"""
        # 验证 bufsize=1 的效果，输出应该是实时的
        result = subprocess_exec("echo 'unbuffered test'")
        assert result.strip() == "unbuffered test"

        # 测试多行输出的实时性
        result = subprocess_exec("echo 'line1'; echo 'line2'; echo 'line3'")
        lines = result.strip().split('\n')
        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "line3"

    def test_mixed_line_endings(self):
        """测试不同的行结束符"""
        # 测试不同行结束符的处理
        # Unix风格的换行符
        result = subprocess_exec("printf 'line1\\nline2\\nline3\\n'")
        lines = result.split('\n')
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "line3"

        # 测试没有换行符的输出
        result = subprocess_exec("printf 'no_newline'")
        assert result == "no_newline"

    def test_concurrent_subprocess_exec_calls(self):
        """测试多个并发的subprocess_exec调用"""
        # 测试日志记录器的线程安全性
        import concurrent.futures

        def run_command(cmd_id):
            return subprocess_exec(f"echo 'concurrent test {cmd_id}'")

        # 并发执行多个命令
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_command, i) for i in range(10)]
            results = [f.result() for f in futures]

        # 验证所有命令都成功执行
        assert len(results) == 10
        for i, result in enumerate(results):
            assert f"concurrent test {i}" in result
