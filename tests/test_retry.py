import pytest
import time
from unittest.mock import Mock, patch, call
from agents.retry import with_retry, RetryConfig, _is_transient_error


class TestTransientErrorDetection:
    def test_timeout_error(self):
        assert _is_transient_error(Exception("Request timeout"))
        assert _is_transient_error(Exception("Connection timed out"))

    def test_rate_limit_error(self):
        assert _is_transient_error(Exception("Rate limit exceeded"))
        assert _is_transient_error(Exception("429 Too Many Requests"))

    def test_service_unavailable_error(self):
        assert _is_transient_error(Exception("503 Service Unavailable"))
        assert _is_transient_error(Exception("502 Bad Gateway"))

    def test_connection_error(self):
        assert _is_transient_error(Exception("Connection refused"))
        assert _is_transient_error(Exception("Network error"))

    def test_non_transient_error(self):
        assert not _is_transient_error(Exception("Invalid input"))
        assert not _is_transient_error(Exception("404 Not Found"))
        assert not _is_transient_error(Exception("Authentication failed"))


class TestRetryConfig:
    def test_delay_calculation_exponential(self):
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0

    def test_delay_capped_at_max(self):
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False,
        )
        assert config.get_delay(0) == 1.0
        assert config.get_delay(5) == 10.0  # 32 capped to 10
        assert config.get_delay(10) == 10.0

    def test_jitter_adds_randomness(self):
        config = RetryConfig(
            initial_delay=10.0,
            exponential_base=1.0,
            jitter=True,
        )
        delays = [config.get_delay(0) for _ in range(10)]
        # All delays should be within ~10% of 10.0
        assert all(9.0 <= d <= 11.0 for d in delays)
        # But they should not all be exactly 10.0
        assert len(set(delays)) > 1


class TestRetryDecorator:
    def test_succeeds_on_first_try(self):
        config = RetryConfig(max_retries=3)

        @with_retry(config)
        def func():
            return "success"

        result = func()
        assert result == "success"

    def test_retries_on_transient_error(self):
        config = RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)

        call_count = 0

        @with_retry(config)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Timeout")
            return "success"

        result = func()
        assert result == "success"
        assert call_count == 3

    def test_fails_on_non_transient_error(self):
        config = RetryConfig(max_retries=3, initial_delay=0.01)

        call_count = 0

        @with_retry(config)
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            func()

        # Should not retry on non-transient error
        assert call_count == 1

    def test_gives_up_after_max_retries(self):
        config = RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)

        call_count = 0

        @with_retry(config)
        def func():
            nonlocal call_count
            call_count += 1
            raise Exception("Timeout")

        with pytest.raises(Exception):
            func()

        # Should try initial attempt + 2 retries = 3 total
        assert call_count == 3

    def test_exponential_backoff_timing(self):
        config = RetryConfig(
            max_retries=2,
            initial_delay=0.05,
            exponential_base=2.0,
            jitter=False,
        )

        call_count = 0
        times = []

        @with_retry(config)
        def func():
            nonlocal call_count
            times.append(time.time())
            call_count += 1
            if call_count < 3:
                raise Exception("Timeout")
            return "success"

        result = func()
        assert result == "success"

        # Check approximate delays between retries
        delay1 = times[1] - times[0]
        delay2 = times[2] - times[1]

        # First retry should have delay ~0.05s
        assert 0.04 < delay1 < 0.1

        # Second retry should have delay ~0.10s (double)
        assert 0.09 < delay2 < 0.15

    def test_preserves_function_metadata(self):
        @with_retry()
        def my_function():
            """Docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "Docstring."

    def test_handles_rate_limit_429(self):
        config = RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)

        call_count = 0

        @with_retry(config)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 Too Many Requests")
            return "success"

        result = func()
        assert result == "success"
        assert call_count == 2

    def test_handles_rate_limit_text(self):
        config = RetryConfig(max_retries=2, initial_delay=0.01, jitter=False)

        call_count = 0

        @with_retry(config)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Rate limit exceeded")
            return "success"

        result = func()
        assert result == "success"
        assert call_count == 2
