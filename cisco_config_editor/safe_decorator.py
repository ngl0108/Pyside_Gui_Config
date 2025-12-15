# cisco_config_editor/safe_decorator.py
from functools import wraps
from typing import Callable, Any
from PySide6.QtWidgets import QMessageBox
import traceback


class SafeExecute:
    """안전한 함수 실행을 위한 데코레이터 클래스"""

    def __init__(self, show_dialog=True, log_error=True):
        self.show_dialog = show_dialog
        self.log_error = log_error

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"함수 '{func.__name__}' 실행 중 오류:\n{str(e)}"
                error_details = traceback.format_exc()

                # 로깅
                if self.log_error:
                    print(f"[ERROR] {error_msg}")
                    print(error_details)

                # 다이얼로그 표시
                if self.show_dialog and hasattr(args[0], 'is_qt_object'):
                    try:
                        QMessageBox.critical(
                            args[0],
                            "실행 오류",
                            f"{error_msg}\n\n자세한 내용은 콘솔을 확인하세요."
                        )
                    except:
                        pass

                return None

        return wrapper


# 사용 예시 데코레이터
def safe_execute(func=None, *, show_dialog=True, log_error=True):
    """
    함수를 안전하게 실행하는 데코레이터

    사용법:
    @safe_execute
    def my_function():
        # 코드

    @safe_execute(show_dialog=False)
    def another_function():
        # 코드
    """
    if func is None:
        return lambda f: SafeExecute(show_dialog=show_dialog, log_error=log_error)(f)
    return SafeExecute(show_dialog=show_dialog, log_error=log_error)(func)