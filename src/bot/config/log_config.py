import logging
import sys

def setup_logger():
    """
    봇 전역에서 사용할 표준 로거를 설정하고 반환합니다.
    이 함수를 통해 모든 모듈이 동일한 로거 인스턴스를 공유하게 됩니다.
    """
    # 'discord_bot'이라는 이름의 로거를 생성합니다.
    logger = logging.getLogger('discord_bot')
    
    # 로거의 레벨을 INFO로 설정합니다. (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    logger.setLevel(logging.INFO)
    
    # 핸들러가 이미 설정되어 있다면 중복 추가를 방지합니다.
    if not logger.handlers:
        # 로그를 콘솔(stdout)에 출력하는 핸들러를 생성합니다.
        handler = logging.StreamHandler(sys.stdout)
        
        # 로그 형식(formatter)을 지정합니다.
        # 예: 2025-09-06 14:30:00,123 - discord_bot - INFO - 메시지 내용
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # 생성한 핸들러를 로거에 추가합니다.
        logger.addHandler(handler)
        
    return logger
